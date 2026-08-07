import { AlertTriangle, ArrowUpRight, Info, Lightbulb } from "lucide-react";
import { BarList } from "@/components/charts/bar-list";
import { Heatmap } from "@/components/charts/heatmap";
import { Panel } from "@/components/ui/panel";
import { Stat } from "@/components/ui/stat";
import { appColors } from "@/lib/colors";
import { count, hours, minutes, percent } from "@/lib/format";
import type { Analysis, Finding } from "@/lib/types";

export interface TabProps {
  analysis: Analysis;
  onNavigate: (tab: string) => void;
}

const TONES: Record<Finding["tone"], { Icon: typeof Info; color: string }> = {
  warning: { Icon: AlertTriangle, color: "var(--serious)" },
  opportunity: { Icon: Lightbulb, color: "var(--accent)" },
  info: { Icon: Info, color: "var(--ink-3)" },
};

export function OverviewTab({ analysis, onNavigate }: TabProps) {
  const { overview, quality } = analysis;
  const color = appColors(analysis.apps);
  const caseWord = quality.case_strategy === "work_session" ? "work session" : "case";

  return (
    <div className="grid gap-6">
      <Panel flush title="What stands out" subtitle="Written from the results below. Open one to see the evidence.">
        <ol className="divide-y divide-line border-t border-line">
          {analysis.findings.map((finding) => {
            const { Icon, color: tone } = TONES[finding.tone];
            return (
              <li key={finding.title}>
                <button
                  type="button"
                  onClick={() => onNavigate(finding.tab)}
                  className="group grid w-full grid-cols-[1.25rem_1fr_auto] items-start gap-3 px-5 py-3.5 text-left transition hover:bg-surface-2 md:grid-cols-[1.25rem_minmax(0,26rem)_1fr_auto]"
                >
                  <Icon className="mt-0.5 size-4" style={{ color: tone }} aria-hidden />
                  <span className="text-[14px] font-semibold leading-snug text-ink">{finding.title}</span>
                  <span className="col-start-2 text-[13px] leading-relaxed text-ink-2 md:col-start-3">{finding.detail}</span>
                  <ArrowUpRight
                    className="col-start-3 row-start-1 size-4 text-ink-3 transition group-hover:translate-x-0.5 group-hover:text-ink md:col-start-4"
                    aria-hidden
                  />
                </button>
              </li>
            );
          })}
        </ol>
      </Panel>

      <section aria-label="Key numbers" className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Stat
          label="Tracked work"
          value={hours(overview.tracked_hours)}
          detail={`${percent(overview.idle_hours / overview.tracked_hours)} of it idle · ${overview.active_days} ${overview.active_days === 1 ? "day" : "days"}`}
          hint="Time inside recorded process steps. Idle is time inside a step with no mouse or keyboard input."
        />
        <Stat
          label={quality.case_strategy === "work_session" ? "Work sessions" : "Cases"}
          value={count(overview.cases)}
          detail={`${count(overview.steps)} steps · ${overview.activities} activities`}
          hint={
            quality.case_strategy === "work_session"
              ? "Too few steps carry a Business ID, so a case is a person's steps until a break of 30 minutes or more."
              : "Cases come from the Business ID, cleaned and filled in from neighbouring steps."
          }
        />
        <Stat
          label={`Typical ${caseWord}`}
          value={minutes(overview.median_case_minutes)}
          detail={`Slowest 10% take over ${minutes(overview.p90_case_minutes)}`}
          hint="Median time from the first to the last step of a case, waiting included."
        />
        <Stat
          label="Copied between apps"
          value={count(overview.cross_app_transfers)}
          detail={`${count(overview.copy_paste_operations)} copy, cut and paste actions`}
          hint="Pastes matched to a copy in a different application by the same person shortly before: data carried by hand."
        />
      </section>

      <div className="grid items-start gap-6 xl:grid-cols-[1fr_1.2fr]">
        <Panel title="Where the time goes" subtitle="Tracked hours per application; the lighter part of each bar is idle time.">
          <BarList
            rows={analysis.apps.map((app) => ({
              label: app.app,
              value: app.active_hours + app.idle_hours,
              secondary: app.idle_hours,
              color: color(app.app),
              display: `${hours(app.active_hours + app.idle_hours)} · ${percent(app.share)}`,
            }))}
          />
        </Panel>
        <Panel title="When work happens" subtitle="Active hours by weekday and hour of the day.">
          <Heatmap cells={analysis.heatmap} />
        </Panel>
      </div>
    </div>
  );
}
