"""Turn an uploaded CSV into a clean, case-annotated step log plus a data-quality report."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from worktrace.ingest.business_ids import clean_business_ids, impute_business_ids
from worktrace.ingest.generic import is_event_log, read_event_log
from worktrace.ingest.kyp import is_kyp_export, read_kyp_steps
from worktrace.ingest.reader import open_export
from worktrace.ingest.sessions import assign_sessions
from worktrace.schemas import CaseStrategy, DataQuality

# Below this share of steps with a trustworthy Business ID, cases are work sessions instead.
MIN_ID_COVERAGE = 0.5


@dataclass
class EventLog:
    """steps: one row per process step, with case_id and session_id. clipboard: copy/cut/paste events."""

    steps: pd.DataFrame
    clipboard: pd.DataFrame
    quality: DataQuality

    @property
    def case_steps(self) -> pd.DataFrame:
        """Steps that belong to a case, ordered within each case."""
        cased = self.steps.dropna(subset=["case_id"])
        return cased.sort_values(["case_id", "start"]).reset_index(drop=True)


def load_event_log(path: str | Path) -> EventLog:
    export = open_export(path)
    if is_kyp_export(export.columns):
        kyp = read_kyp_steps(export)
        steps, clipboard, rows_read, dropped = kyp.steps, kyp.clipboard, kyp.rows_read, kyp.dropped
        source = "kyp_activity_sequence"
    elif is_event_log(export.columns):
        steps, rows_read, dropped = read_event_log(export)
        clipboard = pd.DataFrame(columns=["user", "time", "app", "activity", "kind"])
        source = "event_log"
    else:
        raise ValueError(
            "Unrecognised CSV. Upload a KYP.ai Activity Sequence Export, or an event log with "
            "case, activity and timestamp columns."
        )
    if steps.empty:
        raise ValueError("The file has no usable events.")

    steps = steps.sort_values(["user", "start"]).reset_index(drop=True)
    steps["session_id"] = assign_sessions(steps)
    notes: list[str] = []

    if source == "event_log":
        strategy: CaseStrategy = "case_column"
        rejected, id_share, imputed, ids_found = [], 1.0, 0, steps["case_id"].nunique()
    else:
        steps["business_id"], rejected = clean_business_ids(steps.pop("raw_business_id"))
        ids_found = int(steps["business_id"].nunique())
        steps["business_id"], imputed = impute_business_ids(steps)
        id_share = float(steps["business_id"].notna().mean())
        strategy = "business_id" if id_share >= MIN_ID_COVERAGE else "work_session"
        steps["case_id"] = steps["business_id"] if strategy == "business_id" else steps["session_id"]
        notes.extend(_kyp_notes(steps, strategy, id_share, rejected))

    rows_per_step = float(steps["rows"].sum() / len(steps))
    quality = DataQuality(
        source_format=source,
        rows_read=rows_read,
        rows_dropped={reason: count for reason, count in dropped.items() if count},
        steps=len(steps),
        rows_per_step=round(rows_per_step, 2),
        case_strategy=strategy,
        cases=int(steps["case_id"].nunique()),
        business_ids_found=ids_found,
        business_ids_rejected=rejected[:12],
        steps_with_business_id=round(id_share, 4),
        steps_with_imputed_id=imputed,
        export_metadata=export.metadata,
        notes=notes,
    )
    return EventLog(steps=steps, clipboard=clipboard, quality=quality)


def _kyp_notes(steps: pd.DataFrame, strategy: CaseStrategy, id_share: float, rejected: list[str]) -> list[str]:
    notes = [
        "Interaction rows were collapsed into process steps; step counters were counted once per step.",
    ]
    if rejected:
        notes.append(f"{len(rejected)} Business ID values did not match the dominant ID format and were ignored.")
    if strategy == "work_session":
        notes.append(
            f"Only {id_share:.0%} of steps carry a usable Business ID, so cases are work sessions "
            "(a user's steps until a break of 30 minutes or more)."
        )
    return notes
