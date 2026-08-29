# How WorkTrace works

The engine is a Python package (`backend/worktrace`) with one job per module. Every function takes a pandas frame
of steps and returns Pydantic models that the dashboard renders as they are.

```
ingest/      CSV -> clean step log with cases          mining/      step log -> results
  reader       encodings, gzip, chunks, footer           transitions   directly-follows relation, Heuristics Miner dependency
  kyp          interaction rows -> process steps         process_map   map + simplification behind the sliders
  generic      any case/activity/timestamp log           variants      variants and deviations by sequence alignment
  business_ids ID shape voting, Markov case attribution  window        cases cut off by the export window
  sessions     work sessions when IDs are missing        bottlenecks   multi-signal scoring of steps and hand-overs
                                                         rework        loops back to an earlier step
analysis.py  runs everything, builds the result          routines      closed frequent sequences
findings.py  the headline sentences                      clipboard     copy -> paste matching across applications
explain.py   Gemini or evidence-based explanations       switching     application switches and ping-pongs
api/         FastAPI, background jobs, result cache      automation    candidate scoring and approach
synthetic.py the synthetic AP team                       people        speed index, timelines
                                                         anomalies     Isolation Forest + robust z-scores
                                                         bpmn          BPMN 2.0 export
```

## 1. Reading the export

A KYP.ai Activity Sequence Export has one row per interaction (a click, a text entry, a paste), but the step-level
columns (`Process Step Active Duration`, `Copy No.`, `Clicks No.` …) are repeated on every interaction row of the step.
Summed over rows they would multiply every counter by the number of interactions, so rows are grouped by `(user, step start, step name)` first and counters are read once per step. Steps split by a
chunk boundary of the streaming reader are joined again. When an export has no counter columns, the interaction types
are counted instead (and normalised: `Click`, `mouse`, `Text entry`, `text-entry` …).

The exporter appends an `Applied filters / Time zone / Time interval` footer that looks like data rows. Rows whose
only non-empty cell is the first one and contains a colon are taken off and kept as export metadata.

## 2. Finding the cases

**Shape voting.** Business IDs come from OCR and an AI extractor, so many are noise (`kypidbuser`, `2026`, `PRO-1`).
Each ID is reduced to its shape (`INV-2026-04812` → `AAA-9999-99999`); a shape is kept only if it is at least half as
common as the most common one.

**Case attribution.** Most steps carry no ID, and people juggle cases: an invoice waits for approval while others are
processed, then gets posted between two unrelated ones. Giving an untagged step to its neighbours is therefore wrong.
A first-order Markov model `P(next activity | activity)` is learned from the steps whose case is certain, and each
untagged step joins the case most likely to continue with it: one of the user's open cases, scored by
`P(step | that case's last activity)`, or the case starting right after it, scored by `P(its first step | step)`.
Below a probability of 0.05 the step stays unassigned instead of being forced somewhere.

If fewer than half of the steps end up in a case, cases become **work sessions**: a person's steps until a break of
30 minutes or more (a gap between steps or idle time inside one).

**Cut-off cases.** An export covers fixed dates, so some cases were already running on the first day or still open on
the last. The usual start and end activities are learned from cases well inside the window; a case near an edge that
does not start or end like them is left out of variant, map and duration statistics.

## 3. Mining

**Process map.** For each pair of activities the Heuristics Miner dependency
`(|a>b| − |b>a|) / (|a>b| + |b>a| + 1)` says whether `b` reliably follows `a`. Edges below 0.5 are dropped. The two
sliders keep activities and paths used by at least a given share of cases; every activity keeps its strongest in and
out edge, and anything not on a path from start to end is removed. The same rules produce the BPMN export, where an
activity with several outgoing paths gets an exclusive split gateway and one with several incoming paths a join.

