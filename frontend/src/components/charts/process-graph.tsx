"use client";

import dagre from "@dagrejs/dagre";
import {
  Background,
  BaseEdge,
  Controls,
  EdgeLabelRenderer,
  type Edge,
  type EdgeProps,
  getBezierPath,
  Handle,
  type Node,
  type NodeProps,
  Position,
  ReactFlow,
  type ReactFlowInstance,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useEffect, useMemo, useRef } from "react";
import { count, duration } from "@/lib/format";
import type { MapEdge, ProcessMap } from "@/lib/types";

export type EdgeMetric = "frequency" | "waiting";

interface ActivityData extends Record<string, unknown> {
  label: string;
  app: string;
  count: number;
  median: number;
  color: string;
  kind: "start" | "end" | "activity";
  highlighted: boolean;
}

interface FlowData extends Record<string, unknown> {
  edge: MapEdge;
  metric: EdgeMetric;
  weight: number;
}

const NODE_WIDTH = 210;
const NODE_HEIGHT = 58;

function ActivityNode({ data }: NodeProps<Node<ActivityData>>) {
  if (data.kind !== "activity") {
    return (
      <div className="grid size-10 place-items-center rounded-full border-2 border-ink bg-surface text-[11px] font-semibold uppercase text-ink">
        {data.kind === "start" ? "▶" : "■"}
        <Handle type="target" position={Position.Top} className="!opacity-0" />
        <Handle type="source" position={Position.Bottom} className="!opacity-0" />
      </div>
    );
  }
  return (
    <div
      className="rounded-xl border bg-surface px-3 py-2 shadow-[var(--shadow)]"
      style={{ width: NODE_WIDTH, borderColor: data.highlighted ? "var(--critical)" : "var(--line)" }}
    >
      <Handle type="target" position={Position.Top} className="!opacity-0" />
      <div className="truncate text-[12px] font-semibold text-ink" title={data.label}>
        {data.label}
      </div>
      <div className="mt-1 flex items-center gap-1.5 text-[11px] text-ink-3">
        <span className="size-2 shrink-0 rounded-full" style={{ background: data.color }} />
        <span className="truncate">{data.app}</span>
        <span className="tabular ml-auto shrink-0">
          {count(data.count)} · {duration(data.median)}
        </span>
      </div>
      <Handle type="source" position={Position.Bottom} className="!opacity-0" />
    </div>
  );
}

function FlowEdge({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data, markerEnd }: EdgeProps<Edge<FlowData>>) {
  const [path, labelX, labelY] = getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition });
  if (!data) return null;
  const waiting = data.metric === "waiting";
  const label = waiting ? duration(data.edge.median_wait_seconds) : count(data.edge.count);
  const stroke = waiting ? "var(--series-2)" : "var(--accent)";
  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        markerEnd={markerEnd}
        style={{ stroke, strokeWidth: 1 + data.weight * 5, opacity: 0.35 + data.weight * 0.6 }}
      />
      {data.weight > 0.12 && (
        <EdgeLabelRenderer>
          <span
            className="tabular pointer-events-none absolute rounded-md border border-line bg-surface px-1.5 py-0.5 text-[11px] font-medium text-ink-2"
            style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
          >
            {label}
          </span>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

const nodeTypes = { activity: ActivityNode };
const edgeTypes = { flow: FlowEdge };

interface ProcessGraphProps {
  map: ProcessMap;
  metric: EdgeMetric;
  color: (app: string) => string;
  highlighted: Set<string>;
}

const READABLE_ZOOM = 0.7;

export function ProcessGraph({ map, metric, color, highlighted }: ProcessGraphProps) {
  const { nodes, edges } = useMemo(() => layout(map, metric, color, highlighted), [map, metric, color, highlighted]);
  const container = useRef<HTMLDivElement>(null);
  const flow = useRef<ReactFlowInstance<Node<ActivityData>, Edge<FlowData>> | null>(null);

  // Fit the whole map when it is small enough to stay readable; otherwise start at the top at a readable zoom.
  const frame = useCallback(() => {
    const instance = flow.current;
    const box = container.current?.getBoundingClientRect();
    if (!instance || !box || nodes.length === 0) return;
    const xs = nodes.map((node) => node.position.x);
    const width = Math.max(...xs) - Math.min(...xs) + NODE_WIDTH;
    const height = Math.max(...nodes.map((node) => node.position.y)) + NODE_HEIGHT;
    const zoom = Math.min(1, (box.width - 48) / width, (box.height - 48) / height);
    if (zoom >= READABLE_ZOOM) {
      instance.fitView({ padding: 0.08, maxZoom: 1 });
      return;
    }
    const scale = Math.max(READABLE_ZOOM, Math.min(1, (box.width - 48) / width));
    instance.setViewport({ x: (box.width - width * scale) / 2 - Math.min(...xs) * scale, y: 24, zoom: scale });
  }, [nodes]);

  useEffect(frame, [frame]);

  return (
    <div ref={container} className="h-full w-full">
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      onInit={(instance) => {
        flow.current = instance;
        frame();
      }}
      minZoom={0.2}
      nodesDraggable
      nodesConnectable={false}
      proOptions={{ hideAttribution: true }}
    >
      <Background gap={20} size={1} color="var(--line)" />
      <Controls showInteractive={false} position="bottom-right" />
    </ReactFlow>
    </div>
  );
}

function layout(map: ProcessMap, metric: EdgeMetric, color: (app: string) => string, highlighted: Set<string>) {
  const graph = new dagre.graphlib.Graph();
  graph.setGraph({ rankdir: "TB", nodesep: 40, ranksep: 56 });
  graph.setDefaultEdgeLabel(() => ({}));
  map.nodes.forEach((node) =>
    graph.setNode(node.id, node.kind === "activity" ? { width: NODE_WIDTH, height: NODE_HEIGHT } : { width: 40, height: 40 }),
  );
  map.edges.forEach((edge) => graph.setEdge(edge.source, edge.target));
  dagre.layout(graph);

  const value = (edge: MapEdge) => (metric === "waiting" ? edge.median_wait_seconds : edge.count);
  const max = Math.max(...map.edges.map(value), 1e-9);

  const nodes: Node<ActivityData>[] = map.nodes.map((node) => {
    const position = graph.node(node.id);
    const size = node.kind === "activity" ? { w: NODE_WIDTH, h: NODE_HEIGHT } : { w: 40, h: 40 };
    return {
      id: node.id,
      type: "activity",
      position: { x: position.x - size.w / 2, y: position.y - size.h / 2 },
      data: {
        label: node.label,
        app: node.app,
        count: node.count,
        median: node.median_seconds,
        color: color(node.app),
        kind: node.kind,
        highlighted: highlighted.has(node.id),
      },
    };
  });
  const edges: Edge<FlowData>[] = map.edges.map((edge) => ({
    id: `${edge.source}->${edge.target}`,
    source: edge.source,
    target: edge.target,
    type: "flow",
    data: { edge, metric, weight: Math.sqrt(value(edge) / max) },
  }));
  return { nodes, edges };
}
