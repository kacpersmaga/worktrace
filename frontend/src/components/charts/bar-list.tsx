interface BarRow {
  label: string;
  value: number;
  /** Part of the value drawn lighter at the end of the bar (for example idle time). */
  secondary?: number;
  color: string;
  display: string;
  detail?: string;
}

/** Horizontal bars with the label above and the value at the tip; one baseline, rounded data ends. */
export function BarList({ rows }: { rows: BarRow[] }) {
  const max = Math.max(...rows.map((row) => row.value), 1e-9);
  return (
    <ul className="grid gap-3">
      {rows.map((row) => {
        const width = (row.value / max) * 100;
        const secondary = row.secondary ? (row.secondary / row.value) * 100 : 0;
        return (
          <li key={row.label} className="group" title={row.detail ?? `${row.label}: ${row.display}`}>
            <div className="mb-1 flex items-baseline justify-between gap-3 text-[13px]">
              <span className="flex min-w-0 items-center gap-2 text-ink">
                <span className="size-2 shrink-0 rounded-full" style={{ background: row.color }} aria-hidden />
                <span className="truncate">{row.label}</span>
              </span>
              <span className="tabular shrink-0 text-ink-2">{row.display}</span>
            </div>
            <div className="h-2.5 rounded-r bg-transparent">
              <div
                className="flex h-full overflow-hidden rounded-r-[4px] transition-opacity group-hover:opacity-80"
                style={{ width: `${Math.max(width, 0.8)}%` }}
              >
                <div className="h-full" style={{ width: `${100 - secondary}%`, background: row.color }} />
                {secondary > 0 && (
                  <div
                    className="ml-[2px] h-full"
                    style={{ width: `${secondary}%`, background: row.color, opacity: 0.35 }}
                  />
                )}
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