**Variants.** Each variant is aligned with the most common path (difflib's sequence matcher). The opcodes say whether a
step was skipped, inserted or replaced, and counting them gives the typical deviations.

**Bottlenecks.** Two kinds, each ranked against its own kind, because working time and calendar waiting time are
different units:

| Steps | weight | Hand-overs | weight |
| --- | --- | --- | --- |
| hours spent in the step | 35% | total waiting time | 45% |
| rework: cases that repeat it | 20% | typical (median) wait | 30% |
| long tail: p90 / median duration | 15% | share of cases passing through | 25% |
| idle share inside the step | 15% | | |
| betweenness centrality on the process graph | 15% | | |

Each signal becomes a percentile rank and the score is the weighted average, so the dashboard can show why a step
scored as it did. Severity needs absolute weight too: a step under 8% of tracked time cannot be critical (under 3%, not even high), nor a
hand-over on the path of fewer than 15% of cases. Hand-overs with a typical wait under five minutes do not qualify.
When cases are work sessions the rework signal is switched off (coming back to a tool is multitasking, not rework).

**Automation candidates** are scored on hours per week (30%), volume (20%), manual inputs per minute (20%), copy-paste
transfers per run (15%) and predictability (15%), where predictability is `1 − H(next step) / log2(#next steps)`. The
approach follows the dominant signal (document extraction, system integration, RPA data entry, workflow rule,
assisted RPA) and the saving uses a conservative rate per approach (25–60%).

**Copy-paste flows.** Every paste is matched to the latest copy or cut of the same user within ten minutes
(`merge_asof`). A match across two applications is data carried by hand.

**Routines** are sequences of 3–6 consecutive steps repeated across cases; a pattern is dropped when a one-step-longer
pattern explains at least 90% of its support, so the list shows whole routines rather than fragments.

**People.** The speed index compares each person with the team median on the same activities and averages the ratios
(geometric mean weighted by volume). People with fewer than 20 comparable executions get no index.

**Unusual cases.** An Isolation Forest runs on log-scaled case features (duration, steps, repeats, waiting share,
applications); flagged cases are explained by the features with a robust z-score (median and MAD) above 2.5.

## 4. Why a step is slow, and what to do

A score says that a step matters; `mining/diagnosis.py` says why. Every interaction row in a KYP export has its own
duration, and together they cover the step, so a step's time splits into typing, clicking and scrolling, copy-paste,
looking at the screen and time with no input. Next to that the diagnosis collects the window titles the step happens
in, the steps before and after it, the values pasted in (and from where) and copied out (and to where), the quick
trips to another application, the spread between people, and the slowest runs.

Each measurement that crosses a threshold becomes a cause with its evidence, a concrete action and the hours per day
or week it concerns, biggest first:

| Cause | Fires when | Suggested fix |
| --- | --- | --- |
| Data re-keyed | ≥ 0.5 values per run pasted in from another app | document AI for PDFs and scans, otherwise an integration or import |
| Results copied on | ≥ 0.5 values per run pasted into a later step | send the result automatically |
| Look-ups | ≥ 0.5 quick trips (A → B → A in 2 min) per run | bring the information into the main screen |
| Manual typing | ≥ 5 text entries per run | pre-fill, templates, validation |
| Nobody working | ≥ 15% of the step without input; breaks of 10+ min counted and listed | find out what people wait for |
| Slow outliers | p90 ≥ 3 × median; the slow runs' own time split names the reason | depends on what the slow runs are made of |
| Rework | ≥ 5% of cases come back through the same loop | catch the reason at the first pass |
| People | slowest person ≥ 1.6 × the fastest on the same step | compare methods, write down the faster one |

Hand-overs get their own causes: approval queues, waiting for an outside reply, work resuming only the next day, and a
different person continuing the case. Automation candidates also get a blueprint: the steps the automation would take
over, written from what was observed (trigger, inputs, the screen it fills, where the result goes).

## 5. Checking it against ground truth

The synthetic accounts-payable team has known behaviour planted in it, and `tests/test_end_to_end.py` checks that the
engine finds it: the approval wait among the top bottlenecks, the missing-PO loop at its planted rate (about 17.5% of
invoices), PDF → SAP copy-paste, and the slower clerk.

One limit is known and visible in the data: when several invoices wait for approval, an untagged "Post invoice"
step cannot be tied to one of them with certainty. It goes to the one that has waited longest, so a small share of
cases still look as if they skipped posting.
