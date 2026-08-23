"""Why a step is slow and what to do about it.

A score says *that* a step matters; a manager needs *why* and *what next*. For
one activity this module measures what actually happens inside it: how its
time splits into typing, clicking, copy-paste, reading and time with no input
(every interaction in a KYP export carries its own duration), which screens it
happens in, what data is pasted in or copied out, which application people
keep flicking to, how far apart the fastest and slowest person are, and what
the slow outliers are made of.

Each measurement that crosses a threshold becomes a cause: the evidence in
numbers, a concrete action, and how many hours per day or week it concerns.
Causes are ordered by those hours.
"""

from dataclasses import dataclass

import pandas as pd

from worktrace.mining.scoring import human_duration
from worktrace.mining.transitions import with_successors
from worktrace.schemas import Cause, Diagnosis, ReworkLoop, Share

DOCUMENT_APPS = ("acrobat", "reader", "pdf", "scan")
BROWSERS = ("chrome", "edge", "firefox", "safari", "browser")
APPROVAL_WORDS = ("approv", "sign-off", "authoris", "authoriz")
EXTERNAL_WORDS = ("vendor", "supplier", "customer", "client", "email", "e-mail", "mail")

REKEY_PER_RUN = 0.5
COPY_OUT_PER_RUN = 0.5
LOOKUPS_PER_RUN = 0.5
TYPING_PER_RUN = 5
IDLE_SHARE = 0.15
LONG_BREAK_S = 600
DOMINANT_SHARE = 0.45
TAIL_RATIO = 3
MIN_TAIL_RUNS = 20
PEOPLE_RATIO = 1.6
MIN_PERSON_RUNS = 10
REWORK_SHARE = 0.05
NEXT_DAY_SHARE = 0.5
OTHER_PERSON_SHARE = 0.5
MIN_BLUEPRINT_VALUES = 0.2

TIME_LABELS = {
    "typing_s": "Typing",
    "clicking_s": "Clicking and scrolling",
    "clipboard_s": "Copying and pasting",
    "looking_s": "Looking at the screen",
    "no_input_s": "No input (away or waiting)",
}

# What the slow runs are made of decides what to do about them.
TAIL_ACTIONS = {
    "no_input_s": ("long pauses with the step open, not slow work",
                   "Ask the people involved what they were waiting for (the system, a colleague, missing information) and fix that cause."),
    "typing_s": ("much more typing than usual",
                 "Those cases carry more data to enter (long documents, many lines). Pre-fill or import it instead of typing."),
    "clicking_s": ("clicking and scrolling through screens",
                   "People are searching for something. A search, a filter or a direct link to the record they need cuts this."),
    "clipboard_s": ("copying and pasting",
                    "The data for those cases is gathered from several places. Bring the sources together or connect them."),
    "looking_s": ("reading the screen without input",
                  "Those cases need more reading and judgement. A short checklist for the common exceptions speeds them up."),
}


@dataclass
class DiagnosisContext:
    flow: pd.DataFrame        # case-ordered steps, repeats collapsed
    steps: pd.DataFrame       # every step, with switch marks (switched, ping_pong, from_app)
    transfers: pd.DataFrame   # matched copy -> paste pairs
    rework: list[ReworkLoop]
    aliases: dict[str, str]
    periods: float            # number of days or weeks the export covers
    period: str               # "day" or "week"
    cases_are_sessions: bool

    def describe_run(self, run: pd.Series) -> str:
        """A run as a manager can find it: who, when, and the case ID when there is a real one."""
        who = self.aliases.get(run["user"], run["user"])
        when = f"{run['start'].day} {run['start']:%b %H:%M}"
        return f"{who}, {when}" if self.cases_are_sessions else f"{run['case_id']} ({who}, {when})"


