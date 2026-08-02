import { Timeline } from "@/components/charts/timeline";
import { Hint } from "@/components/ui/hint";
import { Panel } from "@/components/ui/panel";
import { appColors } from "@/lib/colors";
import { count, hours, minutes, percent } from "@/lib/format";
import type { TabProps } from "./overview-tab";

const SPEED_HINT =
  "For every activity a person does at least 3 times, the team median duration is divided by theirs; the ratios are averaged (geometric mean, weighted by volume). 1.25 means 25% faster than the team on the same work.";

/** Diverging bar around 1.0: faster to the right in blue, slower to the left in red, grey at par. */
function SpeedBar({ value }: { value: number }) {
  const offset = Math.max(-1, Math.min(1, Math.log2(value))) * 50;
  const faster = offset >= 0;
  return (
    <div className="relative h-2 w-28 rounded-full bg-[var(--neutral-mid)]" aria-hidden>
      <span className="absolute inset-y-[-3px] left-1/2 w-px bg-line-strong" />
      <span
        className="absolute inset-y-0 rounded-full"
        style={{
          left: faster ? "50%" : `${50 + offset}%`,
          width: `${Math.abs(offset)}%`,
          background: faster ? "var(--series-1)" : "var(--critical)",
        }}
      />
    </div>
  );
}

export function PeopleTab({ analysis }: TabProps) {
  const color = appColors(analysis.apps);
  const caseWord = analysis.quality.case_strategy === "work_session" ? "Sessions" : "Cases";

  return (
    <div className="grid gap-6">
      <Panel
        flush
        title="How each person works"
        subtitle="User names in task-mining exports are anonymised; people are numbered by tracked time."
      >
        <div className="overflow-x-auto border-t border-line">
          <table className="w-full min-w-[820px] text-[13px]">
            <thead>
              <tr className="text-left text-[12px] text-ink-3">
                <th className="px-5 py-3 font-medium">Person</th>
                <th className="px-3 py-3 text-right font-medium">Active</th>
                <th className="px-3 py-3 text-right font-medium">{caseWord}</th>
                <th className="px-3 py-3 text-right font-medium">Typical case</th>
                <th className="px-3 py-3 font-medium">
                  <span className="inline-flex items-center gap-1.5">
                    Speed vs team <Hint text={SPEED_HINT} />
                  </span>
                </th>
                <th className="px-3 py-3 text-right font-medium">Switches / h</th>
                <th className="px-3 py-3 text-right font-medium">Clipboard / h</th>
                <th className="px-3 py-3 text-right font-medium">Idle</th>
                <th className="px-5 py-3 font-medium">Main apps</th>
              </tr>
            </thead>
            <tbody className="tabular divide-y divide-line">
              {analysis.people.map((person) => (
                <tr key={person.user} className="hover:bg-surface-2/60">
                  <td className="px-5 py-3 font-medium text-ink" title={person.user}>
                    {person.alias}
                  </td>
                  <td className="px-3 py-3 text-right">{hours(person.active_hours)}</td>
                  <td className="px-3 py-3 text-right">{count(person.cases)}</td>
                  <td className="px-3 py-3 text-right">{minutes(person.median_case_minutes)}</td>
                  <td className="px-3 py-3">
                    {person.speed_index === null ? (
                      <span className="text-[12px] text-ink-3">Too little shared work</span>
                    ) : (
                      <span className="flex items-center gap-3">
                        <SpeedBar value={person.speed_index} />
                        <span className="w-10 text-ink">{person.speed_index.toFixed(2)}</span>
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-3 text-right">{person.switches_per_hour.toFixed(0)}</td>
                  <td className="px-3 py-3 text-right">{person.clipboard_per_hour.toFixed(0)}</td>
                  <td className="px-3 py-3 text-right">{percent(person.idle_share)}</td>
                  <td className="px-5 py-3">
                    <span className="flex flex-wrap gap-x-3 gap-y-1 text-[12px] text-ink-2">
                      {person.top_apps.map((app) => (
                        <span key={app} className="flex items-center gap-1.5">
                          <span className="size-2 rounded-full" style={{ background: color(app) }} />
                          {app}
                        </span>
                      ))}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="A day in each person's work" subtitle="Each person's busiest day, as consecutive blocks of time per application.">
        <Timeline days={analysis.timelines} color={color} apps={analysis.apps.slice(0, 7).map((app) => app.app)} />
      </Panel>
    </div>
  );
}
