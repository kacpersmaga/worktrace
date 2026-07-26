"use client";

import clsx from "clsx";
import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import type { EdgeMetric } from "@/components/charts/process-graph";
import { ProcessGraph } from "@/components/charts/process-graph";
import { Panel } from "@/components/ui/panel";
import { appColors } from "@/lib/colors";
import { percent } from "@/lib/format";
import { simplifyMap } from "@/lib/simplify-map";
import type { TabProps } from "./overview-tab";

const BpmnView = dynamic(() => import("@/components/charts/bpmn-view").then((module) => module.BpmnView), { ssr: false });

type View = EdgeMetric | "bpmn";

const VIEWS: { key: View; label: string }[] = [
  { key: "frequency", label: "Frequency" },
  { key: "waiting", label: "Waiting time" },
  { key: "bpmn", label: "BPMN model" },
];

// Slider positions are shares of cases; the scale is non-linear so the useful low end gets room.
const SHARES = [0, 0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.1, 0.15, 0.2, 0.3, 0.5];

interface DialProps {
  label: string;
  hint: string;
  value: number;
  onChange: (value: number) => void;
}

function Dial({ label, hint, value, onChange }: DialProps) {
  return (
    <label className="grid gap-1.5 text-[12px]">
      <span className="flex items-baseline justify-between gap-3">
        <span className="font-medium text-ink">{label}</span>
        <span className="tabular text-ink-3">{SHARES[value] === 0 ? "all" : `≥ ${percent(SHARES[value], SHARES[value] < 0.01 ? 1 : 0)} of cases`}</span>
      </span>
      <input
        type="range"
        min={0}
        max={SHARES.length - 1}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="w-full accent-[var(--accent)]"
        aria-valuetext={`${label}: ${hint}`}
      />
    </label>
  );
}

export function MapTab({ analysis }: TabProps) {
  const [view, setView] = useState<View>("frequency");
  const [activityLevel, setActivityLevel] = useState(SHARES.indexOf(0.05));
  const [pathLevel, setPathLevel] = useState(SHARES.indexOf(0.02));
  const color = useMemo(() => appColors(analysis.apps), [analysis.apps]);
  const highlighted = useMemo(
    () => new Set(analysis.bottlenecks.filter((item) => item.kind === "step" && item.severity === "critical").map((item) => item.activity)),
    [analysis.bottlenecks],
  );
  const map = useMemo(
    () => simplifyMap(analysis.process_map, SHARES[activityLevel], SHARES[pathLevel]),
    [analysis.process_map, activityLevel, pathLevel],
  );
  const shown = map.nodes.filter((node) => node.kind === "activity").length;

  return (
    <Panel
      flush
      title="Process map"
      subtitle={
        view === "bpmn"
          ? "BPMN 2.0 of activities in at least 5% of cases and paths taken by at least 2%, with exclusive gateways where paths split or join."
          : `${shown} of ${analysis.process_map.activities_total} activities and ${map.edges.length} paths. Edges are relations the Heuristics Miner trusts; activities outlined in red are critical bottlenecks.`
      }
      action={
        <div className="flex shrink-0 rounded-lg border border-line bg-surface-2 p-0.5" role="tablist">
          {VIEWS.map((option) => (
            <button
              key={option.key}
              type="button"
              role="tab"
              aria-selected={view === option.key}
              onClick={() => setView(option.key)}
              className={clsx(
                "rounded-md px-2.5 py-1 text-[12px] font-medium transition",
                view === option.key ? "bg-surface text-ink shadow-sm" : "text-ink-3 hover:text-ink",
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      }
    >
      {view !== "bpmn" && (
        <div className="grid gap-4 border-t border-line px-5 py-4 sm:grid-cols-2">
          <Dial label="Activities" hint="how common an activity must be to show" value={activityLevel} onChange={setActivityLevel} />
          <Dial label="Paths" hint="how common a path must be to show" value={pathLevel} onChange={setPathLevel} />
        </div>
      )}
      <div className="h-[70vh] min-h-[520px] border-t border-line">
        {view === "bpmn" ? (
          <BpmnView analysisId={analysis.id} />
        ) : (
          <ProcessGraph map={map} metric={view} color={color} highlighted={highlighted} />
        )}
      </div>
    </Panel>
  );
}
