"""Routines: the same short sequence of steps, repeated across many cases.

Sequences of 3 to 6 consecutive steps are counted over all cases. A sequence
is kept only if it is not just a piece of a longer routine with almost the same
support (a "closed" pattern), so the list shows whole routines rather than
every fragment of them.
"""

from collections import defaultdict

import pandas as pd

from worktrace.schemas import Routine

MIN_LENGTH, MAX_LENGTH = 3, 6
MIN_SUPPORT_SHARE = 0.03
CLOSED_RATIO = 0.9
MAX_ROUTINES = 10


def find_routines(flow: pd.DataFrame) -> list[Routine]:
    """flow: case-ordered steps with repeats collapsed."""
    support: dict[tuple[str, ...], set[str]] = defaultdict(set)
    occurrences: dict[tuple[str, ...], list[float]] = defaultdict(list)

    for case_id, group in flow.groupby("case_id", sort=False):
        path = group["activity"].tolist()
        durations = (group["active_s"] + group["idle_s"]).tolist()
        for length in range(MIN_LENGTH, MAX_LENGTH + 1):
            for start in range(len(path) - length + 1):
                pattern = tuple(path[start:start + length])
                if len(set(pattern)) < length:
                    continue  # loops are rework, not routines
                support[pattern].add(case_id)
                occurrences[pattern].append(sum(durations[start:start + length]))

    min_support = max(3, int(flow["case_id"].nunique() * MIN_SUPPORT_SHARE))
    frequent = {pattern: len(cases) for pattern, cases in support.items() if len(cases) >= min_support}
    closed = _closed_patterns(frequent)

    routines = [
        Routine(
            steps=list(pattern),
            occurrences=len(occurrences[pattern]),
            cases=frequent[pattern],
            median_seconds=round(float(pd.Series(occurrences[pattern]).median()), 1),
            hours=round(sum(occurrences[pattern]) / 3600, 2),
        )
        for pattern in closed
    ]
    return sorted(routines, key=lambda routine: routine.hours, reverse=True)[:MAX_ROUTINES]


def _closed_patterns(frequent: dict[tuple[str, ...], int]) -> list[tuple[str, ...]]:
    """Drop patterns that a one-step-longer pattern explains with at least CLOSED_RATIO of the support."""
    best_extension: dict[tuple[str, ...], int] = defaultdict(int)
    for pattern, count in frequent.items():
        if len(pattern) > MIN_LENGTH:
            for shorter in (pattern[:-1], pattern[1:]):
                best_extension[shorter] = max(best_extension[shorter], count)
    return [pattern for pattern, count in frequent.items() if best_extension[pattern] < count * CLOSED_RATIO]
