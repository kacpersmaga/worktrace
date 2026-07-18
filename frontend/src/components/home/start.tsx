"use client";

import { ArrowRight, Database, FlaskConical, Loader2, Upload } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Demo, Job } from "@/lib/types";

export function Start() {
  const router = useRouter();
  const [demos, setDemos] = useState<Demo[]>([]);
  const [recent, setRecent] = useState<Job[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    Promise.all([api.demos(), api.recent()])
      .then(([demoList, jobs]) => {
        setDemos(demoList);
        setRecent(jobs.filter((job) => job.status === "done" && !job.id.startsWith("demo-")).slice(0, 5));
      })
      .catch(() => setOffline(true));
  }, []);

  async function open(action: () => Promise<Job>, key: string) {
    setBusy(key);
    setError(null);
    try {
      const job = await action();
      router.push(`/analysis/${job.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Something went wrong");
      setBusy(null);
    }
  }

  if (offline) {
    return (
      <div className="panel p-6 text-[14px] text-ink-2">
        The analysis service is not running. Start it with <code className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[13px]">uv run uvicorn worktrace.api.app:app</code> in{" "}
        <code className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[13px]">backend/</code>, then reload.
      </div>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1.15fr_1fr]">
      <UploadZone busy={busy === "upload"} onFile={(file) => open(() => api.upload(file), "upload")} />
      <div className="grid gap-4">
        {demos.map((demo) => (
          <button
            key={demo.key}
            type="button"
            onClick={() => open(() => api.openDemo(demo.key), demo.key)}
            disabled={busy !== null}
            className="panel group flex items-start gap-4 p-5 text-left transition hover:border-line-strong disabled:opacity-70"
          >
            <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-lg bg-surface-2 text-ink-2">
              {demo.synthetic ? <FlaskConical className="size-4" aria-hidden /> : <Database className="size-4" aria-hidden />}
            </span>
            <span className="min-w-0 flex-1">
              <span className="flex items-center gap-2 text-[15px] font-semibold tracking-tight">
                {demo.name}
                <span className="rounded-full bg-surface-2 px-2 py-0.5 text-[11px] font-medium text-ink-3">
                  {demo.synthetic ? "Synthetic" : "Real data"}
                </span>
              </span>
              <span className="mt-1 block text-[13px] leading-relaxed text-ink-2">{demo.description}</span>
            </span>
            {busy === demo.key ? (
              <Loader2 className="mt-1 size-4 animate-spin text-ink-3" aria-hidden />
            ) : (
              <ArrowRight className="mt-1 size-4 text-ink-3 transition group-hover:translate-x-0.5 group-hover:text-ink" aria-hidden />
            )}
          </button>
        ))}
        {recent.length > 0 && (
          <div className="panel p-5">
            <h2 className="text-[13px] font-medium text-ink-3">Your recent analyses</h2>
            <ul className="mt-2 divide-y divide-line">
              {recent.map((job) => (
                <li key={job.id}>
                  <Link href={`/analysis/${job.id}`} className="flex items-center justify-between py-2 text-[14px] hover:text-accent">
                    {job.name}
                    <span className="text-[12px] text-ink-3">{new Date(job.created).toLocaleString("en-GB")}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      {error && <p className="text-[13px] text-critical lg:col-span-2">{error}</p>}
    </div>
  );
}

function UploadZone({ busy, onFile }: { busy: boolean; onFile: (file: File) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        const file = event.dataTransfer.files[0];
        if (file) onFile(file);
      }}
      className={`flex min-h-72 flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition ${
        dragging ? "border-accent bg-accent-soft" : "border-line-strong bg-surface"
      }`}
    >
      <span className="grid size-12 place-items-center rounded-xl bg-ink text-surface">
        {busy ? <Loader2 className="size-5 animate-spin" aria-hidden /> : <Upload className="size-5" aria-hidden />}
      </span>
      <h2 className="mt-5 text-[18px] font-semibold tracking-tight">Analyse your own export</h2>
      <p className="mt-2 max-w-sm text-[13px] leading-relaxed text-ink-2">
        A KYP.ai Activity Sequence Export, or any event log with case, activity and timestamp columns. CSV or .csv.gz, up to 400 MB.
      </p>
      <button
        type="button"
        onClick={() => input.current?.click()}
        disabled={busy}
        className="mt-6 rounded-lg bg-button px-4 py-2 text-[13px] font-medium text-button-ink transition hover:opacity-90 disabled:opacity-60"
      >
        {busy ? "Uploading…" : "Choose a file"}
      </button>
      <input
        ref={input}
        type="file"
        accept=".csv,.gz"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFile(file);
        }}
      />
    </div>
  );
}
