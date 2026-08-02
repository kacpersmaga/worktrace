"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { use, useEffect, useState } from "react";
import { Dashboard } from "@/components/dashboard/dashboard";
import { Brand } from "@/components/brand";
import { api } from "@/lib/api";
import type { Analysis } from "@/lib/types";

const POLL_MS = 700;

export default function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        // Demo links are shareable: if the service has not computed this demo yet, start it.
        const job = await api.status(id).catch((reason) => {
          if (id.startsWith("demo-")) return api.openDemo(id.slice("demo-".length));
          throw reason;
        });
        if (cancelled) return;
        if (job.status === "running") {
          setTimeout(poll, POLL_MS);
        } else if (job.status === "failed") {
          setError(job.error ?? "The analysis failed.");
        } else {
          setAnalysis(await api.analysis(id));
        }
      } catch (reason) {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "Could not load the analysis.");
      }
    }
    poll();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (analysis) return <Dashboard analysis={analysis} />;

  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col px-6 py-8">
      <Brand />
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        {error ? (
          <>
            <h1 className="text-[20px] font-semibold tracking-tight">This file could not be analysed</h1>
            <p className="mt-2 text-[14px] leading-relaxed text-ink-2">{error}</p>
            <Link href="/" className="mt-6 rounded-lg bg-button px-4 py-2 text-[13px] font-medium text-button-ink">
              Try another file
            </Link>
          </>
        ) : (
          <>
            <Loader2 className="size-6 animate-spin text-accent" aria-hidden />
            <h1 className="mt-4 text-[18px] font-semibold tracking-tight">Reading the export</h1>
            <p className="mt-2 max-w-sm text-[13px] leading-relaxed text-ink-3">
              Rebuilding steps, finding cases and mining the process. Large exports take a minute.
            </p>
          </>
        )}
      </div>
    </main>
  );
}
