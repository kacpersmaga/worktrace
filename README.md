<p align="center"><img src="docs/readme/hero.jpg" width="100%" alt="WorkTrace. See how work really flows. First place at AI Krak Hack 2026."></p>

<p align="center"><img src="docs/readme/demo.gif" width="100%" alt="Opening the accounts payable demo: overview, process map with the detail sliders, a bottleneck opened to its evidence, automation candidates and the people timeline"></p>

<p align="center"><img src="docs/readme/fixed.jpg" width="100%" alt="The hackathon numbers were wrong. Now they are not."></p>

<p align="center"><img src="docs/readme/map.jpg" width="100%" alt="The process as it runs, not as the wiki says"></p>

<p align="center"><img src="docs/readme/bottlenecks.jpg" width="100%" alt="Bottlenecks ranked by evidence, not a threshold"></p>

<p align="center"><img src="docs/readme/automation.jpg" width="100%" alt="What to automate first, and how"></p>

<p align="center"><img src="docs/readme/people.jpg" width="100%" alt="Fair comparisons between people"></p>

<p align="center"><img src="docs/readme/engineering.jpg" width="100%" alt="Real algorithms, small and readable"></p>

<p align="center"><img src="docs/readme/run.jpg" width="100%" alt="Running on your machine in two commands"></p>

<p align="center">
  <a href="docs/ENGINEERING.md"><b>How it works</b></a>&nbsp;&nbsp;|&nbsp;&nbsp;<a href="#run-it"><b>Run it</b></a>&nbsp;&nbsp;|&nbsp;&nbsp;<a href="docs/challenge-brief.pdf"><b>The challenge</b></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/AI%20Krak%20Hack%202026-1st%20place-eda100" alt="AI Krak Hack 2026, first place">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB" alt="Python 3.12">
  <img src="https://img.shields.io/badge/FastAPI-pandas%20·%20networkx%20·%20scikit--learn-009688" alt="FastAPI, pandas, networkx, scikit-learn">
  <img src="https://img.shields.io/badge/Next.js-16-000000" alt="Next.js 16">
</p>

## About

WorkTrace started as our entry to the **Process-to-Automation Copilot** challenge at **AI Krak Hack 2026** (Kraków, 27–28 March 2026), where team VibeCoders took first place. The brief: take task-mining data from KYP.ai (every click, keystroke and copy-paste of a team at work), reconstruct how the process really runs, find the bottlenecks and say what to automate.

After the event I rebuilt it. The prototype read the export the naive way and its numbers were wrong (see the table above). This version reads the export for what it is, uses real process-mining algorithms instead of hand-tuned `if`s, and every number on screen can show where it came from.

## What it does

- **Reads messy exports.** KYP.ai Activity Sequence Exports (plain or `.gz`, any common encoding) and generic event logs with case, activity and timestamp columns. Footers, broken rows and repeated counters are handled; the Data quality tab says what was fixed.
- **Finds the cases.** Business IDs read by OCR are cleaned by shape voting, and untagged steps are attributed to cases with a Markov model of the process. Without usable IDs, work is split into sessions.
- **Maps the process.** Heuristics Miner dependency graph with Disco-style sliders for activities and paths, waiting times on every hand-over, and a BPMN 2.0 export.
- **Ranks bottlenecks and automation candidates** from several measured signals, each with its percentile and the reasons in plain language. Optional Gemini explanations, grounded in the measured numbers only.
- **Compares people fairly** (speed on the same activities, not raw totals), finds rework loops, routines, copy-paste flows between applications and unusual cases.

<details>
<summary><b>Run it</b></summary>

<br>

Python 3.12+ with [uv](https://docs.astral.sh/uv/), and Node.js 22+.

```bash
cd backend && uv run uvicorn worktrace.api.app:app     # API on :8000
cd frontend && npm install && npm run dev              # dashboard on :3000
```

Open http://localhost:3000 and pick a demo dataset, or upload your own export. Or run both in containers with `docker compose up`.

```bash
cd backend && uv run pytest                             # 28 tests, including ground-truth checks on synthetic data
uv run python -m worktrace.synthetic --days 15          # regenerate the synthetic AP team
GEMINI_API_KEY=... uv run uvicorn worktrace.api.app:app  # turn on Gemini explanations
```

</details>

<details>
<summary><b>The data</b></summary>

<br>

| Dataset | What it is |
| --- | --- |
| `data/demo/kyp_pilot_day.csv.gz` | A real, anonymised KYP.ai Activity Sequence Export from the hackathon: eight people of a software team on 1 March 2026. Screen text, OCR, URLs and window titles are removed. |
| `data/demo/accounts_payable.csv.gz` | Synthetic: three weeks of nine accounts-payable clerks, written by [`synthetic.py`](backend/worktrace/synthetic.py) in the exact export format with its quirks (repeated counters, NOT_FOUND and junk IDs, the footer). Built-in behaviour (approval waits, an 18% missing-PO loop, a slower clerk) is checked by the tests. |

The full hackathon dataset (1.6 GB) belongs to the organisers and is not included.

</details>

<details>
<summary><b>Credits</b></summary>

<br>

The hackathon prototype was built by team VibeCoders: Mateusz Caputa, Marcin Pałys and Kacper Smaga. The analysis engine, the dashboard and this repository are a rebuild by Kacper Smaga.

</details>
