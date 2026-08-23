"""Directly-follows relations: which step comes right after which, and how long the hand-over takes."""

import pandas as pd


def collapse_repeats(steps: pd.DataFrame) -> pd.DataFrame:
    """Merge back-to-back steps of the same activity in a case (A, A, B -> A, B).

    Task mining splits one activity into many steps when a window loses focus for a
    second. Merging them keeps durations right and stops fake self-loops.
    """
    same_as_previous = (steps["case_id"] == steps["case_id"].shift()) & (steps["activity"] == steps["activity"].shift())
    block = (~same_as_previous).cumsum()
    sums = ["active_s", "idle_s", "clicks", "keys", "copies", "pastes", "cuts",
            "typing_s", "clicking_s", "clipboard_s", "looking_s", "no_input_s"]
    merged = steps.groupby(block, sort=False).agg(
        {"case_id": "first", "activity": "first", "user": "first", "app": "first", "view": "first",
         "start": "first", "end": "max", **{column: "sum" for column in sums}}
    )
    return merged.reset_index(drop=True)


def with_successors(steps: pd.DataFrame) -> pd.DataFrame:
    """Add next_activity and wait_s (gap until the next step of the same case) to case-ordered steps."""
    steps = steps.copy()
    by_case = steps.groupby("case_id", sort=False)
    steps["next_activity"] = by_case["activity"].shift(-1)
    next_start = by_case["start"].shift(-1)
    steps["wait_s"] = (next_start - steps["end"]).dt.total_seconds().clip(lower=0)
    return steps


def directly_follows(steps: pd.DataFrame) -> pd.DataFrame:
    """One row per (activity, next_activity) with frequency and hand-over waiting times."""
    pairs = with_successors(steps).dropna(subset=["next_activity"])
    grouped = pairs.groupby(["activity", "next_activity"])
    return grouped.agg(
        count=("wait_s", "size"),
        cases=("case_id", "nunique"),
        median_wait_s=("wait_s", "median"),
        p90_wait_s=("wait_s", lambda waits: waits.quantile(0.9)),
        total_wait_s=("wait_s", "sum"),
    ).reset_index()


def dependency_measure(dfg: pd.DataFrame) -> pd.Series:
    """Heuristics Miner dependency a => b: (|a>b| - |b>a|) / (|a>b| + |b>a| + 1).

    Close to 1 when b reliably follows a and rarely the other way round; near 0
    for steps that just happen to interleave. Self-loops use |a>a| / (|a>a| + 1).
    """
    forward = dfg.set_index(["activity", "next_activity"])["count"]
    backward = forward.copy()
    backward.index = backward.index.swaplevel()
    backward = backward.reindex(forward.index, fill_value=0)
    loops = forward.index.get_level_values(0) == forward.index.get_level_values(1)
    measure = (forward - backward) / (forward + backward + 1)
    measure[loops] = forward[loops] / (forward[loops] + 1)
    return pd.Series(measure.to_numpy(), index=dfg.index)
