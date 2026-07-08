"""A readable process map from a spaghetti of real behaviour.

Real logs connect almost every step to every other step at least once. The map
keeps the most frequent activities, then keeps edges the Heuristics Miner trusts
(high dependency) and drops the rest, while making sure every activity stays
reachable from the start and can reach the end.
"""

import networkx as nx
import pandas as pd

from worktrace.mining.transitions import dependency_measure, directly_follows
from worktrace.schemas import MapEdge, MapNode, ProcessMap

START, END = "__start__", "__end__"
MAX_ACTIVITIES = 18
MIN_DEPENDENCY = 0.6
MIN_EDGE_SHARE = 0.01


def build_process_map(flow: pd.DataFrame) -> ProcessMap:
    """flow: case-ordered steps with repeats collapsed."""
    frequency = flow["activity"].value_counts()
    kept = set(frequency.head(MAX_ACTIVITIES).index)
    focused = flow[flow["activity"].isin(kept)]

    dfg = directly_follows(_with_terminals(focused))
    real = ~dfg["activity"].eq(START) & ~dfg["next_activity"].eq(END)
    dfg["dependency"] = 1.0
    dfg.loc[real, "dependency"] = dependency_measure(dfg[real]).to_numpy()

    min_count = max(2, int(dfg["count"].sum() * MIN_EDGE_SHARE / 10))
    strong = (dfg["dependency"] >= MIN_DEPENDENCY) & (dfg["count"] >= min_count)
    edges = dfg[strong | _best_edges(dfg)]
    edges = _drop_unreachable(edges)

    nodes = [_activity_node(name, focused) for name in frequency.index if name in kept]
    nodes = [node for node in nodes if node.id in set(edges["activity"]) | set(edges["next_activity"])]
    cases = flow["case_id"].nunique()
    nodes += [
        MapNode(id=START, label="Start", app="", count=cases, median_seconds=0, total_hours=0, kind="start"),
        MapNode(id=END, label="End", app="", count=cases, median_seconds=0, total_hours=0, kind="end"),
    ]
    return ProcessMap(
        nodes=nodes,
        edges=[_edge(row) for row in edges.itertuples()],
        activities_shown=len(nodes) - 2,
        activities_total=int(flow["activity"].nunique()),
        transitions_covered=round(float(edges["count"].sum() / dfg["count"].sum()), 4),
    )


def _with_terminals(flow: pd.DataFrame) -> pd.DataFrame:
    """Add artificial start and end events so the map shows where cases begin and finish."""
    first = flow.groupby("case_id", sort=False).head(1).copy()
    last = flow.groupby("case_id", sort=False).tail(1).copy()
    first["activity"], first["end"] = START, first["start"]
    last["activity"], last["start"] = END, last["end"]
    framed = pd.concat([first, flow, last], ignore_index=True)
    order = framed["activity"].map({START: 0, END: 2}).fillna(1)
    return framed.assign(_order=order).sort_values(["case_id", "start", "_order"]).drop(columns="_order")


def _best_edges(dfg: pd.DataFrame) -> pd.Series:
    """Every activity keeps its most frequent incoming and outgoing edge, so nothing floats alone."""
    best_out = dfg.groupby("activity")["count"].transform("max") == dfg["count"]
    best_in = dfg.groupby("next_activity")["count"].transform("max") == dfg["count"]
    return best_out | best_in


def _drop_unreachable(edges: pd.DataFrame) -> pd.DataFrame:
    graph = nx.DiGraph(list(zip(edges["activity"], edges["next_activity"])))
    if START not in graph or END not in graph:
        return edges
    reachable = nx.descendants(graph, START) | {START}
    finishing = nx.ancestors(graph, END) | {END}
    keep = reachable & finishing
    return edges[edges["activity"].isin(keep) & edges["next_activity"].isin(keep)]


def _activity_node(name: str, flow: pd.DataFrame) -> MapNode:
    rows = flow[flow["activity"] == name]
    durations = rows["active_s"] + rows["idle_s"]
    return MapNode(
        id=name,
        label=name,
        app=str(rows["app"].mode().iat[0]),
        count=len(rows),
        median_seconds=round(float(durations.median()), 1),
        total_hours=round(float(durations.sum() / 3600), 2),
    )


def _edge(row) -> MapEdge:
    return MapEdge(
        source=row.activity,
        target=row.next_activity,
        count=int(row.count),
        dependency=round(float(row.dependency), 3),
        median_wait_seconds=round(float(row.median_wait_s), 1),
        p90_wait_seconds=round(float(row.p90_wait_s), 1),
    )
