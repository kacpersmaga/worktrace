import { ArrowRight, Clock, MousePointerClick, Search, Wrench } from "lucide-react";
import type { Cause, Diagnosis, Share } from "@/lib/types";

// What the time inside a step was spent on. "No input" is grey on purpose: nothing was happening.
const TIME_COLORS: Record<string, string> = {
  Typing: "var(--series-1)",
  "Clicking and scrolling": "var(--series-3)",
  "Copying and pasting": "var(--series-2)",
  "Looking at the screen": "var(--series-4)",
  "No input (away or waiting)": "var(--line-strong)",
};

function TimeSplit({ split }: { split: Share[] }) {
  const shown = split.filter((part) => part.share > 0);
  return (
    <div>
      <h4 className="text-[12px] font-medium text-ink-3">Where the time in one run goes</h4>
      <div className="mt-2 flex h-3 gap-[2px] overflow-hidden rounded-[4px]" role="img" aria-label={shown.map((part) => `${part.label} ${Math.round(part.share * 100)}%`).join(", ")}>
        {shown.map((part) => (
          <span key={part.label} title={`${part.label}: ${Math.round(part.share * 100)}%, ${part.detail}`} style={{ width: `${part.share * 100}%`, background: TIME_COLORS[part.label] }} />
        ))}
      </div>
      <ul className="mt-2.5 grid gap-x-5 gap-y-1 text-[12px] sm:grid-cols-2 xl:grid-cols-3">
        {split.map((part) => (
          <li key={part.label} className="flex items-center gap-2 text-ink-2">
            <span className="size-2.5 shrink-0 rounded-[3px]" style={{ background: TIME_COLORS[part.label] }} />
            <span className="truncate">{part.label}</span>
            <span className="tabular ml-auto shrink-0 font-medium text-ink">{Math.round(part.share * 100)}%</span>
            <span className="tabular w-16 shrink-0 text-right text-ink-3">{part.detail.replace(" per run", "")}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Fact({ label, items, format }: { label: string; items: Share[]; format: (item: Share) => string }) {
  if (items.length === 0) return null;
  return (
    <div className="min-w-0">
      <dt className="text-[12px] font-medium text-ink-3">{label}</dt>
      <dd className="mt-1 grid gap-0.5 text-[13px] text-ink">
        {items.slice(0, 2).map((item) => (
          <span key={item.label} className="truncate" title={item.label}>
            {format(item)}
          </span>
        ))}
      </dd>
    </div>
  );
}

const percentOf = (item: Share) => `${item.label} · ${Math.round(item.share * 100)}%`;
const meaningful = (item: Share) => item.share >= 0.1;
const perRun = (item: Share) => `${item.label} (${item.detail}) · ${item.share.toFixed(1)} per run`;

function CauseCard({ cause, rank }: { cause: Cause; rank: number }) {
  return (
    <li className="rounded-xl border border-line bg-surface p-4">
      <div className="flex items-start justify-between gap-4">
        <h4 className="text-[14px] font-semibold leading-snug text-ink">
          <span className="tabular mr-2 text-ink-3">{rank}.</span>
          {cause.title}
        </h4>
        <span className="tabular shrink-0 rounded-full bg-surface-2 px-2 py-0.5 text-[11px] font-medium text-ink-2">{cause.impact}</span>
      </div>
      <p className="mt-2 flex gap-2 text-[13px] leading-relaxed text-ink-2">
        <Search className="mt-0.5 size-3.5 shrink-0 text-ink-3" aria-hidden />
        {cause.evidence}
      </p>
      <p className="mt-2 flex gap-2 rounded-lg bg-accent-soft px-3 py-2 text-[13px] leading-relaxed text-ink">
        <Wrench className="mt-0.5 size-3.5 shrink-0 text-accent-ink" aria-hidden />
        <span>
          <span className="font-semibold text-accent-ink">What to do: </span>
          {cause.action}
        </span>
      </p>
      {cause.examples.length > 0 && (
        <div className="mt-2.5 text-[12px] text-ink-3">
          <span className="font-medium text-ink-2">Look at: </span>
          {cause.examples.join(" · ")}
        </div>
      )}
    </li>
  );
}

export function DiagnosisView({ diagnosis }: { diagnosis: Diagnosis }) {
  const hasFacts = diagnosis.screens.length + diagnosis.before.length > 0;
  return (
    <div className="grid gap-5">
      <p className="flex gap-2 text-[14px] leading-relaxed text-ink">
        <Clock className="mt-1 size-4 shrink-0 text-ink-3" aria-hidden />
        {diagnosis.summary}
      </p>

      {diagnosis.time_split.length > 0 && <TimeSplit split={diagnosis.time_split} />}

      {hasFacts && (
        <dl className="grid gap-4 border-y border-line py-4 sm:grid-cols-2 xl:grid-cols-4">
          <Fact label="On screen" items={diagnosis.screens} format={percentOf} />
          <Fact label="Comes after" items={diagnosis.before.filter((item) => item.share >= 0.02)} format={percentOf} />
          <Fact label="Data pasted in from" items={diagnosis.data_in.filter(meaningful)} format={perRun} />
          <Fact label="Data copied out to" items={diagnosis.data_out.filter(meaningful)} format={perRun} />
        </dl>
      )}

      {diagnosis.causes.length > 0 ? (
        <div>
          <h4 className="mb-2.5 flex items-center gap-1.5 text-[12px] font-medium text-ink-3">
            <MousePointerClick className="size-3.5" aria-hidden />
            Why it takes time, and what to do, biggest first
          </h4>
          <ol className="grid gap-2.5">
            {diagnosis.causes.map((cause, index) => (
              <CauseCard key={cause.kind + cause.title} cause={cause} rank={index + 1} />
            ))}
          </ol>
        </div>
      ) : (
        <p className="text-[13px] text-ink-3">No single cause stands out: the time is spread evenly over normal work in this step.</p>
      )}
    </div>
  );
}

export function Blueprint({ steps }: { steps: string[] }) {
  return (
    <div>
      <h4 className="mb-2.5 text-[12px] font-medium text-ink-3">What the automation would do</h4>
      <ol className="grid gap-1.5">
        {steps.map((step, index) => (
          <li key={step} className="flex gap-2.5 text-[13px] leading-relaxed text-ink-2">
            <span className="tabular grid size-5 shrink-0 place-items-center rounded-full bg-surface-2 text-[11px] font-medium text-ink">{index + 1}</span>
            {step}
          </li>
        ))}
      </ol>
    </div>
  );
}

export function TopCause({ diagnosis }: { diagnosis: Diagnosis | null }) {
  const cause = diagnosis?.causes[0];
  if (!cause) return null;
  return (
    <span className="flex items-center gap-1 text-ink-2">
      <ArrowRight className="size-3" aria-hidden />
      {cause.title}
    </span>
  );
}
