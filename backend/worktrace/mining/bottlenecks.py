"""Bottleneck detection that weighs evidence instead of applying one threshold.

The hackathon version flagged the transition with the longest *average* wait,
so a single overnight gap seen once came out as "critical". Here two kinds of
bottleneck are scored from several independent signals:

Steps, where the work itself is slow:
  - time tied up       total hours spent in the step (impact, not just slowness)
  - idle share         part of the step spent waiting with no input
  - long tail          p90 / median duration; unstable steps are the ones to fix
  - rework             share of cases that come back to the step
  - centrality         betweenness in the process graph; a slow step every path
                       goes through blocks more work than one on a side branch

Hand-overs, where work waits between two steps of a case:
  - waiting hours      total time cases spent between A and B
  - median wait        how long a typical case waits there

Each signal becomes a percentile rank among the candidates of the same kind,
and the score is their weighted average. The kinds are not ranked against each
other: work time and calendar waiting time are different units, and an hour
of waiting overnight is not an hour of someone's work. Severity also needs
absolute weight: a step must hold a real share of the tracked time, and a
hand-over must sit on the path of a real share of cases. The ranks are returned with the score, so every
number on screen can say why it is there.
"""

import networkx as nx
import pandas as pd

from worktrace.mining.rework import rework_rate_by_activity
from worktrace.mining.scoring import (
    decimal, hours, human_duration, make_signals, percent, percentile_ranks, severity, times, weighted_score,
)
from worktrace.mining.transitions import directly_follows
from worktrace.schemas import Bottleneck, Severity

MIN_EXECUTIONS = 5
MIN_HANDOVER_WAIT_S = 300
MAX_BOTTLENECKS = 15
SEVERITY_ORDER: list[Severity] = ["critical", "high", "medium", "low"]
# (minimum share, highest severity allowed below it): of tracked time for steps, of cases for hand-overs
STEP_CEILINGS: list[tuple[float, Severity]] = [(0.01, "low"), (0.03, "medium"), (0.08, "high")]
HANDOVER_CEILINGS: list[tuple[float, Severity]] = [(0.02, "low"), (0.05, "medium"), (0.15, "high")]

STEP_WEIGHTS = {"hours": 0.35, "idle_share": 0.15, "tail": 0.15, "rework": 0.2, "centrality": 0.15}
STEP_LABELS = {
    "hours": "Time tied up",
    "idle_share": "Idle inside the step",
    "tail": "Slowest 10% vs median",
    "rework": "Cases that repeat it",
    "centrality": "Paths running through it",
}
STEP_FORMATS = {"hours": hours, "idle_share": percent, "tail": times, "rework": percent, "centrality": decimal}

HANDOVER_WEIGHTS = {"hours": 0.45, "median_wait": 0.3, "reach": 0.25}
HANDOVER_LABELS = {"hours": "Waiting in total (calendar)", "median_wait": "Typical wait", "reach": "Cases passing through"}
HANDOVER_FORMATS = {"hours": lambda value: f"{value / 24:,.0f} days", "median_wait": human_duration, "reach": percent}


def detect_bottlenecks(flow: pd.DataFrame, cases_are_sessions: bool = False) -> list[Bottleneck]:
    """flow: case-ordered steps with repeats collapsed.

    When cases are work sessions, coming back to an activity is ordinary
    multitasking rather than rework, so the rework signal is left out.
    """
    steps = _step_measurements(flow)
    handovers = _handover_measurements(flow)
    if steps.empty and handovers.empty:
        return []

    found = []
    if not steps.empty:
        ranks = steps.drop(columns=["occurrences", "cases", "median_s", "p90_s"]).apply(percentile_ranks)
        weights = STEP_WEIGHTS | ({"rework": 0.0} if cases_are_sessions else {})
        steps["score"] = weighted_score(ranks, weights)
        tracked_hours = (flow["active_s"] + flow["idle_s"]).sum() / 3600
        for name, row in steps.iterrows():
            bottleneck = _step_bottleneck(name, row, ranks.loc[name], cases_are_sessions)
            bottleneck.severity = _cap(bottleneck.severity, row["hours"] / tracked_hours, STEP_CEILINGS)
            found.append(bottleneck)
    if not handovers.empty:
        ranks = handovers[list(HANDOVER_WEIGHTS)].apply(percentile_ranks)
        handovers["score"] = weighted_score(ranks, HANDOVER_WEIGHTS)
        for key, row in handovers.iterrows():
            bottleneck = _handover_bottleneck(key, row, ranks.loc[key])
            bottleneck.severity = _cap(bottleneck.severity, row["reach"], HANDOVER_CEILINGS)
            found.append(bottleneck)
    return sorted(found, key=lambda bottleneck: bottleneck.score, reverse=True)[:MAX_BOTTLENECKS]


def _cap(level: Severity, share: float, ceilings: list[tuple[float, Severity]]) -> Severity:
    """A high rank alone is not enough: the worst levels need real weight behind them."""
    for minimum_share, ceiling in ceilings:
        if share < minimum_share and SEVERITY_ORDER.index(level) < SEVERITY_ORDER.index(ceiling):
            return ceiling
    return level


