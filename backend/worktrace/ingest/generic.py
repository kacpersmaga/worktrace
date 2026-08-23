"""Plain event logs: one row per event with a case, an activity and a timestamp.

Column names are matched loosely, so exports from Celonis, Disco, pm4py or a
hand-made spreadsheet work without renaming anything.
"""

import pandas as pd

from worktrace.ingest.reader import RawExport

ALIASES = {
    "case": ["case:concept:name", "case_id", "case id", "caseid", "case", "business id", "ticket", "order id"],
    "activity": ["concept:name", "activity", "activity name", "event", "task", "step", "process step"],
    "start": ["time:timestamp", "timestamp", "start", "start_time", "start time", "start timestamp", "time", "date"],
    "end": ["end", "end_time", "end time", "complete", "end timestamp", "completed"],
    "user": ["org:resource", "user", "resource", "user name", "performer", "employee", "agent"],
    "app": ["application", "app", "application name", "system", "tool"],
}


def find_columns(columns: list[str]) -> dict[str, str]:
    lowered = {column.strip().lower(): column for column in columns}
    found = {}
    for role, names in ALIASES.items():
        match = next((lowered[name] for name in names if name in lowered), None)
        if match:
            found[role] = match
    return found


def is_event_log(columns: list[str]) -> bool:
    return {"case", "activity", "start"}.issubset(find_columns(columns))


def read_event_log(export: RawExport) -> tuple[pd.DataFrame, int, dict[str, int]]:
    """Return steps in the same shape as the KYP reader, plus rows read and drop counts."""
    mapping = find_columns(export.columns)
    frame = pd.concat(export.chunks(usecols=list(mapping.values())), ignore_index=True)
    frame = frame.rename(columns={column: role for role, column in mapping.items()})

    steps = pd.DataFrame({
        "case_id": frame["case"].str.strip(),
        "activity": frame["activity"].str.strip(),
        "user": frame["user"].str.strip() if "user" in frame else "unknown",
        "app": frame["app"].str.strip() if "app" in frame else "",
        "start": pd.to_datetime(frame["start"], errors="coerce", format="mixed"),
        "end": pd.to_datetime(frame["end"], errors="coerce", format="mixed") if "end" in frame else pd.NaT,
    })
    rows_read = len(steps) + export.footer_rows
    no_time = steps["start"].isna()
    no_identity = steps["case_id"].eq("") | steps["activity"].eq("")
    steps = steps.loc[~no_time & ~no_identity].sort_values(["case_id", "start"]).reset_index(drop=True)
    steps["app"] = steps["app"].replace("", "Unknown")
    steps["view"] = ""
    steps["user"] = steps["user"].replace("", "unknown")

    # Without end times an event lasts until the next event of the same case starts.
    next_start = steps.groupby("case_id")["start"].shift(-1)
    steps["end"] = steps["end"].fillna(next_start).fillna(steps["start"]).clip(lower=steps["start"])
    steps["active_s"] = (steps["end"] - steps["start"]).dt.total_seconds()
    steps["idle_s"] = 0.0
    steps["rows"] = 1
    for counter in ("clicks", "keys", "copies", "pastes", "cuts"):
        steps[counter] = 0
    for column in ("typing_s", "clicking_s", "clipboard_s", "looking_s", "no_input_s"):
        steps[column] = 0.0  # a plain event log says nothing about what happened inside a step

    dropped = {"no timestamp": int(no_time.sum()), "no case or activity": int((no_identity & ~no_time).sum())}
    dropped["footer lines"] = export.footer_rows
    return steps, rows_read, dropped
