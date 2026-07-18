"use client";

import { Loader2, Sparkles } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Explanation } from "@/lib/types";

interface ExplainButtonProps {
  analysisId: string;
  kind: "bottleneck" | "automation" | "finding" | "anomaly";
  index: number;
}

export function ExplainButton({ analysisId, kind, index }: ExplainButtonProps) {
  const [state, setState] = useState<"idle" | "loading" | "error">("idle");
  const [explanation, setExplanation] = useState<Explanation | null>(null);

  async function load() {
    setState("loading");
    try {
      setExplanation(await api.explain(analysisId, kind, index));
      setState("idle");
    } catch {
      setState("error");
    }
  }

  if (explanation) {
    return (
      <div className="rounded-xl border border-line bg-surface-2 p-4">
        <div className="mb-2 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-ink-3">
          <Sparkles className="size-3.5 text-accent" aria-hidden />
          {explanation.source === "gemini" ? "Explained by Gemini from these numbers" : "Explained from the measured evidence"}
        </div>
        <div className="space-y-2 text-[13px] leading-relaxed text-ink-2">
          {explanation.text.split(/\n{2,}/).map((paragraph) => (
            <p key={paragraph.slice(0, 24)}>{paragraph}</p>
          ))}
        </div>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={load}
      disabled={state === "loading"}
      className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface px-3 py-1.5 text-[12px] font-medium text-ink-2 transition hover:border-line-strong hover:text-ink disabled:opacity-60"
    >
      {state === "loading" ? <Loader2 className="size-3.5 animate-spin" aria-hidden /> : <Sparkles className="size-3.5 text-accent" aria-hidden />}
      {state === "error" ? "Could not explain, try again" : "Explain this"}
    </button>
  );
}
