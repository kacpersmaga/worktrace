"""Cases cut off by the export window.

An export covers fixed dates, so invoices that were already running on the
first day, or still waiting for approval on the last one, appear without their
beginning or end. Counted as they are, they look like process deviations
("21% of cases skip Post invoice") and pull case durations down.

The usual start and end activities are learned from cases that lie well inside
the window. A case near the window's edge that does not start (or finish) with
one of them is treated as cut off and left out of the variant, map and duration
statistics. Cases in the middle of the window that end unusually are real
deviations and stay in.
"""

import pandas as pd

TYPICAL_COVERAGE = 0.95


def complete_cases(flow: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """flow: case-ordered steps. Returns the steps of complete cases and the number of cut-off cases."""
    cases = flow.groupby("case_id", sort=False).agg(
        first=("activity", "first"), last=("activity", "last"), start=("start", "min"), end=("end", "max")
    )
    horizon = (cases["end"] - cases["start"]).quantile(0.9)
    window_start, window_end = cases["start"].min(), cases["end"].max()
    near_start = cases["start"] < window_start + horizon
    near_end = cases["end"] > window_end - horizon
    inner = cases[~near_start & ~near_end]
    if len(inner) < 20:
        return flow, 0  # window too short to learn what complete looks like

    starts = _typical(inner["first"])
    ends = _typical(inner["last"])
    cut_off = (near_start & ~cases["first"].isin(starts)) | (near_end & ~cases["last"].isin(ends))
    kept = cases.index[~cut_off]
    return flow[flow["case_id"].isin(kept)], int(cut_off.sum())


def _typical(activities: pd.Series) -> set[str]:
    """The most common values that together cover TYPICAL_COVERAGE of cases."""
    shares = activities.value_counts(normalize=True)
    covered = shares.cumsum().shift(fill_value=0)
    return set(shares[covered < TYPICAL_COVERAGE].index)
