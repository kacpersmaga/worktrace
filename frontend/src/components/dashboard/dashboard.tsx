"use client";

import clsx from "clsx";
import { Bot, Download, FileCheck2, GitBranch, Gauge, LayoutDashboard, Users, Waypoints } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Brand } from "@/components/brand";
import { api } from "@/lib/api";
import { dateRange } from "@/lib/format";
import type { Analysis } from "@/lib/types";
import { AutomationTab } from "./automation-tab";
import { BottlenecksTab } from "./bottlenecks-tab";
import { MapTab } from "./map-tab";
import { OverviewTab } from "./overview-tab";
import { PeopleTab } from "./people-tab";
import { QualityTab } from "./quality-tab";
import { VariantsTab } from "./variants-tab";

const TABS = [
  { key: "overview", label: "Overview", Icon: LayoutDashboard, Body: OverviewTab },
  { key: "map", label: "Process map", Icon: Waypoints, Body: MapTab },
  { key: "bottlenecks", label: "Bottlenecks", Icon: Gauge, Body: BottlenecksTab },
  { key: "variants", label: "Variants & rework", Icon: GitBranch, Body: VariantsTab },
  { key: "automation", label: "Automation", Icon: Bot, Body: AutomationTab },
  { key: "people", label: "People", Icon: Users, Body: PeopleTab },
  { key: "quality", label: "Data quality", Icon: FileCheck2, Body: QualityTab },
] as const;

export type TabKey = (typeof TABS)[number]["key"];

export function Dashboard({ analysis }: { analysis: Analysis }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const current = TABS.find((tab) => tab.key === params.get("tab")) ?? TABS[0];
  const go = (key: string) => router.replace(`${pathname}?tab=${key}`, { scroll: false });
  const { Body } = current;

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[232px_1fr]">
      <aside className="border-line lg:sticky lg:top-0 lg:h-screen lg:border-r">
        <div className="flex items-center justify-between px-5 py-5 lg:block">
          <Brand />
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-col lg:overflow-visible lg:pb-0" aria-label="Analysis sections">
          {TABS.map(({ key, label, Icon }) => (
            <button
              key={key}
              type="button"
              onClick={() => go(key)}
              aria-current={current.key === key ? "page" : undefined}
              className={clsx(
                "flex shrink-0 items-center gap-2.5 rounded-lg px-3 py-2 text-left text-[13px] transition",
                current.key === key ? "bg-surface font-medium text-ink shadow-[var(--shadow)]" : "text-ink-2 hover:bg-surface/60 hover:text-ink",
              )}
            >
              <Icon className="size-4 opacity-80" aria-hidden />
              {label}
            </button>
          ))}
        </nav>
      </aside>

      <div className="min-w-0">
        <header className="flex flex-wrap items-end justify-between gap-4 px-4 pb-2 pt-6 sm:px-8 lg:pt-8">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 text-[12px] text-ink-3">
              <span>{dateRange(analysis.overview.start, analysis.overview.end)}</span>
              <span aria-hidden>·</span>
              <span>{analysis.overview.users} people</span>
              <span className="rounded-full border border-line bg-surface px-2 py-0.5 font-medium text-ink-2">
                {analysis.synthetic ? "Synthetic data" : "Real data"}
              </span>
            </div>
            <h1 className="mt-1.5 text-[28px] font-semibold tracking-[-0.025em] text-ink">{analysis.name}</h1>
          </div>
          <a
            href={api.bpmnUrl(analysis.id)}
            className="inline-flex items-center gap-2 rounded-lg bg-button px-3.5 py-2 text-[13px] font-medium text-button-ink transition hover:opacity-90"
          >
            <Download className="size-4" aria-hidden />
            Download BPMN
          </a>
        </header>
        <main className="px-4 pb-20 pt-6 sm:px-8">
          <Body analysis={analysis} onNavigate={go} />
        </main>
      </div>
    </div>
  );
}
