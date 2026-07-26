import type { MapEdge, ProcessMap } from "./types";

const START = "__start__";
const END = "__end__";

/**
 * Same rules as `simplify` in backend/worktrace/mining/process_map.py, run live behind the sliders:
 * keep activities seen in at least `activityShare` of cases and paths taken by `pathShare` of cases,
 * let every activity keep its strongest in/out edge, and drop whatever is off the start-to-end paths.
 */
export function simplifyMap(map: ProcessMap, activityShare: number, pathShare: number): ProcessMap {
  const kept = new Set(map.nodes.filter((node) => node.kind !== "activity" || node.cases >= activityShare * map.cases).map((node) => node.id));
  const candidates = map.edges.filter((edge) => kept.has(edge.source) && kept.has(edge.target));
  const best = strongestPerNode(candidates);
  const edges = onStartToEndPaths(candidates.filter((edge) => edge.cases >= pathShare * map.cases || best.has(edge)));
  const connected = new Set(edges.flatMap((edge) => [edge.source, edge.target]));
  return { ...map, nodes: map.nodes.filter((node) => connected.has(node.id)), edges };
}

function strongestPerNode(edges: MapEdge[]): Set<MapEdge> {
  const strongest = new Map<string, MapEdge>();
  for (const edge of edges) {
    for (const key of [`out:${edge.source}`, `in:${edge.target}`]) {
      const current = strongest.get(key);
      if (!current || edge.cases > current.cases) strongest.set(key, edge);
    }
  }
  return new Set(strongest.values());
}

function onStartToEndPaths(edges: MapEdge[]): MapEdge[] {
  const reach = (from: string, next: (edge: MapEdge) => [string, string]) => {
    const seen = new Set([from]);
    const queue = [from];
    while (queue.length) {
      const node = queue.shift()!;
      for (const edge of edges) {
        const [a, b] = next(edge);
        if (a === node && !seen.has(b)) {
          seen.add(b);
          queue.push(b);
        }
      }
    }
    return seen;
  };
  const fromStart = reach(START, (edge) => [edge.source, edge.target]);
  const toEnd = reach(END, (edge) => [edge.target, edge.source]);
  return edges.filter((edge) => fromStart.has(edge.source) && toEnd.has(edge.target) && fromStart.has(edge.target) && toEnd.has(edge.source));
}
