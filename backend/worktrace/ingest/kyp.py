"""KYP.ai "Activity Sequence Export" → one row per process step.

The export has one row per *interaction* (a click, a keystroke burst, a paste),
but the step-level columns (durations, Copy No., Clicks No., ...) are repeated
on every interaction row of the same step. Summing them over rows would
inflate every counter by the number of interactions (about 5x on the sample,
more on busy steps), so rows are collapsed back into steps first and counters
are read once per step.
"""

from dataclasses import dataclass, field

import pandas as pd

from worktrace.ingest.reader import RawExport

USER = "User name"
STEP = "Process step"
APP = "Application name"
STEP_START = "Process step start"
STEP_END = "Process step end"
VIEW = "Original view name"
ACTIVITY_START = "Activity start timestamp"
ACTIVITY_TYPE = "Activity type"
BUSINESS_ID = "Business ID"
AI_BUSINESS_ID = "AI Business ID"
ACTIVE_MS = "Process Step Active Duration"
INTERACTION_MS = "Activity duration (ms)"
PASSIVE_MS = "Process Step Passive Duration"
TOTAL_MS = "Process Step Total Duration"

COUNTERS = {
    "Clicks No.": "clicks",
    "Text entries No.": "keys",
    "Copy No.": "copies",
    "Paste No.": "pastes",
    "Cut No.": "cuts",
}
REQUIRED = {USER, STEP, STEP_START}
OPTIONAL = {APP, VIEW, INTERACTION_MS, STEP_END, ACTIVITY_START, ACTIVITY_TYPE, BUSINESS_ID, AI_BUSINESS_ID, ACTIVE_MS, PASSIVE_MS, TOTAL_MS}

# The same interaction is spelled differently across exporter versions.
INTERACTION_TYPES = {
    "click": "mouse",
    "mouse": "mouse",
    "text entry": "text-entry",
    "text-entry": "text-entry",
    "copy": "copy",
    "cut": "cut",
    "paste": "paste",
    "idle": "idle",
}
TYPE_TO_COUNTER = {"mouse": "clicks", "text-entry": "keys", "copy": "copies", "paste": "pastes", "cut": "cuts"}
CLIPBOARD_TYPES = {"copy", "cut", "paste"}
# Each interaction row has its own duration, and together they cover the step: so the step's time can be
# split into what the person was doing. Anything else (window just opened, heartbeat rows) is looking at the screen.
TIME_SPLIT = {"text-entry": "typing_s", "mouse": "clicking_s", "copy": "clipboard_s", "cut": "clipboard_s",
              "paste": "clipboard_s", "idle": "no_input_s"}
TIME_COLUMNS = ["typing_s", "clicking_s", "clipboard_s", "looking_s", "no_input_s"]
STEP_KEY = ["user", "step_start", "activity"]


@dataclass
class KypSteps:
    steps: pd.DataFrame
    clipboard: pd.DataFrame
    rows_read: int = 0
    dropped: dict[str, int] = field(default_factory=dict)


def is_kyp_export(columns: list[str]) -> bool:
    return REQUIRED.issubset(columns)


def read_kyp_steps(export: RawExport) -> KypSteps:
    usecols = [column for column in export.columns if column in REQUIRED | OPTIONAL | COUNTERS.keys()]
    partial_steps, clipboard_parts = [], []
    rows_read = 0
    dropped = {"no timestamp": 0, "no user or step": 0}

    for chunk in export.chunks(usecols=usecols):
        rows_read += len(chunk)
        rows = _normalise_rows(chunk)
        missing_identity = rows["user"].eq("") | rows["activity"].eq("")
        missing_time = rows["step_start"].isna() & ~missing_identity
        dropped["no user or step"] += int(missing_identity.sum())
        dropped["no timestamp"] += int(missing_time.sum())
        rows = rows.loc[~missing_identity & ~missing_time]
        partial_steps.append(_collapse_to_steps(rows))
        clipboard_parts.append(_clipboard_events(rows))

    steps = _merge_partial_steps(partial_steps)
    clipboard = pd.concat(clipboard_parts, ignore_index=True) if clipboard_parts else _empty_clipboard()
    dropped["footer lines"] = export.footer_rows
    return KypSteps(steps=steps, clipboard=clipboard, rows_read=rows_read + export.footer_rows, dropped=dropped)