def diagnose_step(context: DiagnosisContext, activity: str) -> Diagnosis:
    runs = context.flow[context.flow["activity"] == activity]
    durations = runs["active_s"] + runs["idle_s"]
    screens = _screens(context, activity)
    app = _place(str(runs["app"].mode().iat[0]), screens)
    runs_per = len(runs) / context.periods
    hours_per = durations.sum() / 3600 / context.periods
    data_in = _transfers(context, runs, "target_step", activity, "source_step", "source_app")
    data_out = _transfers(context, runs, "source_step", activity, "target_step", "target_app")

    tail = _long_tail(context, runs, durations)
    causes = [cause for cause in (
        _rekeying(context, runs, app, data_in, hours_per),
        _copy_out(context, app, activity, data_out, hours_per),
        _lookups(context, runs, activity, app, hours_per),
        _typing(context, runs, data_in, hours_per),
        None if tail is not None and tail.kind == "pauses" else _idle(context, runs, app),
        tail,
        _rework(context, activity),
        _people(context, runs, durations),
    ) if cause is not None]
    causes.sort(key=lambda cause: cause.hours, reverse=True)

    summary = (
        f"{activity} in {app} runs about {runs_per:,.0f} times a {context.period} at {human_duration(durations.median())} "
        f"each: {hours_per:.1f} h of work a {context.period}."
    )
    split = _time_split(runs)
    if split:
        biggest = max(split, key=lambda share: share.share)
        summary += f" Most of that time is {biggest.label.lower()} ({biggest.share:.0%})."
    return Diagnosis(
        summary=summary,
        per_run={
            "minutes": round(float(durations.median()) / 60, 2),
            "clicks": round(float(runs["clicks"].mean()), 1),
            "keys": round(float(runs["keys"].mean()), 1),
            "pastes": round(float(runs["pastes"].mean()), 1),
            "copies": round(float(runs["copies"].mean()), 1),
            "idle_minutes": round(float(runs["idle_s"].mean()) / 60, 2),
        },
        time_split=split,
        screens=screens,
        before=_neighbours(context, activity, before=True),
        after=_neighbours(context, activity, before=False),
        data_in=data_in,
        data_out=data_out,
        causes=causes,
    )


def diagnose_handover(context: DiagnosisContext, source: str, target: str) -> Diagnosis:
    pairs = with_successors(context.flow)
    pairs["next_user"] = pairs.groupby("case_id", sort=False)["user"].shift(-1)
    pairs["next_start"] = pairs["end"] + pd.to_timedelta(pairs["wait_s"], unit="s")
    pairs = pairs[(pairs["activity"] == source) & (pairs["next_activity"] == target)]
    waits = pairs["wait_s"]
    next_day = float((pairs["next_start"].dt.date > pairs["end"].dt.date).mean())
    other_person = float((pairs["next_user"] != pairs["user"]).mean())
    resume_hour = int(pairs["next_start"].dt.hour.mode().iat[0])
    cases_per = len(pairs) / context.periods
    wait_hours_per = waits.sum() / 3600 / context.periods
    waiting = f"{wait_hours_per / 24:,.0f} case-days of waiting a {context.period}"
    names = f"{source} {target}".lower()
    slowest = pairs.loc[waits.sort_values(ascending=False).index[:3]]
    examples = [f"{context.describe_run(row)}: waited {human_duration(row['wait_s'])}" for _, row in slowest.iterrows()]

    causes = []
    if any(word in names for word in APPROVAL_WORDS):
        causes.append(Cause(
            kind="approval", title="Cases queue for approval",
            evidence=f"A typical case waits {human_duration(waits.median())}; the slowest 10% wait {human_duration(waits.quantile(0.9))}.",
            action="Auto-approve below an agreed amount, remind approvers after a few hours, and let them approve from e-mail or a phone.",
            hours=round(wait_hours_per, 1), impact=waiting, examples=examples,
        ))
    elif any(word in source.lower() for word in EXTERNAL_WORDS):
        causes.append(Cause(
            kind="external", title="Cases wait for an outside reply",
            evidence=f"After “{source}” a typical case waits {human_duration(waits.median())} before anyone continues.",
            action="Ask for the missing data with a structured form instead of free-text e-mail, chase automatically after a deadline, and mark the case as waiting so nobody re-checks it early.",
            hours=round(wait_hours_per, 1), impact=waiting, examples=examples,
        ))
    if next_day >= NEXT_DAY_SHARE:
        causes.append(Cause(
            kind="overnight", title="Work resumes only the next day",
            evidence=f"{next_day:.0%} of cases are picked up on a later day, most often around {resume_hour}:00.",
            action=f"“{target}” is done in a morning batch. Start it as soon as “{source}” completes (a notification or an automatic task) to win back up to a day per case.",
            hours=round(wait_hours_per * next_day, 1),
            impact=f"{cases_per * next_day:,.0f} cases a {context.period} lose a day",
        ))
    if other_person >= OTHER_PERSON_SHARE:
        causes.append(Cause(
            kind="handoff", title="A different person continues the case",
            evidence=f"In {other_person:.0%} of cases someone else does “{target}”.",
            action="Route the case to the next person automatically and show waiting cases in a shared queue with a target time.",
            hours=round(wait_hours_per * other_person, 1), impact=f"{cases_per * other_person:,.0f} hand-offs a {context.period}",
        ))
    if not causes:
        causes.append(Cause(
            kind="gap", title="Nothing recorded happens in between",
            evidence=f"Cases sit for {human_duration(waits.median())} with no activity in the recorded applications.",
            action="Check what happens outside the recorded apps (phone, paper, another team) and whether it can run in parallel with earlier steps.",
            hours=round(wait_hours_per, 1), impact=waiting, examples=examples,
        ))
    return Diagnosis(
        summary=(
            f"After “{source}”, about {cases_per:,.0f} cases a {context.period} wait a median of {human_duration(waits.median())} "
            f"before “{target}”."
        ),
        per_run={}, screens=[], before=[], after=[], data_in=[], data_out=[],
        causes=causes,
    )


