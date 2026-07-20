"""Cleaning and filling in Business IDs.

In task-mining exports the Business ID comes from OCR and an AI extractor. Most
steps have none (NOT_FOUND), and some of the IDs that are found are noise: a
login name or a stray number read off the screen. Two steps fix that:

1. Shape voting. Every ID is reduced to its shape ("PRO-18472" -> "AAA-99999").
   Real case IDs in one process share a shape. A shape survives only if it is
   at least half as common as the most common one; the rest is noise.
2. Case attribution. People juggle cases: an invoice waits for approval
   while others are processed, then gets posted between two unrelated ones.
   So a step without an ID is not simply given to its neighbours. A first-order
   Markov model of the process is learned from the steps whose case is certain,
   and each untagged step joins the case most likely to continue with it:
     - one of the user's open cases, scored P(step | the case's last activity);
     - or the case that starts right after it, scored P(its first step | step)
       when the step is a plausible way to start a case.
   Ties go to the case the next tagged step belongs to, then to the case that
   has waited longest. Below MIN_PROBABILITY the step stays unassigned
   rather than being forced into a case.
"""

import re
from collections import Counter

import pandas as pd

MISSING_MARKERS = {"", "NOT_FOUND", "NONE", "NULL", "NAN", "N/A", "-1", "0"}
MIN_SHAPE_RATIO = 0.5
MIN_ID_LENGTH = 4
MAX_FILL_GAP = pd.Timedelta(minutes=10)
MAX_OPEN = pd.Timedelta(days=7)
MIN_PROBABILITY = 0.05
START, END = "<start>", "<end>"


def id_shape(value: str) -> str:
    """"INV-2026-00481" -> "AAA-9999-99999"; similar IDs get the same shape."""
    return re.sub(r"[A-Za-z]", "A", re.sub(r"\d", "9", value))


def clean_business_ids(raw: pd.Series) -> tuple[pd.Series, list[str]]:
    """Keep only IDs that look like the dominant ID format. Returns cleaned IDs and rejected values."""
    values = raw.fillna("").astype(str).str.strip()
    candidate = ~values.str.upper().isin(MISSING_MARKERS) & values.str.contains(r"\d") & (values.str.len() >= MIN_ID_LENGTH)
    shapes = Counter(values[candidate].map(id_shape))
    top = max(shapes.values(), default=0)
    accepted_shapes = {shape for shape, count in shapes.items() if count >= top * MIN_SHAPE_RATIO}

    accepted = candidate & values.map(id_shape).isin(accepted_shapes)
    present = ~values.str.upper().isin(MISSING_MARKERS)
    rejected = sorted(set(values[present & ~accepted]))
    return values.where(accepted), rejected


def impute_business_ids(steps: pd.DataFrame) -> tuple[pd.Series, int]:
    """Attribute steps without an ID to cases. Expects user, activity, start, end, business_id, sorted by user and start."""
    model = transition_model(steps[steps["business_id"].notna()])
    filled = steps["business_id"].copy()
    for _, rows in steps.groupby("user", sort=False):
        _attribute_user_steps(rows, filled, model)
    return filled, int((filled.notna() & steps["business_id"].isna()).sum())


def transition_model(tagged: pd.DataFrame) -> dict[tuple[str, str], float]:
    """P(next | activity) within cases, including START -> first activity and last activity -> END."""
    ordered = tagged.sort_values(["business_id", "start"])
    by_case = ordered.groupby("business_id", sort=False)["activity"]
    before = by_case.shift(1).fillna(START)
    after = by_case.shift(-1).fillna(END)
    pairs = pd.concat([
        pd.DataFrame({"from": before, "to": ordered["activity"]}),
        pd.DataFrame({"from": ordered["activity"], "to": after})[after == END],
    ])
    counts = pairs.value_counts()
    return (counts / counts.groupby(level="from").transform("sum")).to_dict()


def _attribute_user_steps(rows: pd.DataFrame, filled: pd.Series, model: dict[tuple[str, str], float]) -> None:
    tagged = rows["business_id"].notna()
    next_id = rows["business_id"].bfill()
    next_activity = rows["activity"].where(tagged).bfill()
    next_start = rows["start"].where(tagged).bfill()
    open_cases: dict[str, tuple[str, pd.Timestamp]] = {}  # case -> (last activity, when it ended)

    columns = zip(rows.index, rows["business_id"], rows["activity"], rows["start"], rows["end"], next_id, next_activity, next_start)
    for index, case_id, activity, start, end, following_id, following_activity, following_start in columns:
        if pd.notna(case_id):
            open_cases[case_id] = (activity, end)
            continue
        upcoming = following_id if pd.notna(following_id) and following_start - end <= MAX_FILL_GAP else None
        case = _most_likely_case(activity, start, open_cases, upcoming, following_activity, model)
        if case is not None:
            filled[index] = case
            open_cases[case] = (activity, end)


def _most_likely_case(activity: str, start: pd.Timestamp, open_cases: dict[str, tuple[str, pd.Timestamp]],
                      upcoming: str | None, upcoming_activity: str | None, model: dict[tuple[str, str], float]) -> str | None:
    scored = []
    for case, (last_activity, last_end) in open_cases.items():
        if start - last_end > MAX_OPEN:
            continue
        probability = model.get((last_activity, activity), 0.0)
        scored.append((probability, case == upcoming, -last_end.value, case))
    if upcoming is not None and upcoming not in open_cases and model.get((START, activity), 0.0) >= MIN_PROBABILITY:
        scored.append((model.get((activity, upcoming_activity), 0.0), True, 0, upcoming))
    if not scored:
        return None
    probability, _, _, case = max(scored)
    return case if probability >= MIN_PROBABILITY else None
