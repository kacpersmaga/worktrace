"use client";

import clsx from "clsx";
import { ArrowRight, ChevronDown } from "lucide-react";
import { useState } from "react";
import { ExplainButton } from "@/components/ui/explain-button";
import { Blueprint, DiagnosisView } from "./diagnosis-view";
import { Panel } from "@/components/ui/panel";
import { SignalBars } from "@/components/ui/signal-bars";
import { Stat } from "@/components/ui/stat";
import { appColors } from "@/lib/colors";
import { count, hours, percent } from "@/lib/format";
import type { TabProps } from "./overview-tab";

export function AutomationTab({ analysis }: TabProps) {
  const [open, setOpen] = useState(0);
  const color = appColors(analysis.apps);
  const candidates = analysis.automation;
  const topSaving = candidates.slice(0, 3).reduce((sum, candidate) => sum + candidate.saving_hours_per_week, 0);
  const trackedPerWeek = analysis.overview.tracked_hours / Math.max(analysis.overview.active_days / 5, 0.2);
  const maxSaving = Math.max(...candidates.map((candidate) => candidate.hours_per_week), 1e-9);
  const singleDay = analysis.overview.active_days < 5;

  return (
    <div className="grid gap-6">
      <section className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Stat label="Top 3 candidates save" value={`${hours(topSaving)}/wk`} detail={`≈ ${(topSaving / 40).toFixed(1)} full-time people`} hint="Hours per week the approach can realistically remove, using conservative automation rates per approach." />
        <Stat
          label="Share of tracked work"
          value={percent(topSaving / trackedPerWeek)}
          detail={`of ${hours(trackedPerWeek)} a week`}
          hint="The top three savings as a share of all tracked work per week."
        />
        <Stat label="Values copied by hand" value={count(analysis.overview.cross_app_transfers)} detail={`${analysis.clipboard.length} distinct routes`} />
        <Stat label="App switches" value={`${analysis.switching.switches_per_hour.toFixed(0)}/h`} detail={`${percent(analysis.switching.ping_pong_share)} quick back-and-forth`} hint="Consecutive steps in different applications within a session. A ping-pong is A → B → A within two minutes." />
      </section>
      {singleDay && (
        <p className="text-[12px] text-ink-3">This export covers {analysis.overview.active_days} day; weekly figures are extrapolated from it.</p>
      )}

      <Panel flush title="What to automate first" subtitle="Ranked on time at stake, volume, manual input, copy-paste and how predictable the next step is.">
        <ol className="divide-y divide-line border-t border-line">
          {candidates.map((candidate, index) => (
            <li key={candidate.activity}>
              <button
                type="button"
                onClick={() => setOpen(open === index ? -1 : index)}
                aria-expanded={open === index}
                className="grid w-full grid-cols-[1.25rem_1fr_auto] items-center gap-4 px-5 py-4 text-left hover:bg-surface-2/60 md:grid-cols-[1.25rem_1fr_14rem_auto]"
              >
                <span className="tabular text-[12px] text-ink-3">{index + 1}</span>
                <span className="min-w-0">
                  <span className="block truncate text-[14px] font-semibold tracking-tight text-ink">{candidate.activity}</span>
                  <span className="mt-1 flex flex-wrap items-center gap-2 text-[12px] text-ink-3">
                    <span className="flex items-center gap-1.5">
                      <span className="size-2 rounded-full" style={{ background: color(candidate.app) }} />
                      {candidate.app}
                    </span>
                    <span className="rounded-full bg-accent-soft px-2 py-0.5 font-medium text-accent-ink">{candidate.approach}</span>
                  </span>
                </span>
                <span className="hidden md:block">
                  <span className="flex h-2 overflow-hidden rounded-r-[4px]" style={{ width: `${(candidate.hours_per_week / maxSaving) * 100}%` }}>
                    <span className="h-full bg-accent" style={{ width: `${candidate.automation_rate * 100}%` }} />
                    <span className="ml-[2px] h-full flex-1 bg-accent opacity-25" />
                  </span>
                  <span className="tabular mt-1.5 block text-[11px] text-ink-3">
                    saves <span className="font-medium text-ink">{hours(candidate.saving_hours_per_week)}</span> of {hours(candidate.hours_per_week)} a week
                  </span>
                </span>
                <span className="flex items-center gap-3">
                  <span className="tabular text-[12px] text-ink-3">{candidate.score.toFixed(0)}</span>
                  <ChevronDown className={clsx("size-4 text-ink-3 transition", open === index && "rotate-180")} aria-hidden />
                </span>
              </button>
              {open === index && (
                <div className="grid gap-5 bg-surface-2/40 px-5 pb-6 pt-2 sm:pl-14">
                  <div className="grid gap-5 rounded-xl border border-line bg-surface p-4 lg:grid-cols-2">
                    <Blueprint steps={candidate.blueprint} />
                    <ul className="grid content-start gap-1.5 text-[13px] leading-relaxed text-ink-2">
                      {candidate.rationale.map((line) => (
                        <li key={line} className="flex gap-2">
                          <span className="mt-2 size-1 shrink-0 rounded-full bg-ink-3" aria-hidden />
                          {line}
                        </li>
                      ))}
                    </ul>
                  </div>
                  {candidate.diagnosis && <DiagnosisView diagnosis={candidate.diagnosis} />}
                  <details className="rounded-xl border border-line bg-surface px-4 py-3">
                    <summary className="cursor-pointer text-[12px] font-medium text-ink-2">How the score of {candidate.score.toFixed(0)} was reached</summary>
                    <div className="mt-4">
                      <SignalBars signals={candidate.signals} />
                    </div>
                  </details>
                  <div>
                    <ExplainButton analysisId={analysis.id} kind="automation" index={index} />
                  </div>
                </div>
              )}
            </li>
          ))}
        </ol>
      </Panel>

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel title="Data carried between applications" subtitle="Each paste matched to the copy it came from. These are integration gaps.">
          <ul className="grid gap-3">
            {analysis.clipboard.slice(0, 8).map((flow) => (
              <li key={`${flow.source_step}>${flow.target_step}`} className="grid grid-cols-[1fr_auto] items-center gap-3 text-[13px]">
                <span className="min-w-0">
                  <span className="flex flex-wrap items-center gap-1.5 font-medium text-ink">
                    <span className="size-2 rounded-full" style={{ background: color(flow.source_app) }} />
                    {flow.source_app}
                    <ArrowRight className="size-3.5 text-ink-3" aria-hidden />
                    <span className="size-2 rounded-full" style={{ background: color(flow.target_app) }} />
                    {flow.target_app}
                  </span>
                  <span className="block truncate text-[12px] text-ink-3">
                    {flow.source_step} → {flow.target_step}
                  </span>
                </span>
                <span className="tabular text-right text-ink-2">
                  {count(flow.transfers)}
                  <span className="block text-[11px] text-ink-3">{flow.users} people</span>
                </span>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel title="Most frequent app switches" subtitle="Ping-pongs are A → B → A within two minutes: looking something up to type it elsewhere.">
          <ul className="grid gap-2.5">
            {analysis.switching.pairs.slice(0, 8).map((pair) => (
              <li key={`${pair.from_app}>${pair.to_app}`} className="grid grid-cols-[1fr_auto] gap-3 text-[13px]">
                <span className="flex items-center gap-1.5 text-ink">
                  {pair.from_app}
                  <ArrowRight className="size-3.5 text-ink-3" aria-hidden />
                  {pair.to_app}
                </span>
                <span className="tabular text-ink-2">
                  {count(pair.switches)} <span className="text-[11px] text-ink-3">({percent(pair.ping_pongs / pair.switches)} ping-pong)</span>
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}
