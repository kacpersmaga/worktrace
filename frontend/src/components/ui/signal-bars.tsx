import type { Signal } from "@/lib/types";

/** Each signal behind a score: the measured value and how it ranks against every other candidate. */
export function SignalBars({ signals }: { signals: Signal[] }) {
  return (
    <dl className="grid gap-2.5">
      {signals.map((signal) => (
        <div key={signal.key} className="grid grid-cols-[minmax(0,11rem)_1fr_4.5rem] items-center gap-3 text-[12px]">
          <dt className="truncate text-ink-2">{signal.label}</dt>
          <div
            className="h-1.5 overflow-hidden rounded-full bg-accent-soft"
            role="meter"
            aria-valuenow={Math.round(signal.percentile * 100)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`${signal.label}: higher than ${Math.round(signal.percentile * 100)}% of candidates`}
          >
            <div className="h-full rounded-full bg-accent" style={{ width: `${Math.max(signal.percentile * 100, 3)}%` }} />
          </div>
          <dd className="tabular text-right font-medium text-ink">{signal.display}</dd>
        </div>
      ))}
    </dl>
  );
}
