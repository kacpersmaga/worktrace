"use client";

import { useState } from "react";
import { clockTime } from "@/lib/format";
import type { PersonDay, TimelineSegment } from "@/lib/types";

interface TimelineProps {
  days: PersonDay[];
  color: (app: string) => string;
  apps: string[];
}

/** Each person's busiest day as application blocks on a shared clock, so rhythms compare at a glance. */
export function Timeline({ days, color, apps }: TimelineProps) {
  const [hover, setHover] = useState<{ alias: string; segment: TimelineSegment } | null>(null);
  const clock = (iso: string) => {
    const date = new Date(iso);
    return date.getHours() + date.getMinutes() / 60 + date.getSeconds() / 3600;
  };
  const starts = days.flatMap((day) => day.segments.map((segment) => clock(segment.start)));
  const ends = days.flatMap((day) => day.segments.map((segment) => clock(segment.end)));
  const from = Math.floor(Math.min(...starts));
  const to = Math.ceil(Math.max(...ends));
  const span = Math.max(to - from, 1);
  const ticks = Array.from({ length: span + 1 }, (_, index) => from + index).filter((_, index, all) => all.length <= 13 || index % 2 === 0);

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-x-4 gap-y-1.5 text-[12px] text-ink-2">
        {apps.map((app) => (
          <span key={app} className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-[3px]" style={{ background: color(app) }} />
            {app}
          </span>
        ))}
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-[3px] bg-[var(--series-other)]" />
          Other
        </span>
      </div>
      <div className="grid gap-2">
        {days.map((day) => (
          <div key={day.alias} className="grid grid-cols-[5.5rem_1fr] items-center gap-3">
            <div className="text-[12px] leading-tight">
              <div className="font-medium text-ink">{day.alias}</div>
              <div className="text-ink-3">{new Date(day.date).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}</div>
            </div>
            <div className="relative h-7 rounded-md bg-surface-2">
              {day.segments.map((segment) => {
                const left = ((clock(segment.start) - from) / span) * 100;
                const width = Math.max(((clock(segment.end) - clock(segment.start)) / span) * 100, 0.15);
                return (
                  <span
                    key={segment.start}
                    onMouseEnter={() => setHover({ alias: day.alias, segment })}
                    onMouseLeave={() => setHover(null)}
                    className="absolute inset-y-1 rounded-[2px] hover:inset-y-0"
                    style={{
                      left: `${left}%`,
                      width: `${width}%`,
                      background: color(segment.app),
                      opacity: segment.idle ? 0.35 : 1,
                    }}
                  />
                );
              })}
            </div>
          </div>
        ))}
        <div className="grid grid-cols-[5.5rem_1fr] gap-3">
          <span />
          <div className="relative h-4">
            {ticks.map((tick) => (
              <span
                key={tick}
                className="tabular absolute -translate-x-1/2 text-[10px] text-ink-3"
                style={{ left: `${((tick - from) / span) * 100}%` }}
              >
                {String(tick).padStart(2, "0")}:00
              </span>
            ))}
          </div>
        </div>
      </div>
      <p className="mt-3 min-h-5 text-[12px] text-ink-2">
        {hover
          ? `${hover.alias} · ${clockTime(hover.segment.start)}–${clockTime(hover.segment.end)} · ${hover.segment.app}: ${hover.segment.activity}${hover.segment.idle ? " (mostly idle)" : ""}`
          : "Hover a block to see what was being done. Faded blocks are mostly idle."}
      </p>
    </div>
  );
}
