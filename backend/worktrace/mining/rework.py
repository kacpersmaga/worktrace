"""Rework: coming back to a step that was already done in the same case.

For each return to an activity, the steps in between form a loop
(A -> B -> A, A -> B -> C -> A). Loops are counted by pattern, so the result
reads like "Check purchase order -> Email vendor -> Check purchase order
happened in 17% of invoices".
"""

from collections import defaultdict

import pandas as pd

from worktrace.schemas import ReworkLoop

MAX_LOOP_LENGTH = 4
MAX_LOOPS = 10


def find_rework_loops(flow: pd.DataFrame) -> list[ReworkLoop]:
    """flow: case-ordered steps with repeats collapsed."""
    occurrences: dict[tuple[str, ...], int] = defaultdict(int)
    cases: dict[tuple[str, ...], set[str]] = defaultdict(set)
    seconds: dict[tuple[str, ...], float] = defaultdict(float)

    for case_id, group in flow.groupby("case_id", sort=False):
        path = group["activity"].tolist()
        durations = (group["active_s"] + group["idle_s"]).tolist()
        last_seen: dict[str, int] = {}
        for position, activity in enumerate(path):
            earlier = last_seen.get(activity)
            last_seen[activity] = position
            if earlier is None or position - earlier > MAX_LOOP_LENGTH:
                continue
            pattern = tuple(path[earlier:position + 1])
            occurrences[pattern] += 1
            cases[pattern].add(case_id)
            seconds[pattern] += sum(durations[earlier + 1:position + 1])

    total_cases = flow["case_id"].nunique()
    loops = [
        ReworkLoop(
            pattern=list(pattern),
            occurrences=count,
            cases=len(cases[pattern]),
            share_of_cases=round(len(cases[pattern]) / total_cases, 4),
            hours=round(seconds[pattern] / 3600, 2),
        )
        for pattern, count in occurrences.items()
    ]
    return sorted(loops, key=lambda loop: loop.hours, reverse=True)[:MAX_LOOPS]


def rework_rate_by_activity(flow: pd.DataFrame) -> pd.Series:
    """Share of cases containing the activity in which it is done more than once."""
    per_case = flow.groupby(["activity", "case_id"]).size()
    return (per_case > 1).groupby(level="activity").mean()
