import { Info } from "lucide-react";

/** A small (i) that explains a metric on hover or keyboard focus. */
export function Hint({ text }: { text: string }) {
  return (
    <span className="group relative inline-flex" tabIndex={0} aria-label={text}>
      <Info className="size-3.5 text-ink-3 transition-colors group-hover:text-ink-2" aria-hidden />
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-30 mb-2 w-64 -translate-x-1/2 rounded-lg bg-ink px-3 py-2 text-[12px] font-normal leading-relaxed text-surface opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus:opacity-100"
      >
        {text}
      </span>
    </span>
  );
}