def automation_blueprint(diagnosis: Diagnosis, activity: str, app: str) -> list[str]:
    """The steps a bot or integration would take over, written from what was observed."""
    trigger = next((share.label for share in diagnosis.before if share.label != "(case start)"), None)
    lines = [f"Start when “{trigger}” finishes." if trigger else "Start when a new case arrives."]
    for source in diagnosis.data_in[:2]:
        if source.share < MIN_BLUEPRINT_VALUES:
            continue
        verb = "Extract" if any(word in source.detail.lower() for word in DOCUMENT_APPS) else "Read"
        lines.append(f"{verb} the values people copy from “{source.label}” in {source.detail} ({source.share:.1f} per case today).")
    screen = diagnosis.screens[0].label if diagnosis.screens else app
    typed = diagnosis.per_run.get("keys", 0)
    lines.append(f"Fill in “{screen}”" + (f", where about {typed:.0f} entries are typed by hand today." if typed >= 1 else "."))
    for target in diagnosis.data_out[:2]:
        if target.share < MIN_BLUEPRINT_VALUES:
            continue
        lines.append(f"Write the result into “{target.label}” in {target.detail} ({target.share:.1f} copy-pastes per case today).")
    lines.append("Pass the case to a person only when a check fails or data is missing.")
    return lines


# --- measurements ------------------------------------------------------------

def _transfers(context: DiagnosisContext, runs: pd.DataFrame, side: str, activity: str,
               other_step: str, other_app: str) -> list[Share]:
    moved = context.transfers[(context.transfers[side] == activity)]
    moved = moved[moved["source_app"] != moved["target_app"]]
    if moved.empty:
        return []
    counts = moved.groupby([other_step, other_app]).size().sort_values(ascending=False).head(3)
    return [Share(label=step, detail=app, share=round(count / len(runs), 2)) for (step, app), count in counts.items()]


def _time_split(runs: pd.DataFrame) -> list[Share]:
    """Where the time inside the step goes, from the duration of each recorded interaction."""
    seconds = runs[list(TIME_LABELS)].sum()
    total = seconds.sum()
    if total <= 0:
        return []
    per_run = seconds / len(runs)
    return [
        Share(label=label, share=round(float(seconds[column] / total), 3), detail=f"{human_duration(per_run[column])} per run")
        for column, label in TIME_LABELS.items()
    ]


def _place(app: str, screens: list[Share]) -> str:
    """“Chrome” says nothing; the page title of a web app does."""
    if any(name in app.lower() for name in BROWSERS) and screens and screens[0].share >= 0.5:
        return f"{screens[0].label} ({app})"
    return app


def _screens(context: DiagnosisContext, activity: str) -> list[Share]:
    views = context.steps.loc[context.steps["activity"] == activity, "view"]
    views = views[views.str.len() > 0]
    if views.empty:
        return []
    shares = views.value_counts(normalize=True).head(3)
    return [Share(label=view, share=round(share, 3)) for view, share in shares.items()]


def _neighbours(context: DiagnosisContext, activity: str, before: bool) -> list[Share]:
    shift = 1 if before else -1
    neighbour = context.flow.groupby("case_id", sort=False)["activity"].shift(shift)
    neighbour = neighbour.fillna("(case start)" if before else "(case end)")
    shares = neighbour[context.flow["activity"] == activity].value_counts(normalize=True).head(3)
    return [Share(label=name, share=round(share, 3)) for name, share in shares.items()]


# --- causes --------------------------------------------------------------------

