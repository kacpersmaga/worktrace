import { AlertOctagon, AlertTriangle, CircleDot, Minus } from "lucide-react";
import type { Severity } from "@/lib/types";

const STYLES: Record<Severity, { label: string; color: string; Icon: typeof AlertOctagon }> = {
  critical: { label: "Critical", color: "var(--critical)", Icon: AlertOctagon },
  high: { label: "High", color: "var(--serious)", Icon: AlertTriangle },
  medium: { label: "Medium", color: "var(--warning)", Icon: CircleDot },
  low: { label: "Low", color: "var(--ink-3)", Icon: Minus },
};

/** Severity is never colour alone: an icon and a word carry it too. */
export function SeverityBadge({ severity }: { severity: Severity }) {
  const { label, color, Icon } = STYLES[severity];
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-line bg-surface-2 px-2 py-0.5 text-[11px] font-medium text-ink-2">
      <Icon className="size-3" style={{ color }} aria-hidden strokeWidth={2.5} />
      {label}
    </span>
  );
}
