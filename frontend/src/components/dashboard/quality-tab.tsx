import { CheckCircle2 } from "lucide-react";
import { Panel } from "@/components/ui/panel";
import { count, percent } from "@/lib/format";
import type { TabProps } from "./overview-tab";

const STRATEGY = {
  business_id: "Cases are Business IDs (cleaned and filled in from neighbouring steps).",
  work_session: "Cases are work sessions: a person's steps until a break of 30 minutes or more.",
  case_column: "Cases come from the case column of the event log.",
};

export function QualityTab({ analysis }: TabProps) {
  const quality = analysis.quality;
  const kyp = quality.source_format === "kyp_activity_sequence";
  const funnel = [
    { label: "Rows in the file", value: quality.rows_read },
    ...Object.entries(quality.rows_dropped).map(([reason, value]) => ({ label: `Dropped: ${reason}`, value: -value })),
    { label: kyp ? "Process steps rebuilt" : "Events kept", value: quality.steps },
    { label: "Cases", value: quality.cases },
    ...(quality.cases_cut_off ? [{ label: "Cut off by the export window", value: -quality.cases_cut_off }] : []),
  ];

  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <Panel
        title="From file to cases"
        subtitle={kyp ? `KYP.ai Activity Sequence Export · ${quality.rows_per_step.toFixed(1)} interaction rows per step on average` : "Event log"}
      >
        <dl className="divide-y divide-line">
          {funnel.map((row) => (
            <div key={row.label} className="tabular flex justify-between py-2.5 text-[13px]">
              <dt className={row.value < 0 ? "pl-4 text-ink-3" : "text-ink-2"}>{row.label}</dt>
              <dd className={row.value < 0 ? "text-ink-3" : "font-medium text-ink"}>
                {row.value < 0 ? `−${count(-row.value)}` : count(row.value)}
              </dd>
            </div>
          ))}
        </dl>
        <p className="mt-4 text-[13px] leading-relaxed text-ink-2">{STRATEGY[quality.case_strategy]}</p>
        {quality.cases_cut_off > 0 && (
          <p className="mt-2 text-[13px] leading-relaxed text-ink-2">
            Cases near the start or end of the export that do not begin or finish like complete cases were left out of
            variant, map and duration statistics: they were already running, or still open, when the export was taken.
          </p>
        )}
      </Panel>

      {kyp && (
        <Panel title="Business IDs" subtitle="Usually read off the screen by OCR, so incomplete and sometimes wrong.">
          <dl className="tabular grid grid-cols-2 gap-4 text-[13px]">
            <div>
              <dt className="text-ink-3">Steps with a usable ID</dt>
              <dd className="mt-1 text-[22px] font-semibold tracking-tight">{percent(quality.steps_with_business_id)}</dd>
            </div>
            <div>
              <dt className="text-ink-3">Filled in from neighbours</dt>
              <dd className="mt-1 text-[22px] font-semibold tracking-tight">{count(quality.steps_with_imputed_id)}</dd>
            </div>
          </dl>
          {quality.business_ids_rejected.length > 0 && (
            <div className="mt-5">
              <h3 className="text-[12px] text-ink-3">Rejected as noise (do not match the dominant ID format)</h3>
              <ul className="mt-2 flex flex-wrap gap-1.5">
                {quality.business_ids_rejected.map((value) => (
                  <li key={value} className="rounded-md border border-line bg-surface-2 px-2 py-0.5 font-mono text-[11px] text-ink-2 line-through decoration-ink-3">
                    {value}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Panel>
      )}

      <Panel title="What was cleaned" subtitle="Problems in the export, and what the reader did about them.">
        <ul className="grid gap-2.5 text-[13px] leading-relaxed text-ink-2">
          {quality.notes.map((note) => (
            <li key={note} className="flex gap-2">
              <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-good" aria-hidden />
              {note}
            </li>
          ))}
          {Object.entries(quality.rows_dropped).map(([reason, value]) => (
            <li key={reason} className="flex gap-2">
              <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-good" aria-hidden />
              {count(value)} rows dropped ({reason}).
            </li>
          ))}
        </ul>
      </Panel>

      {Object.keys(quality.export_metadata).length > 0 && (
        <Panel title="Export settings" subtitle="Read from the footer the exporter appends to the file.">
          <dl className="divide-y divide-line text-[13px]">
            {Object.entries(quality.export_metadata).map(([key, value]) => (
              <div key={key} className="flex justify-between gap-4 py-2.5">
                <dt className="text-ink-3">{key}</dt>
                <dd className="text-right text-ink">{value}</dd>
              </div>
            ))}
          </dl>
        </Panel>
      )}
    </div>
  );
}