def _step_measurements(flow: pd.DataFrame) -> pd.DataFrame:
    flow = flow.assign(duration_s=flow["active_s"] + flow["idle_s"])
    grouped = flow.groupby("activity")
    steps = grouped.agg(
        occurrences=("duration_s", "size"),
        cases=("case_id", "nunique"),
        median_s=("duration_s", "median"),
        p90_s=("duration_s", lambda durations: durations.quantile(0.9)),
        total_s=("duration_s", "sum"),
        idle_s=("idle_s", "sum"),
    )
    steps = steps[steps["occurrences"] >= MIN_EXECUTIONS]
    measured = pd.DataFrame(index=steps.index)
    measured["hours"] = steps["total_s"] / 3600
    measured["idle_share"] = (steps["idle_s"] / steps["total_s"].where(steps["total_s"] > 0)).fillna(0)
    measured["tail"] = steps["p90_s"] / steps["median_s"].clip(lower=1)
    measured["rework"] = rework_rate_by_activity(flow).reindex(steps.index).fillna(0)
    measured["centrality"] = _betweenness(flow).reindex(steps.index).fillna(0)
    return measured.join(steps[["occurrences", "cases", "median_s", "p90_s"]])


def _betweenness(flow: pd.DataFrame) -> pd.Series:
    """Betweenness centrality on the directly-follows graph; frequent edges count as short distances."""
    dfg = directly_follows(flow)
    graph = nx.DiGraph()
    for row in dfg.itertuples():
        if row.activity != row.next_activity:
            graph.add_edge(row.activity, row.next_activity, distance=1 / row.count)
    if graph.number_of_nodes() < 3:
        return pd.Series(dtype=float)
    return pd.Series(nx.betweenness_centrality(graph, weight="distance", normalized=True))


def _handover_measurements(flow: pd.DataFrame) -> pd.DataFrame:
    dfg = directly_follows(flow)
    dfg = dfg[(dfg["count"] >= MIN_EXECUTIONS) & (dfg["median_wait_s"] >= MIN_HANDOVER_WAIT_S)]
    dfg = dfg[dfg["activity"] != dfg["next_activity"]]
    measured = pd.DataFrame({
        "hours": dfg["total_wait_s"].to_numpy() / 3600,
        "median_wait": dfg["median_wait_s"].to_numpy(),
        "p90_wait": dfg["p90_wait_s"].to_numpy(),
        "occurrences": dfg["count"].to_numpy(),
        "cases": dfg["cases"].to_numpy(),
        "reach": dfg["cases"].to_numpy() / flow["case_id"].nunique(),
    }, index=pd.MultiIndex.from_frame(dfg[["activity", "next_activity"]]))
    return measured


def _step_bottleneck(activity: str, row: pd.Series, ranks: pd.Series, cases_are_sessions: bool) -> Bottleneck:
    evidence = [f"{row['hours']:.1f} h spent in this step across {int(row['occurrences'])} executions."]
    if ranks["tail"] >= 0.7 and row["tail"] >= 2:
        evidence.append(
            f"The slowest 10% take {human_duration(row['p90_s'])}, {row['tail']:.1f}x the median of {human_duration(row['median_s'])}."
        )
    if row["rework"] >= 0.1 and not cases_are_sessions:
        evidence.append(f"Repeated within the same case in {row['rework']:.0%} of cases.")
    if row["idle_share"] >= 0.15:
        evidence.append(f"{row['idle_share']:.0%} of the time in this step has no keyboard or mouse input.")
    if ranks["centrality"] >= 0.75:
        evidence.append("Sits on many of the paths through the process, so delays here hold up most cases.")

    return Bottleneck(
        kind="step",
        activity=activity,
        score=round(float(row["score"]), 1),
        severity=severity(row["score"]),
        hours_lost=round(float(row["hours"]), 2),
        median_seconds=round(float(row["median_s"]), 1),
        p90_seconds=round(float(row["p90_s"]), 1),
        occurrences=int(row["occurrences"]),
        cases=int(row["cases"]),
        signals=make_signals(row, ranks, _without_rework(STEP_LABELS, cases_are_sessions), STEP_FORMATS),
        evidence=evidence,
    )


def _handover_bottleneck(key: tuple[str, str], row: pd.Series, ranks: pd.Series) -> Bottleneck:
    source, target = key
    evidence = [
        f"Cases wait a median of {human_duration(row['median_wait'])} between these steps, "
        f"{human_duration(row['p90_wait'])} for the slowest 10%.",
        f"{row['hours'] / 24:,.0f} days of calendar time spent waiting here, over {int(row['occurrences']):,} hand-overs "
        f"({row['reach']:.0%} of cases).",
    ]
    return Bottleneck(
        kind="handover",
        activity=source,
        next_activity=target,
        score=round(float(row["score"]), 1),
        severity=severity(row["score"]),
        hours_lost=round(float(row["hours"]), 2),
        median_seconds=round(float(row["median_wait"]), 1),
        p90_seconds=round(float(row["p90_wait"]), 1),
        occurrences=int(row["occurrences"]),
        cases=int(row["cases"]),
        signals=make_signals(row, ranks, HANDOVER_LABELS, HANDOVER_FORMATS),
        evidence=evidence,
    )



def _without_rework(labels: dict[str, str], cases_are_sessions: bool) -> dict[str, str]:
    return {key: label for key, label in labels.items() if not (cases_are_sessions and key == "rework")}
