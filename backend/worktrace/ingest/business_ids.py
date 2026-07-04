"""Cleaning and filling in Business IDs.

In task-mining exports the Business ID comes from OCR and an AI extractor. Most
steps have none (NOT_FOUND), and some of the IDs that are found are noise: a
login name or a stray number read off the screen. Two steps fix that:

1. Shape voting. Every ID is reduced to its shape ("PRO-18472" -> "AAA-99999").
   Real case IDs in one process share a shape. A shape survives only if it is
   at least half as common as the most common one; the rest is noise.
2. Imputation. A step without an ID that sits between two steps of the same
   user carrying the same ID (and close in time) belongs to that case, the way
   a person reading the log would assume. A step between two *different* cases
   goes to the neighbour that does not have that activity yet: the "Open email"
   right before a new invoice's first tagged step starts the new invoice, it
   does not repeat the previous one.
"""

import re
from collections import Counter

import pandas as pd

MISSING_MARKERS = {"", "NOT_FOUND", "NONE", "NULL", "NAN", "N/A", "-1", "0"}
MIN_SHAPE_RATIO = 0.5
MIN_ID_LENGTH = 4
MAX_FILL_GAP = pd.Timedelta(minutes=10)


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
    """Fill steps without an ID from the surrounding steps of the same user.

    Expects columns user, activity, start, end, business_id (NaN where unknown),
    sorted by user and start.
    """
    ids = steps["business_id"]
    by_user = steps.groupby("user", sort=False)
    previous_id = by_user["business_id"].ffill()
    next_id = by_user["business_id"].bfill()
    previous_seen = steps["end"].where(ids.notna()).groupby(steps["user"]).ffill()
    next_seen = steps["start"].where(ids.notna()).groupby(steps["user"]).bfill()
    near_previous = steps["start"] - previous_seen <= MAX_FILL_GAP
    near_next = next_seen - steps["end"] <= MAX_FILL_GAP

    known = set(zip(ids.dropna(), steps.loc[ids.notna(), "activity"]))
    previous_has = pd.Series([pair in known for pair in zip(previous_id, steps["activity"])], index=steps.index)
    next_has = pd.Series([pair in known for pair in zip(next_id, steps["activity"])], index=steps.index)

    missing = ids.isna()
    enclosed = missing & previous_id.notna() & (previous_id == next_id) & near_previous & near_next
    to_next = missing & ~enclosed & next_id.notna() & near_next & ~next_has & (previous_has | ~near_previous)
    to_previous = missing & ~enclosed & ~to_next & previous_id.notna() & near_previous & ~previous_has & next_has

    filled = ids.where(~(enclosed | to_previous), previous_id).where(~to_next, next_id)
    return filled, int((enclosed | to_next | to_previous).sum())
