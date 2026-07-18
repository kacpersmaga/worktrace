import { Hint } from "./hint";

interface StatProps {
  label: string;
  value: string;
  detail?: string;
  hint?: string;
}

export function Stat({ label, value, detail, hint }: StatProps) {
  return (
    <div className="panel px-5 py-4">
      <div className="flex items-center gap-1.5 text-[13px] text-ink-3">
        {label}
        {hint && <Hint text={hint} />}
      </div>
      <div className="mt-2 text-[28px] font-semibold leading-none tracking-tight text-ink">{value}</div>
      {detail && <div className="mt-2 text-[12px] text-ink-3">{detail}</div>}
    </div>
  );
}
