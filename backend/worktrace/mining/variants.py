"""Process variants and how cases deviate from the main path.

Each case is compared with the most common path using sequence alignment
(difflib). The alignment says *how* a case differs: a skipped step, an extra
step, or one step done instead of another. Counting those over all cases gives
the typical deviations, which says more than "312 unique variants".
"""

from collections import Counter
from difflib import SequenceMatcher

import pandas as pd

from worktrace.schemas import Deviation, Variant, VariantAnalysis

MAX_VARIANTS = 25
MAX_DEVIATIONS = 12
MAX_ALIGNED_VARIANTS = 300


def analyse_variants(flow: pd.DataFrame) -> VariantAnalysis:
    """flow: case-ordered steps with repeats collapsed."""
    cases = flow.groupby("case_id", sort=False).agg(
        path=("activity", tuple),
        start=("start", "min"),
        end=("end", "max"),
    )
    cases["minutes"] = (cases["end"] - cases["start"]).dt.total_seconds() / 60
    total = len(cases)

    grouped = cases.groupby("path").agg(cases=("minutes", "size"), median_minutes=("minutes", "median"))
    grouped = grouped.sort_values("cases", ascending=False)
    main_path = list(grouped.index[0])

    variants, cumulative = [], 0
    for number, (path, row) in enumerate(grouped.head(MAX_VARIANTS).iterrows(), start=1):
        cumulative += row["cases"]
        variants.append(Variant(
            id=number,
            steps=list(path),
            cases=int(row["cases"]),
            share=round(row["cases"] / total, 4),
            cumulative_share=round(cumulative / total, 4),
            median_minutes=round(float(row["median_minutes"]), 1),
            distance_from_main=round(1 - SequenceMatcher(None, main_path, path, autojunk=False).ratio(), 3),
        ))

    return VariantAnalysis(
        total_variants=len(grouped),
        main_path=main_path,
        main_path_share=round(grouped["cases"].iat[0] / total, 4),
        top5_coverage=round(grouped["cases"].head(5).sum() / total, 4),
        variants=variants,
        deviations=_typical_deviations(grouped, main_path, total),
    )


def _typical_deviations(grouped: pd.DataFrame, main_path: list[str], total: int) -> list[Deviation]:
    counts: Counter[tuple[str, str]] = Counter()
    # The long tail of one-off variants adds little but costs a quadratic alignment each.
    for path, row in grouped.head(MAX_ALIGNED_VARIANTS).iterrows():
        found: set[tuple[str, str]] = set()
        matcher = SequenceMatcher(None, main_path, list(path), autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "delete":
                found.update(("skipped", step) for step in main_path[i1:i2])
            elif tag == "insert":
                found.update(("inserted", step) for step in path[j1:j2])
            elif tag == "replace":
                found.update(("replaced", step) for step in path[j1:j2])
        for key in found:
            counts[key] += int(row["cases"])

    return [
        Deviation(kind=kind, activity=activity, cases=cases, share=round(cases / total, 4))
        for (kind, activity), cases in counts.most_common(MAX_DEVIATIONS)
    ]
