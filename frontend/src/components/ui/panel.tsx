import clsx from "clsx";

interface PanelProps {
  title?: string;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
  flush?: boolean;
  children: React.ReactNode;
}

export function Panel({ title, subtitle, action, className, flush, children }: PanelProps) {
  return (
    <section className={clsx("panel", className)}>
      {title && (
        <header className="flex items-start justify-between gap-4 px-5 pt-5">
          <div className="min-w-0">
            <h2 className="text-[15px] font-semibold tracking-tight text-ink">{title}</h2>
            {subtitle && <p className="mt-1 text-[13px] leading-relaxed text-ink-3">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className={clsx(!flush && "p-5", flush && title && "pt-4")}>{children}</div>
    </section>
  );
}
