"use client";

import clsx from "clsx";
import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import type { EdgeMetric } from "@/components/charts/process-graph";
import { ProcessGraph } from "@/components/charts/process-graph";
import { Panel } from "@/components/ui/panel";
import { appColors } from "@/lib/colors";
import { percent } from "@/lib/format";
import type { TabProps } from "./overview-tab";

const BpmnView = dynamic(() => import("@/components/charts/bpmn-view").then((module) => module.BpmnView), { ssr: false });

type View = EdgeMetric | "bpmn";

const VIEWS: { key: View; label: string }[] = [
  { key: "frequency", label: "Frequency" },
  { key: "waiting", label: "Waiting time" },
  { key: "bpmn", label: "BPMN model" },
];

export function MapTab({ analysis }: TabProps) {
  const [view, setView] = useState<View>("frequency");
  const color = useMemo(() => appColors(analysis.apps), [analysis.apps]);
  const highlighted = useMemo(
    () => new Set(analysis.bottlenecks.filter((item) => item.kind === "step" && item.severity === "critical").map((item) => item.activity)),
    [analysis.bottlenecks],
  );
  const map = analysis.process_map;

  return (
    <Panel
      flush
      title="Process map"
      subtitle={
        <>
          {map.activities_shown} of {map.activities_total} activities, the {percent(map.transitions_covered)} of transitions the
          Heuristics Miner trusts (dependency ≥ 0.6). Activities outlined in red are critical bottlenecks.
        </>
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
      <div className="h-[72vh] min-h-[520px] border-t border-line">
        {view === "bpmn" ? (
          <BpmnView analysisId={analysis.id} />
        ) : (
          <ProcessGraph map={map} metric={view} color={color} highlighted={highlighted} />
        )}
      </div>
    </Panel>
  );
}