def _rekeying(context: DiagnosisContext, runs: pd.DataFrame, app: str, data_in: list[Share], hours: float) -> Cause | None:
    per_run = sum(source.share for source in data_in)
    if per_run < REKEY_PER_RUN:
        return None
    top = data_in[0]
    document = any(word in top.detail.lower() for word in DOCUMENT_APPS)
    action = (
        f"Extract the fields from the {top.detail} document automatically (document AI) and pre-fill {app}, so people only check them."
        if document else
        f"Pass the data from {top.detail} to {app} through an integration or a file import instead of copy-paste."
    )
    return Cause(
        kind="rekeying", title=f"Data is re-keyed from {top.detail}",
        evidence=f"{per_run:.1f} values per run are pasted in, most from “{top.label}” ({top.detail}), and "
                 f"{runs['keys'].mean():.0f} more entries are typed.",
        action=action, hours=round(hours, 1), impact=f"{hours:.1f} h of work a {context.period} in this step",
    )


def _copy_out(context: DiagnosisContext, app: str, activity: str, data_out: list[Share], hours: float) -> Cause | None:
    per_run = sum(target.share for target in data_out)
    if per_run < COPY_OUT_PER_RUN:
        return None
    top = data_out[0]
    return Cause(
        kind="copy_out", title=f"Results are copied by hand into {top.detail}",
        evidence=f"After each run {per_run:.1f} values are pasted into “{top.label}” ({top.detail}), one at a time.",
        action=f"Send the result from {app} to {top.detail} automatically (an integration, a bulk import or a small bot), so nobody copies values one by one.",
        hours=round(hours * 0.5, 1), impact=f"the copying in “{top.label}”",
    )


def _lookups(context: DiagnosisContext, runs: pd.DataFrame, activity: str, app: str, hours: float) -> Cause | None:
    marked = context.steps[(context.steps["activity"] == activity) & context.steps["ping_pong"]]
    per_run = len(marked) / len(runs)
    if per_run < LOOKUPS_PER_RUN:
        return None
    partner = str(marked["from_app"].mode().iat[0])
    return Cause(
        kind="lookups", title=f"People keep jumping to {partner} and back",
        evidence=f"{per_run:.1f} quick trips to {partner} per run (out and back within two minutes): looking something up or fetching a value.",
        action=f"If it is the same information each time, show it inside {app} (a lookup or a side panel); if values are carried over, connect the two.",
        hours=round(hours * 0.3, 1), impact=f"{len(marked) / context.periods:,.0f} switches a {context.period}",
    )


def _typing(context: DiagnosisContext, runs: pd.DataFrame, data_in: list[Share], hours: float) -> Cause | None:
    keys = runs["keys"].mean()
    if keys < TYPING_PER_RUN or sum(source.share for source in data_in) >= REKEY_PER_RUN:
        return None
    return Cause(
        kind="typing", title="A lot is typed by hand",
        evidence=f"About {keys:.0f} text entries and {runs['clicks'].mean():.0f} clicks per run.",
        action="Pre-fill what the system already knows, use templates and defaults for the rest, and validate fields as they are typed.",
        hours=round(hours * 0.5, 1), impact=f"{hours:.1f} h of work a {context.period} in this step",
    )


def _idle(context: DiagnosisContext, runs: pd.DataFrame, app: str) -> Cause | None:
    no_input = runs[["idle_s", "no_input_s"]].max(axis=1)
    total = (runs["active_s"] + runs["idle_s"]).sum()
    share = no_input.sum() / total if total else 0
    if share < IDLE_SHARE:
        return None
    hours = no_input.sum() / 3600 / context.periods
    long_breaks = no_input[no_input >= LONG_BREAK_S]
    if len(long_breaks):
        runs_word = "run" if len(long_breaks) == 1 else "runs"
        detail = (f" {len(long_breaks)} {runs_word} had a break of 10 minutes or more with the step open; "
                  f"the longest was {human_duration(long_breaks.max())}.")
    else:
        detail = " The pauses are short and frequent rather than one long break."
    examples = [f"{context.describe_run(runs.loc[index])}: {human_duration(no_input[index])} without input"
                for index in long_breaks.sort_values(ascending=False).index[:3]]
    return Cause(
        kind="idle", title="The step sits open with nobody working in it",
        evidence=f"{share:.0%} of the time in this step has no mouse or keyboard input ({hours:.1f} h a {context.period}).{detail}",
        action=(f"A screen open with no input means the person left or waited: for {app} to load, for a colleague, for "
                f"information. Ask the people involved which, then fix that cause (a performance ticket, faster answers, "
                f"or close the case and resume it later)."),
        hours=round(hours, 1), impact=f"{hours:.1f} h a {context.period} without input", examples=examples,
    )


