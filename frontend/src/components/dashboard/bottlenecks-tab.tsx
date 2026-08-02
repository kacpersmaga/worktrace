"use client";

import clsx from "clsx";
import { ArrowRight, ChevronDown, Hourglass, Timer } from "lucide-react";
import { useState } from "react";
import { ExplainButton } from "@/components/ui/explain-button";
import { Hint } from "@/components/ui/hint";
import { Panel } from "@/components/ui/panel";
import { SeverityBadge } from "@/components/ui/severity-badge";
import { SignalBars } from "@/components/ui/signal-bars";
import { count, duration, hours } from "@/lib/format";
import type { Bottleneck } from "@/lib/types";
import type { TabProps } from "./overview-tab";

const SCORE_HINT =
  "0–100. Each signal is ranked against every other step or hand-over, and the score is a weighted average of those ranks. Severity also needs real hours behind it: a step under 3% of tracked time cannot be critical.";

export function BottlenecksTab({ analysis }: TabProps) {
  const [open, setOpen] = useState(0);
  const sessions = analysis.quality.case_strategy === "work_session";

  return (
    <div className="grid gap-6">
      <Panel
        flush
        title="Ranked bottlenecks"
        subtitle="Slow steps and slow hand-overs between steps, ranked by the evidence behind them. Open a row to see why."
      >
        <ol className="divide-y divide-line border-t border-line">
          {analysis.bottlenecks.map((bottleneck, index) => (
            <BottleneckRow
              key={`${bottleneck.activity}-${bottleneck.next_activity}`}
              analysisId={analysis.id}
              bottleneck={bottleneck}
              index={index}
              open={open === index}
              onToggle={() => setOpen(open === index ? -1 : index)}
            />
          ))}
        </ol>
      </Panel>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="How the score works">
          <dl className="grid gap-3 text-[13px] leading-relaxed text-ink-2">
            <div>
              <dt className="flex items-center gap-1.5 font-medium text-ink">
                <Timer className="size-4 text-ink-3" aria-hidden /> Step bottlenecks
              </dt>
              <dd className="mt-1">
                Time tied up (35%), rework{sessions ? " (off: cases are work sessions)" : " (20%)"}, long tail p90/median (15%),
                idle share (15%) and betweenness centrality on the process graph (15%).
              </dd>
            </div>
            <div>
              <dt className="flex items-center gap-1.5 font-medium text-ink">
                <Hourglass className="size-4 text-ink-3" aria-hidden /> Hand-over bottlenecks
              </dt>
              <dd className="mt-1">
                Total waiting hours (45%), typical wait (30%) and the share of cases passing through (25%). Only hand-overs
                with a typical wait of 5 minutes or more qualify.
              </dd>
            </div>
          </dl>
        </Panel>
        <Panel title="Unusual cases" subtitle="Isolation Forest over case duration, steps, rework, waiting and apps.">
          {analysis.anomalies.length === 0 ? (
            <p className="text-[13px] text-ink-3">Needs at least 30 cases; nothing stood out here.</p>
          ) : (
            <ul className="grid gap-3">
              {analysis.anomalies.slice(0, 5).map((anomaly) => (
                <li key={anomaly.case_id} className="text-[13px]">
                  <div className="flex justify-between gap-2">
                    <span className="truncate font-medium text-ink">{anomaly.case_id}</span>
                    <span className="shrink-0 text-ink-3">{anomaly.user}</span>
                  </div>
                  <p className="mt-0.5 leading-relaxed text-ink-2">{anomaly.reasons[0]}</p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  );
}

interface RowProps {
  analysisId: string;
  bottleneck: Bottleneck;
  index: number;
  open: boolean;
  onToggle: () => void;
}

function BottleneckRow({ analysisId, bottleneck, index, open, onToggle }: RowProps) {
  const handover = bottleneck.kind === "handover";
  return (
    <li>
      <button type="button" onClick={onToggle} aria-expanded={open} className="flex w-full items-center gap-4 px-5 py-4 text-left hover:bg-surface-2/60">
        <span className="tabular w-5 shrink-0 text-[12px] text-ink-3">{index + 1}</span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[14px] font-semibold tracking-tight text-ink">
            {bottleneck.activity}
            {handover && (
              <>
                <ArrowRight className="size-3.5 text-ink-3" aria-hidden />
                {bottleneck.next_activity}
              </>
            )}
          </span>
          <span className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-ink-3">
            <span>{handover ? "Waiting between steps" : "Slow step"}</span>
            <span>
              {handover ? "typical wait" : "median"} {duration(bottleneck.median_seconds)}
            </span>
            <span>{count(bottleneck.occurrences)}× in {count(bottleneck.cases)} cases</span>
          </span>
        </span>
        <span className="hidden text-right sm:block">
          <span className="tabular block text-[15px] font-semibold text-ink">
            {handover ? `${count(Math.round(bottleneck.hours_lost / 24))} days` : hours(bottleneck.hours_lost)}
          </span>
          <span className="block text-[11px] text-ink-3">{handover ? "waited in total" : "of work in step"}</span>
        </span>
        <span className="flex w-24 shrink-0 flex-col items-end gap-1.5">
          <SeverityBadge severity={bottleneck.severity} />
          <span className="tabular flex items-center gap-1 text-[11px] text-ink-3">
            score {bottleneck.score.toFixed(0)}
            {index === 0 && <Hint text={SCORE_HINT} />}
          </span>
        </span>
        <ChevronDown className={clsx("size-4 shrink-0 text-ink-3 transition", open && "rotate-180")} aria-hidden />
      </button>
      {open && (
        <div className="grid gap-5 bg-surface-2/40 px-5 pb-5 pt-1 sm:pl-14 lg:grid-cols-2">
          <div>
            <h3 className="mb-3 text-[12px] font-medium uppercase tracking-wide text-ink-3">Signals, ranked against all candidates</h3>
            <SignalBars signals={bottleneck.signals} />
          </div>
          <div className="grid content-start gap-3">
            <h3 className="text-[12px] font-medium uppercase tracking-wide text-ink-3">Evidence</h3>
            <ul className="grid gap-1.5 text-[13px] leading-relaxed text-ink-2">
              {bottleneck.evidence.map((line) => (
                <li key={line} className="flex gap-2">
                  <span className="mt-2 size-1 shrink-0 rounded-full bg-ink-3" aria-hidden />
                  {line}
                </li>
              ))}
            </ul>
            <div>
              <ExplainButton analysisId={analysisId} kind="bottleneck" index={index} />
            </div>
          </div>
        </div>
      )}
    </li>
  );
}
