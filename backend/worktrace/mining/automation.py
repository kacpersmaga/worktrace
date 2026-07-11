"""Which steps to automate first, and how.

Each activity is measured on five signals and ranked against the others:
  - hours per week        how much time is at stake
  - volume                executions per week
  - manual input          clicks, keystrokes and clipboard operations per minute
  - data hand-carry       cross-application copy-paste transfers per execution
  - predictability        1 - normalised entropy of what comes next; steps that
                          always lead to the same next step follow a rule a bot
                          can follow too

The approach is picked from the dominant signal, and the expected saving uses
a conservative automation rate per approach (see AUTOMATION_RATES).
"""

import math

import pandas as pd

from worktrace.mining.scoring import hours, make_signals, percent, percentile_ranks, weighted_score
from worktrace.schemas import AutomationCandidate

MIN_EXECUTIONS = 10
MAX_CANDIDATES = 12
WEIGHTS = {"hours_per_week": 0.3, "per_week": 0.2, "manual_rate": 0.2, "transfer_rate": 0.15, "predictability": 0.15}
LABELS = {
    "hours_per_week": "Hours per week",
    "per_week": "Executions per week",
    "manual_rate": "Manual inputs per minute",
    "transfer_rate": "Copy-paste transfers per run",
    "predictability": "Predictable next step",
}
FORMATS = {
    "hours_per_week": hours,
    "per_week": lambda value: f"{value:.0f}",
    "manual_rate": lambda value: f"{value:.1f}",
    "transfer_rate": lambda value: f"{value:.2f}",
    "predictability": percent,
}

# Share of a step's time an approach can realistically remove. Deliberately conservative.
AUTOMATION_RATES = {
    "System integration": 0.8,
    "Document data extraction": 0.6,
    "RPA data entry": 0.5,
    "Workflow rule": 0.7,
    "Assisted RPA": 0.35,
}
DOCUMENT_APPS = ("acrobat", "reader", "pdf", "scan")


def automation_candidates(flow: pd.DataFrame, transfers: pd.DataFrame, weeks: float) -> list[AutomationCandidate]:
    measured = _measure(flow, transfers, weeks)
    if measured.empty:
        return []
    ranks = measured[list(WEIGHTS)].apply(percentile_ranks)
    measured["score"] = weighted_score(ranks, WEIGHTS)
    measured = measured.sort_values("score", ascending=False).head(MAX_CANDIDATES)
    return [_candidate(name, row, ranks.loc[name]) for name, row in measured.iterrows()]


def _measure(flow: pd.DataFrame, transfers: pd.DataFrame, weeks: float) -> pd.DataFrame:
    flow = flow.assign(
        duration_s=flow["active_s"] + flow["idle_s"],
        inputs=flow["clicks"] + flow["keys"] + flow["copies"] + flow["pastes"] + flow["cuts"],
    )
    grouped = flow.groupby("activity").agg(
        executions=("duration_s", "size"),
        total_s=("duration_s", "sum"),
        active_s=("active_s", "sum"),
        inputs=("inputs", "sum"),
        keys=("keys", "sum"),
        app=("app", lambda apps: apps.mode().iat[0]),
    )
    grouped = grouped[grouped["executions"] >= MIN_EXECUTIONS]

    cross_app = transfers[transfers["source_app"] != transfers["target_app"]]
    transfers_in = cross_app.groupby("target_step").size()
    transfers_out = cross_app.groupby("source_step").size()
    moved = transfers_in.add(transfers_out, fill_value=0).reindex(grouped.index).fillna(0)

    measured = pd.DataFrame(index=grouped.index)
    measured["app"] = grouped["app"]
    measured["hours_per_week"] = grouped["total_s"] / 3600 / weeks
    measured["per_week"] = grouped["executions"] / weeks
    measured["manual_rate"] = grouped["inputs"] / (grouped["active_s"] / 60).clip(lower=1 / 60)
    measured["transfer_rate"] = moved / grouped["executions"]
    source_app = cross_app.groupby("target_step")["source_app"].agg(lambda apps: apps.mode().iat[0])
    measured["fed_from"] = source_app.reindex(grouped.index).fillna("")
    measured["key_rate"] = grouped["keys"] / grouped["executions"]
    measured["predictability"] = _predictability(flow).reindex(grouped.index).fillna(0)
    return measured


def _predictability(flow: pd.DataFrame) -> pd.Series:
    """1 - H(next step) / log2(#possible next steps); 1.0 when the next step is always the same."""
    following = flow.groupby("case_id", sort=False)["activity"].shift(-1).fillna("(end)")
    counts = pd.crosstab(flow["activity"], following)

    def score(row: pd.Series) -> float:
        probabilities = row[row > 0] / row.sum()
        if len(probabilities) <= 1:
            return 1.0
        entropy = -sum(p * math.log2(p) for p in probabilities)
        return 1 - entropy / math.log2(len(probabilities))

    return counts.apply(score, axis=1)


def _is_document_app(app: str) -> bool:
    return any(name in app.lower() for name in DOCUMENT_APPS)


def _approach(row: pd.Series) -> str:
    """Pick the approach from the dominant signal; the order matters, first match wins."""
    if _is_document_app(row["app"]) or (_is_document_app(row["fed_from"]) and row["key_rate"] >= 3):
        return "Document data extraction"
    if row["transfer_rate"] >= 0.5:
        return "System integration"
    if row["key_rate"] >= 3:
        return "RPA data entry"
    if row["predictability"] >= 0.75:
        return "Workflow rule"
    return "Assisted RPA"


def _candidate(activity: str, row: pd.Series, ranks: pd.Series) -> AutomationCandidate:
    approach = _approach(row)
    rate = AUTOMATION_RATES[approach]
    rationale = [f"{row['hours_per_week']:.1f} h of work per week over {row['per_week']:.0f} executions."]
    if row["transfer_rate"] >= 0.2:
        source = f" (mostly from {row['fed_from']})" if row["fed_from"] else ""
        rationale.append(f"{row['transfer_rate']:.1f} values per run are carried by copy-paste between applications{source}.")
    if row["key_rate"] >= 3:
        rationale.append(f"About {row['key_rate']:.0f} text entries per run: typing that a bot can do from structured data.")
    if row["predictability"] >= 0.6:
        rationale.append(f"What follows is predictable ({row['predictability']:.0%}), so the step follows a stable rule.")
    rationale.append(f"{approach} typically removes about {rate:.0%} of this time.")

    return AutomationCandidate(
        activity=activity,
        app=row["app"],
        approach=approach,
        score=round(float(row["score"]), 1),
        hours_per_week=round(float(row["hours_per_week"]), 2),
        saving_hours_per_week=round(float(row["hours_per_week"] * rate), 2),
        automation_rate=rate,
        executions_per_week=round(float(row["per_week"]), 1),
        signals=make_signals(row, ranks, LABELS, FORMATS),
        rationale=rationale,
    )
