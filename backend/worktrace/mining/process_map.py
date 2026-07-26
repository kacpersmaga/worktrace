"""A readable process map from a spaghetti of real behaviour.

Real logs connect almost every step to every other step at least once. The map
keeps the edges the Heuristics Miner trusts (a high dependency measure) and
records how many cases use each activity and edge. `simplify` then cuts it down
the way Disco-style tools do, with two dials: how common an activity must be,
and how common a path must be. Every activity keeps its strongest incoming and
outgoing edge, and anything not on a path from start to end is dropped.
The dashboard runs the same simplification live behind two sliders.
"""

import networkx as nx
import pandas as pd

from worktrace.mining.transitions import dependency_measure, directly_follows
from worktrace.schemas import MapEdge, MapNode, ProcessMap

START, END = "__start__", "__end__"
MAX_ACTIVITIES = 30
MIN_DEPENDENCY = 0.5

# Defaults for the exported model: activities in 5% of cases, paths taken by 2% of cases.
BPMN_ACTIVITY_SHARE = 0.05
BPMN_PATH_SHARE = 0.02


def build_process_map(flow: pd.DataFrame) -> ProcessMap:
    """flow: case-ordered steps with repeats collapsed."""
    frequency = flow["activity"].value_counts()
    focused = flow[flow["activity"].isin(frequency.head(MAX_ACTIVITIES).index)]

    dfg = directly_follows(_with_terminals(focused))
    real = ~dfg["activity"].eq(START) & ~dfg["next_activity"].eq(END)
    dfg["dependency"] = 1.0
    dfg.loc[real, "dependency"] = dependency_measure(dfg[real]).to_numpy()
    edges = dfg[(dfg["dependency"] >= MIN_DEPENDENCY) | _best_edges(dfg)]

    cases = int(flow["case_id"].nunique())
    nodes = [_activity_node(name, group) for name, group in focused.groupby("activity")]
    nodes += [
        MapNode(id=START, label="Start", app="", count=cases, cases=cases, median_seconds=0, total_hours=0, kind="start"),
        MapNode(id=END, label="End", app="", count=cases, cases=cases, median_seconds=0, total_hours=0, kind="end"),
    ]
    return ProcessMap(
        nodes=nodes,
        edges=[_edge(row) for row in edges.itertuples()],
        cases=cases,
        activities_total=int(flow["activity"].nunique()),
    )


def simplify(process_map: ProcessMap, activity_share: float, path_share: float) -> ProcessMap:
    """Keep activities seen in at least activity_share of cases and paths taken by path_share of cases."""
    kept = {node.id for node in process_map.nodes if node.kind != "activity" or node.cases >= activity_share * process_map.cases}
    candidates = [edge for edge in process_map.edges if edge.source in kept and edge.target in kept]
    best = _strongest_per_node(candidates)
    edges = [edge for edge in candidates if edge.cases >= path_share * process_map.cases or id(edge) in best]
    edges = _on_start_to_end_paths(edges)
    connected = {edge.source for edge in edges} | {edge.target for edge in edges}
    return process_map.model_copy(update={
        "nodes": [node for node in process_map.nodes if node.id in connected],
        "edges": edges,
    })


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


def _strongest_per_node(edges: list[MapEdge]) -> set[int]:
    strongest: dict[tuple[str, str], MapEdge] = {}
    for edge in edges:
        for key in (("out", edge.source), ("in", edge.target)):
            if key not in strongest or edge.cases > strongest[key].cases:
                strongest[key] = edge
    return {id(edge) for edge in strongest.values()}


def _on_start_to_end_paths(edges: list[MapEdge]) -> list[MapEdge]:
    graph = nx.DiGraph([(edge.source, edge.target) for edge in edges])
    if START not in graph or END not in graph:
        return edges
    keep = (nx.descendants(graph, START) | {START}) & (nx.ancestors(graph, END) | {END})
    return [edge for edge in edges if edge.source in keep and edge.target in keep]


def _activity_node(name: str, rows: pd.DataFrame) -> MapNode:
    durations = rows["active_s"] + rows["idle_s"]
    return MapNode(
        id=name,
        label=name,
        app=str(rows["app"].mode().iat[0]),
        count=len(rows),
        cases=int(rows["case_id"].nunique()),
        median_seconds=round(float(durations.median()), 1),
        total_hours=round(float(durations.sum() / 3600), 2),
    )


def _edge(row) -> MapEdge:
    return MapEdge(
        source=row.activity,
        target=row.next_activity,
        count=int(row.count),
        cases=int(row.cases),
        dependency=round(float(row.dependency), 3),
        median_wait_seconds=round(float(row.median_wait_s), 1),
        p90_wait_seconds=round(float(row.p90_wait_s), 1),
    )
