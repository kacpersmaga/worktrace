import { Trophy } from "lucide-react";
import { Brand } from "@/components/brand";
import { Start } from "@/components/home/start";

const STEPS = [
  { title: "Rebuild the steps", text: "Interaction rows become process steps; counters are counted once, broken rows and footers are dropped." },
  { title: "Find the cases", text: "Business IDs are cleaned by shape voting and filled in from neighbouring steps, or work is split into sessions." },
  { title: "Mine the process", text: "Heuristics-miner map, variant alignment, rework loops and routines from the real sequence of work." },
  { title: "Rank what to fix", text: "Bottlenecks and automation candidates scored from several signals, each with the evidence behind it." },
];

export default function Home() {
  return (
    <main className="mx-auto max-w-6xl px-4 pb-24 sm:px-8">
      <nav className="flex items-center justify-between py-6">
        <Brand />
        <a
          href="https://github.com/kacpersmaga/worktrace"
          className="text-[13px] text-ink-3 transition-colors hover:text-ink"
        >
          Source on GitHub
        </a>
      </nav>

      <section className="pb-14 pt-12 sm:pt-20">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1 text-[12px] font-medium text-ink-2">
          <Trophy className="size-3.5 text-[var(--series-4)]" aria-hidden />
          Winner of AI Krak Hack 2026, Process-to-Automation Copilot challenge
        </span>
        <h1 className="mt-6 max-w-3xl text-[44px] font-semibold leading-[1.02] tracking-[-0.035em] text-ink sm:text-[64px]">
          See how work really flows.
        </h1>
        <p className="mt-5 max-w-2xl text-[17px] leading-relaxed text-ink-2 sm:text-[19px]">
          Drop in a task-mining export. WorkTrace rebuilds the real process from clicks and keystrokes,
          shows where cases wait, and ranks the steps worth automating first.
        </p>
      </section>

      <Start />

      <section className="mt-20">
        <h2 className="text-[13px] font-medium uppercase tracking-[0.08em] text-ink-3">What happens to your file</h2>
        <ol className="mt-5 grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, index) => (
            <li key={step.title} className="bg-surface p-5">
              <span className="tabular text-[12px] font-medium text-accent">0{index + 1}</span>
              <h3 className="mt-2 text-[15px] font-semibold tracking-tight">{step.title}</h3>
              <p className="mt-1.5 text-[13px] leading-relaxed text-ink-2">{step.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <footer className="mt-20 border-t border-line pt-6 text-[12px] text-ink-3">
        Built by team VibeCoders at AI Krak Hack 2026, then rebuilt from the ground up. Everything runs locally.
      </footer>
    </main>
  );
}
