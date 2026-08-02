"use client";

import { useState } from "react";
import { hours } from "@/lib/format";
import type { HeatCell } from "@/lib/types";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const STEPS = ["--seq-1", "--seq-2", "--seq-3", "--seq-4", "--seq-5", "--seq-6"];

/** Weekday × hour grid on a single-hue ramp; empty cells recede to the surface. */
export function Heatmap({ cells }: { cells: HeatCell[] }) {
  const [hover, setHover] = useState<HeatCell | null>(null);
  const days = [...new Set(cells.map((cell) => cell.weekday))].sort();
  const busyHours = cells.filter((cell) => cell.active_hours > 0).map((cell) => cell.hour);
  const first = Math.min(...busyHours, 8);
  const last = Math.max(...busyHours, 17);
  const hourRange = Array.from({ length: last - first + 1 }, (_, index) => first + index);
  const max = Math.max(...cells.map((cell) => cell.active_hours), 1e-9);
  const lookup = new Map(cells.map((cell) => [`${cell.weekday}-${cell.hour}`, cell]));

  const fill = (value: number) =>
    value <= 0 ? "var(--seq-0)" : `var(${STEPS[Math.min(STEPS.length - 1, Math.floor((value / max) * STEPS.length))]})`;

  return (
    <div>
      <div className="overflow-x-auto">
        <div className="grid min-w-[480px] gap-[3px]" style={{ gridTemplateColumns: `2.5rem repeat(${hourRange.length}, 1fr)` }}>
          <span />
          {hourRange.map((hour) => (
            <span key={hour} className="tabular pb-1 text-center text-[11px] text-ink-3">
              {hour % 2 === 0 ? `${hour}` : ""}
            </span>
          ))}
          {days.map((day) => (
            <div key={day} className="contents">
              <span className="self-center text-[11px] text-ink-3">{DAYS[day]}</span>
              {hourRange.map((hour) => {
                const cell = lookup.get(`${day}-${hour}`) ?? { weekday: day, hour, active_hours: 0 };
                return (
                  <span
                    key={hour}
                    onMouseEnter={() => setHover(cell)}
                    onMouseLeave={() => setHover(null)}
                    className="aspect-square min-h-4 rounded-[3px] outline-offset-1 hover:outline hover:outline-2 hover:outline-[var(--ink)]"
                    style={{ background: fill(cell.active_hours) }}
                    aria-label={`${DAYS[day]} ${hour}:00, ${hours(cell.active_hours)} active`}
                  />
                );
              })}
            </div>
          ))}
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between text-[11px] text-ink-3">
        <span className="tabular min-h-4">
          {hover ? `${DAYS[hover.weekday]} ${hover.hour}:00–${hover.hour + 1}:00 · ${hours(hover.active_hours)} active` : "Hover a cell for details"}
        </span>
        <span className="flex items-center gap-1.5">
          Less
          {STEPS.map((step) => (
            <span key={step} className="size-2.5 rounded-[2px]" style={{ background: `var(${step})` }} />
          ))}
          More
        </span>
      </div>
    </div>
  );
}
