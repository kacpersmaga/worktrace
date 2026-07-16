import csv
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from worktrace.synthetic import COLUMNS

T0 = datetime(2026, 3, 2, 9, 0, 0)


def kyp_row(user: str, step: str, app: str, start: datetime, end: datetime, kind: str, at: datetime,
            business_id: str = "", copies: int = 0, pastes: int = 0, clicks: int = 0, keys: int = 0,
            interactions: int = 1, passive_ms: int = 0) -> dict[str, str]:
    def stamp(value: datetime) -> str:
        return value.strftime("%Y-%m-%dT%H:%M:%S.000")

    total = int((end - start).total_seconds() * 1000)
    row = dict.fromkeys(COLUMNS, "")
    row.update({
        "User name": user, "Process step": step, "Application name": app, "Activity Status": "Active",
        "Process step start": stamp(start), "Process step end": stamp(end), "Activity type": kind,
        "Activity start timestamp": stamp(at), "Business ID": business_id,
        "Business ID Source": "AI" if business_id else "NOT_FOUND",
        "Process Step Total Duration": str(total), "Process Step Active Duration": str(total - passive_ms),
        "Process Step Passive Duration": str(passive_ms), "Copy No.": str(copies), "Paste No.": str(pastes),
        "Clicks No.": str(clicks), "Text entries No.": str(keys), "Cut No.": "0", "Activities No.": str(interactions),
    })
    return row


def write_kyp(path: Path, rows: list[dict[str, str]], footer: bool = True, encoding: str = "utf-8") -> Path:
    with path.open("w", newline="", encoding=encoding) as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
        if footer:
            for line in ["Applied filters:", "Time zone: Europe/Warsaw"]:
                writer.writerow(dict.fromkeys(COLUMNS, "") | {"User name": line})
    return path


def step_rows(user: str, step: str, app: str, start: datetime, seconds: int, kinds: list[str], **counters) -> list[dict]:
    """All interaction rows of one step, with step-level counters repeated on each row, like the real export."""
    end = start + timedelta(seconds=seconds)
    return [
        kyp_row(user, step, app, start, end, kind, start + timedelta(seconds=index), interactions=len(kinds), **counters)
        for index, kind in enumerate(kinds)
    ]


def flow_frame(cases: dict[str, list[tuple[str, int, int]]]) -> pd.DataFrame:
    """Case-ordered steps from {case: [(activity, start_offset_s, duration_s), ...]}."""
    rows = []
    for case_id, steps in cases.items():
        for activity, offset, seconds in steps:
            start = T0 + timedelta(seconds=offset)
            rows.append({
                "case_id": case_id, "activity": activity, "user": "u1", "app": activity.split()[0],
                "start": start, "end": start + timedelta(seconds=seconds), "active_s": float(seconds),
                "idle_s": 0.0, "clicks": 1, "keys": 0, "copies": 0, "pastes": 0, "cuts": 0,
            })
    return pd.DataFrame(rows)


@pytest.fixture
def tmp_csv(tmp_path: Path):
    return lambda name="export.csv": tmp_path / name
