"""Splitting a user's stream of steps into work sessions.

Task mining records everything a person does, all day. Without a usable
Business ID, a whole day of one user used to become a single "case", which made
case durations and variants meaningless. A session ends at a real break: a gap
between steps or long idle time inside a step.
"""

import pandas as pd

SESSION_BREAK = pd.Timedelta(minutes=30)


def assign_sessions(steps: pd.DataFrame) -> pd.Series:
    """Session id per step. Expects steps sorted by user and start, with idle_s per step."""
    previous_end = steps.groupby("user", sort=False)["end"].shift()
    previous_idle = steps.groupby("user", sort=False)["idle_s"].shift().fillna(0)
    gap = steps["start"] - previous_end
    new_session = previous_end.isna() | (gap > SESSION_BREAK) | (previous_idle > SESSION_BREAK.total_seconds())
    number = new_session.astype(int).groupby(steps["user"], sort=False).cumsum()
    return steps["user"].str[:8] + "-s" + number.astype(str).str.zfill(3)
