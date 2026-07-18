import { ArrowRight, CornerDownRight, Minus, Plus, Repeat2, Shuffle } from "lucide-react";
import { Panel } from "@/components/ui/panel";
import { Stat } from "@/components/ui/stat";
import { count, hours, minutes, percent } from "@/lib/format";
import type { Deviation } from "@/lib/types";
import type { TabProps } from "./overview-tab";

const DEVIATION: Record<Deviation["kind"], { label: string; Icon: typeof Plus }> = {
  skipped: { label: "Skipped", Icon: Minus },
  inserted: { label: "Extra step", Icon: Plus },
  replaced: { label: "Done instead", Icon: Shuffle },
};

function Path({ steps, max = 12 }: { steps: string[]; max?: number }) {
  const shown = steps.slice(0, max);
  return (
    <ol className="flex flex-wrap items-center gap-1">
      {shown.map((step, index) => (
        <li key={`${step}-${index}`} className="flex items-center gap-1">
          {index > 0 && <ArrowRight className="size-3 text-ink-3" aria-hidden />}
          <span className="rounded-md border border-line bg-surface px-2 py-0.5 text-[12px] text-ink">{step}</span>
        </li>
      ))}
      {steps.length > max && <li className="text-[12px] text-ink-3">+{steps.length - max} more</li>}
    </ol>
  );
}

export function VariantsTab({ analysis }: TabProps) {
  const { variants, rework, routines, quality } = analysis;
  const sessions = quality.case_strategy === "work_session";
  const total = analysis.overview.cases;

  return (
    <div className="grid gap-6">
      {sessions && (
        <p className="panel px-5 py-4 text-[13px] leading-relaxed text-ink-2">
          Cases here are work sessions, so nearly every session is its own variant. Routines and loops below are the useful
          view for this kind of data: they find the same short sequence wherever it happens.
        </p>
      )}
      <section className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Stat label="Variants" value={count(variants.total_variants)} detail={`across ${count(total)} cases`} hint="Distinct orders of activities, after merging back-to-back repeats." />
        <Stat label="Follow the main path" value={percent(variants.main_path_share)} detail="of cases, exactly" />
        <Stat label="Top 5 variants cover" value={percent(variants.top5_coverage)} detail="of cases" />
        <Stat
          label="Rework loops"
          value={count(rework.reduce((sum, loop) => sum + loop.occurrences, 0))}
          detail={`${hours(rework.reduce((sum, loop) => sum + loop.hours, 0))} spent going back`}
          hint="Coming back to an activity already done in the same case, with up to three steps in between."
        />
      </section>

      <Panel title="Main path" subtitle="The most common order of steps, used as the reference for every deviation below.">
        <Path steps={variants.main_path} max={20} />
      </Panel>

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel
          title="How cases deviate"
          subtitle="Every variant is aligned with the main path; these are the differences that come up most."
        >
          <ul className="grid gap-2.5">
            {variants.deviations.map((deviation) => {
              const { label, Icon } = DEVIATION[deviation.kind];
              return (
                <li key={`${deviation.kind}-${deviation.activity}`} className="grid grid-cols-[1fr_6rem_3rem] items-center gap-3 text-[13px]">
                  <span className="flex min-w-0 items-center gap-2">
                    <span className="grid size-5 shrink-0 place-items-center rounded bg-surface-2 text-ink-2">
                      <Icon className="size-3" aria-hidden />
                    </span>
                    <span className="truncate text-ink">
                      <span className="text-ink-3">{label}:</span> {deviation.activity}
                    </span>
                  </span>
                  <span className="h-1.5 rounded-full bg-accent-soft">
                    <span className="block h-full rounded-full bg-accent" style={{ width: `${deviation.share * 100}%` }} />
                  </span>
                  <span className="tabular text-right text-ink-2">{percent(deviation.share)}</span>
                </li>
              );
            })}
          </ul>
        </Panel>

        <Panel title="Rework loops" subtitle="Ranked by the time spent going round them.">
          <ul className="grid gap-4">
            {rework.slice(0, 6).map((loop) => (
              <li key={loop.pattern.join(">")}>
                <div className="mb-1.5 flex items-center justify-between gap-3 text-[12px] text-ink-3">
                  <span className="flex items-center gap-1.5">
                    <Repeat2 className="size-3.5" aria-hidden />
                    {count(loop.occurrences)}× in {percent(loop.share_of_cases, 1)} of cases
                  </span>
                  <span className="tabular">{hours(loop.hours)}</span>
                </div>
                <Path steps={loop.pattern} />
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <Panel title="Top variants" subtitle="Each with its share of cases and how far it is from the main path (0 = identical).">
        <ol className="divide-y divide-line">
          {variants.variants.slice(0, 10).map((variant) => (
            <li key={variant.id} className="grid gap-2 py-3 lg:grid-cols-[1fr_15rem] lg:items-center">
              <Path steps={variant.steps} />
              <div className="tabular grid grid-cols-3 gap-2 text-[12px] text-ink-3 lg:text-right">
                <span>
                  <span className="font-medium text-ink">{percent(variant.share, 1)}</span> cases
                </span>
                <span>{minutes(variant.median_minutes)}</span>
                <span>Δ {variant.distance_from_main.toFixed(2)}</span>
              </div>
            </li>
          ))}
        </ol>
      </Panel>

      <Panel title="Routines" subtitle="Short sequences repeated across many cases: candidates for one automation instead of several.">
        <ul className="grid gap-4">
          {routines.map((routine) => (
            <li key={routine.steps.join(">")} className="grid gap-2 lg:grid-cols-[1fr_15rem] lg:items-center">
              <Path steps={routine.steps} />
              <span className="tabular flex items-center gap-1.5 text-[12px] text-ink-3 lg:justify-end">
                <CornerDownRight className="size-3.5" aria-hidden />
                {count(routine.cases)} cases · {hours(routine.hours)}
              </span>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