def _normalise_rows(chunk: pd.DataFrame) -> pd.DataFrame:
    def text(column: str) -> pd.Series:
        return chunk[column].str.strip() if column in chunk else pd.Series("", index=chunk.index)

    def time(column: str) -> pd.Series:
        return pd.to_datetime(text(column), errors="coerce", format="ISO8601")

    def number(column: str) -> pd.Series:
        return pd.to_numeric(text(column), errors="coerce")

    rows = pd.DataFrame({
        "user": text(USER),
        "activity": text(STEP),
        "app": text(APP).replace("", "Unknown"),
        "view": text(VIEW).replace({"<Removed>": "", "<Anonymized>": ""}),
        "step_start": time(STEP_START),
        "step_end": time(STEP_END),
        "event_time": time(ACTIVITY_START),
        "type": text(ACTIVITY_TYPE).str.lower().map(INTERACTION_TYPES).fillna("other"),
        "business_id": text(BUSINESS_ID).where(text(BUSINESS_ID) != "", text(AI_BUSINESS_ID)),
        "active_ms": number(ACTIVE_MS),
        "passive_ms": number(PASSIVE_MS),
        "total_ms": number(TOTAL_MS),
        "interaction_ms": number(INTERACTION_MS).fillna(0).clip(lower=0),
    })
    for source, target in COUNTERS.items():
        rows[target] = number(source) if source in chunk else float("nan")
    rows["event_time"] = rows["event_time"].fillna(rows["step_start"])
    # A step without a name is still work in a known application.
    unnamed = rows["activity"].eq("") & rows["app"].ne("Unknown")
    rows.loc[unnamed, "activity"] = "Use " + rows.loc[unnamed, "app"]
    return rows


def _collapse_to_steps(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame()
    typed = pd.get_dummies(rows["type"]).reindex(columns=list(TYPE_TO_COUNTER), fill_value=False)
    typed = typed.astype(int).rename(columns=TYPE_TO_COUNTER).add_prefix("seen_")
    rows = pd.concat([rows, typed], axis=1)
    rows["has_id"] = rows["business_id"].where(rows["business_id"] != "")
    spent_on = rows["type"].map(TIME_SPLIT).fillna("looking_s")
    for column in TIME_COLUMNS:
        rows[column] = rows["interaction_ms"].where(spent_on == column, 0) / 1000

    grouped = rows.groupby(STEP_KEY, sort=False)
    steps = grouped.agg(
        app=("app", "first"),
        view=("view", "first"),
        step_end=("step_end", "max"),
        last_event=("event_time", "max"),
        active_ms=("active_ms", "first"),
        passive_ms=("passive_ms", "first"),
        total_ms=("total_ms", "first"),
        raw_business_id=("has_id", "first"),
        rows=("type", "size"),
        **{column: (column, "sum") for column in TIME_COLUMNS},
        **{name: (name, "first") for name in TYPE_TO_COUNTER.values()},
        **{f"seen_{name}": (f"seen_{name}", "sum") for name in TYPE_TO_COUNTER.values()},
    )
    return steps.reset_index()


def _merge_partial_steps(parts: list[pd.DataFrame]) -> pd.DataFrame:
    """Steps cut in half by a chunk boundary appear twice; join them back."""
    parts = [part for part in parts if not part.empty]
    if not parts:
        raise ValueError("No usable rows: every row was missing a user, a step name or a timestamp.")
    steps = pd.concat(parts, ignore_index=True)
    sums = {f"seen_{name}": "sum" for name in TYPE_TO_COUNTER.values()} | {"rows": "sum"} | dict.fromkeys(TIME_COLUMNS, "sum")
    firsts = {column: "first" for column in steps.columns if column not in sums and column not in STEP_KEY}
    steps = steps.groupby(STEP_KEY, sort=False).agg(firsts | sums | {"step_end": "max", "last_event": "max"})
    steps = steps.reset_index()

    for name in TYPE_TO_COUNTER.values():
        # Older exports have no counter columns; fall back to counting the interaction rows.
        steps[name] = steps[name].fillna(steps[f"seen_{name}"]).astype(int)

    end = steps["step_end"].fillna(steps["step_start"] + pd.to_timedelta(steps["total_ms"], unit="ms"))
    steps["end"] = end.fillna(steps["last_event"]).clip(lower=steps["step_start"])
    wall_ms = (steps["end"] - steps["step_start"]).dt.total_seconds() * 1000
    steps["idle_s"] = steps["passive_ms"].fillna(0) / 1000
    steps["active_s"] = steps["active_ms"].fillna(wall_ms - steps["idle_s"] * 1000).clip(lower=0) / 1000

    steps = steps.rename(columns={"step_start": "start"})
    columns = ["user", "activity", "app", "view", "start", "end", "active_s", "idle_s", "rows", "raw_business_id"]
    return steps[columns + list(TYPE_TO_COUNTER.values()) + TIME_COLUMNS].sort_values(["user", "start"]).reset_index(drop=True)


def _clipboard_events(rows: pd.DataFrame) -> pd.DataFrame:
    events = rows.loc[rows["type"].isin(CLIPBOARD_TYPES), ["user", "event_time", "app", "activity", "type"]]
    return events.rename(columns={"event_time": "time", "type": "kind"})


def _empty_clipboard() -> pd.DataFrame:
    return pd.DataFrame(columns=["user", "time", "app", "activity", "kind"])