def _long_tail(context: DiagnosisContext, runs: pd.DataFrame, durations: pd.Series) -> Cause | None:
    if len(runs) < MIN_TAIL_RUNS:
        return None
    median, p90 = durations.median(), durations.quantile(0.9)
    if p90 < TAIL_RATIO * max(median, 1):
        return None
    slow_index = durations[durations > p90].index
    slow = runs.loc[slow_index]
    excess = (durations[slow_index] - median).sum() / 3600 / context.periods
    made_of = slow[list(TIME_LABELS)].sum()
    examples = [f"{context.describe_run(runs.loc[index])}: {human_duration(durations[index])}"
                for index in durations[slow_index].sort_values(ascending=False).index[:3]]
    evidence = f"A typical run takes {human_duration(median)}, but the slowest 10% take over {human_duration(p90)}."
    if made_of.sum() <= 0:
        return Cause(
            kind="long_tail", title="A few runs take far longer than the rest", evidence=evidence,
            action="Open the slowest cases: long runs are usually exceptions handled ad hoc. Give the common ones their own path or checklist.",
            hours=round(excess, 1), impact=f"{excess:.1f} h a {context.period} above a typical run", examples=examples,
        )
    shares = (made_of / made_of.sum()).sort_values(ascending=False)
    dominant, share = shares.index[0], shares.iloc[0]
    if share < DOMINANT_SHARE:
        mix = ", ".join(f"{value:.0%} {TIME_LABELS[column].lower()}" for column, value in shares.head(3).items())
        return Cause(
            kind="long_tail", title="A few runs take far longer than the rest",
            evidence=f"{evidence} Their time is mixed: {mix}.",
            action="Open the slowest runs listed here with the people who did them: with no single pattern, the reason is case-specific (an unusual request, a system problem, an interruption).",
            hours=round(excess, 1), impact=f"{excess:.1f} h a {context.period} above a typical run", examples=examples,
        )
    what, action = TAIL_ACTIONS[dominant]
    return Cause(
        kind="pauses" if dominant == "no_input_s" else "long_tail",
        title="Some runs stall with nobody working" if dominant == "no_input_s" else "A few runs take far longer than the rest",
        evidence=f"{evidence} In those slow runs {share:.0%} of the time is {what}.",
        action=action, hours=round(excess, 1), impact=f"{excess:.1f} h a {context.period} above a typical run", examples=examples,
    )


def _rework(context: DiagnosisContext, activity: str) -> Cause | None:
    if context.cases_are_sessions:
        return None
    loops = [loop for loop in context.rework if loop.pattern[0] == activity and loop.share_of_cases >= REWORK_SHARE]
    if not loops:
        return None
    loop = max(loops, key=lambda item: item.cases)
    reason = " → ".join(loop.pattern[1:-1])
    hours = loop.hours / context.periods
    return Cause(
        kind="rework", title="Cases come back to it",
        evidence=f"{loop.share_of_cases:.0%} of cases do it twice, going through “{reason}” in between.",
        action=f"Catch the reason for “{reason}” before or during “{activity}” (a required field, a check against the order) so the second pass is not needed.",
        hours=round(hours, 1), impact=f"{hours:.1f} h a {context.period} of repeated work",
    )


def _people(context: DiagnosisContext, runs: pd.DataFrame, durations: pd.Series) -> Cause | None:
    per_person = durations.groupby(runs["user"]).agg(["median", "size"])
    per_person = per_person[per_person["size"] >= MIN_PERSON_RUNS]
    if len(per_person) < 3:
        return None
    fast, slow = per_person["median"].idxmin(), per_person["median"].idxmax()
    ratio = per_person.at[slow, "median"] / max(per_person.at[fast, "median"], 1)
    if ratio < PEOPLE_RATIO:
        return None
    team = durations.median()
    own = durations[runs["user"] == slow]
    excess = (own - team).clip(lower=0).sum() / 3600 / context.periods
    fast_name, slow_name = context.aliases.get(fast, fast), context.aliases.get(slow, slow)
    return Cause(
        kind="people", title=f"{slow_name} needs {ratio:.1f}× longer than {fast_name} for the same step",
        evidence=f"{slow_name} takes {human_duration(per_person.at[slow, 'median'])} per run, {fast_name} {human_duration(per_person.at[fast, 'median'])}.",
        action=f"Sit {slow_name} next to {fast_name} for an hour and compare how they do it (shortcuts, order of work, tools); write the faster way down as the team standard.",
        hours=round(excess, 1), impact=f"{excess:.1f} h a {context.period} above the team's typical run",
    )
