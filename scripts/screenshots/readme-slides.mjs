// Renders the README as a sequence of slides (headline + the real screen). Run `npm run screenshots` first.
// Usage: node readme-slides.mjs
import { readFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const images = resolve(root, 'docs/images')
const out = resolve(root, 'docs/readme')
const image = async (name) => `data:image/jpeg;base64,${(await readFile(resolve(images, name))).toString('base64')}`

const width = 1600
const css = `
:root { --desk: #eceef0; --surface: #ffffff; --line: #dfe2e6; --ink: #0e141b; --ink-2: #39434e; --ink-3: #5b6672; --accent: #1c5cab; --amber: #eda100; }
html, body { margin: 0; }
body { width: ${width}px; font-family: 'Instrument Sans', sans-serif; color: var(--ink); -webkit-font-smoothing: antialiased;
  background: var(--desk); background-image: radial-gradient(70% 90% at 100% 0%, #dde6f1, transparent 60%); }
.slide { box-sizing: border-box; padding: 96px 120px 110px; display: grid; gap: 56px; }
h1, h2 { margin: 0; font-family: 'Bricolage Grotesque', sans-serif; font-weight: 600; letter-spacing: -0.04em; line-height: 0.98; text-wrap: balance; }
h1 { font-size: 104px; max-width: 12ch; }
h2 { font-size: 72px; max-width: 17ch; }
h1 em, h2 em { font-style: normal; color: var(--accent); }
p { margin: 0; font-size: 30px; line-height: 1.4; color: var(--ink-2); max-width: 40ch; text-wrap: pretty; }
.name { display: flex; align-items: center; gap: 14px; font-family: 'Bricolage Grotesque', sans-serif; font-size: 32px; font-weight: 600; letter-spacing: -0.02em; }
.award { display: flex; align-items: center; gap: 12px; font-size: 24px; color: var(--ink-2); }
.head { display: grid; gap: 26px; }
.screen { width: 100%; border-radius: 18px; display: block; border: 1px solid var(--line); box-shadow: 0 2px 4px rgb(14 20 27 / 0.05), 0 30px 60px -28px rgb(14 20 27 / 0.35); }
.tilt { transform: perspective(2400px) rotateX(4deg) rotate(-1deg); transform-origin: 50% 0; }
.crop { overflow: hidden; border-radius: 18px; max-height: 760px; border: 1px solid var(--line); box-shadow: 0 30px 60px -28px rgb(14 20 27 / 0.35); }
.crop img { display: block; width: 100%; }
.board { background: var(--ink); color: #eef1f4; border-radius: 22px; padding: 44px 56px; font-family: 'JetBrains Mono', monospace; font-size: 30px; line-height: 1.75; }
.board .dim { color: #8b96a3; }
.board .ok { color: #7cc4ff; }
.facts { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border-top: 2px solid var(--ink); }
.facts div { padding: 34px 36px 8px 0; display: grid; align-content: start; gap: 10px; }
.facts strong { font-family: 'Bricolage Grotesque', sans-serif; font-size: 31px; letter-spacing: -0.02em; line-height: 1.12; }
.facts span { font-size: 22px; line-height: 1.45; color: var(--ink-2); }
table { width: 100%; border-collapse: collapse; font-size: 26px; background: var(--surface); border-radius: 18px; overflow: hidden; box-shadow: 0 30px 60px -32px rgb(14 20 27 / 0.3); }
th, td { text-align: left; padding: 24px 32px; border-bottom: 1px solid var(--line); }
th { font-size: 19px; font-weight: 600; color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.06em; }
td.num { font-variant-numeric: tabular-nums; text-align: right; white-space: nowrap; }
td.bad { color: #b42f2f; text-decoration: line-through; text-decoration-thickness: 2px; }
td.good { font-weight: 600; }
tr:last-child td { border-bottom: 0; }
`

const logo = `<svg width="38" height="38" viewBox="0 0 24 24"><rect x="1" y="1" width="22" height="22" rx="6" fill="#0e141b"/><path d="M6 15.5 9.5 9l3.5 5 3-3.5 2 2.5" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="18" cy="13" r="1.6" fill="#2a78d6"/></svg>`
const trophy = `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#eda100" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/></svg>`

const slides = {
  hero: async () => `<div class="slide"><div class="head"><div class="name">${logo} WorkTrace</div>
    <h1>See how work <em>really</em> flows.</h1>
    <p>Process and task mining for the clicks, keystrokes and copy-pastes behind a business process.</p>
    <div class="award">${trophy} First place at AI Krak Hack 2026, Process-to-Automation Copilot challenge</div></div>
    <img class="screen tilt" src="${await image('ap-overview.jpg')}"></div>`,
  raw: async () => `<div class="slide"><div class="head"><h2>Built for raw task-mining data</h2>
    <p>The challenge came with exports straight from KYP.ai: every click and keystroke, nothing cleaned. WorkTrace reads them for what they are.</p></div>
    <div class="facts">
      <div><strong>Steps, not rows</strong><span>8,978 interaction rows of the real export become 1,858 process steps; each counter is read once.</span></div>
      <div><strong>Time per interaction</strong><span>Every row carries its duration, so each step splits into typing, clicking, copy-paste and time with no input.</span></div>
      <div><strong>Footers and broken rows</strong><span>The exporter's “Applied filters” block becomes metadata instead of four extra users.</span></div>
      <div><strong>IDs read by OCR</strong><span>Shape voting drops noise like “kypidbuser” or “2026”; a Markov model gives untagged steps their case.</span></div>
      <div><strong>Cases cut by the window</strong><span>Invoices still waiting on the last day do not pose as process deviations.</span></div>
      <div><strong>Any event log too</strong><span>Case, activity and timestamp columns are found by name, from Celonis, Disco or a spreadsheet.</span></div>
    </div></div>`,
  diagnosis: async () => `<div class="slide"><div class="head"><h2>Not just what is slow. Why, and what to do.</h2>
    <p>Real data: one KYP.ai step is 60% time with no input, and its slowest runs are pauses, not work. The runs to look at are listed.</p></div>
    <div class="crop"><img src="${await image('kyp-bottlenecks.jpg')}"></div></div>`,
  map: async () => `<div class="slide"><div class="head"><h2>The process as it runs, not as the wiki says</h2>
    <p>Heuristics-miner map with two dials for detail, waiting times on every hand-over, and a BPMN export.</p></div>
    <div class="crop"><img src="${await image('ap-map.jpg')}"></div></div>`,
  bottlenecks: async () => `<div class="slide"><div class="head"><h2>Bottlenecks ranked by evidence, not a threshold</h2>
    <p>Each bottleneck opens into what happens in the step, the causes with their evidence, and the action to take.</p></div>
    <div class="crop"><img src="${await image('ap-bottlenecks.jpg')}"></div></div>`,
  automation: async () => `<div class="slide"><div class="head"><h2>What to automate first, and how</h2>
    <p>Each candidate comes with the steps the automation would take over, written from what people do today.</p></div>
    <div class="crop"><img src="${await image('ap-automation.jpg')}"></div></div>`,
  people: async () => `<div class="slide"><div class="head"><h2>Fair comparisons between people</h2>
    <p>Speed compared on the same activities, never on raw totals. A day of each person's work at a glance.</p></div>
    <div class="crop"><img src="${await image('ap-people-full.jpg')}"></div></div>`,
  engineering: async () => `<div class="slide"><div class="head"><h2>Real algorithms, small and readable</h2>
    <p>Python 3.12, pandas, networkx and scikit-learn behind FastAPI. Next.js 16 in front. 31 tests.</p></div>
    <div class="facts">
      <div><strong>Steps, not rows</strong><span>Interaction rows collapse into process steps; every counter is read once.</span></div>
      <div><strong>Cases from noisy IDs</strong><span>Shape voting rejects OCR noise; a Markov model attributes untagged steps.</span></div>
      <div><strong>Cut-off cases left out</strong><span>Cases clipped by the export window do not pose as deviations.</span></div>
      <div><strong>Heuristics Miner + BPMN</strong><span>Dependency measure, start-to-end pruning, XOR gateways where paths split.</span></div>
      <div><strong>Variants by alignment</strong><span>Sequence alignment says which step was skipped, added or swapped.</span></div>
      <div><strong>Isolation Forest</strong><span>Unusual cases flagged, then explained with robust z-scores.</span></div>
    </div></div>`,
  run: async () => `<div class="slide"><div class="head"><h2>Running on your machine in two commands</h2>
    <p>Two demo datasets ship with it: a real KYP.ai day and a synthetic three-week AP team.</p></div>
    <div class="board"><span class="dim">$</span> cd backend &amp;&amp; uv run uvicorn worktrace.api.app:app<br><span class="dim">$</span> cd frontend &amp;&amp; npm install &amp;&amp; npm run dev<br><span class="ok">→ http://localhost:3000</span><br><br><span class="dim"># or both in containers</span><br><span class="dim">$</span> docker compose up</div></div>`,
}

const browser = await chromium.launch()
try {
  const page = await browser.newPage({ viewport: { width, height: 900 }, deviceScaleFactor: 1 })
  for (const [name, build] of Object.entries(slides)) {
    await page.setContent(`<!doctype html><html><head>
      <link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600&family=Instrument+Sans:wght@400;600&family=JetBrains+Mono&display=swap" rel="stylesheet">
      <style>${css}</style></head><body>${await build()}</body></html>`, { waitUntil: 'networkidle' })
    await page.evaluate(() => document.fonts.ready)
    await page.locator('.slide').screenshot({ path: resolve(out, `${name}.jpg`), type: 'jpeg', quality: 86 })
    console.log(`  docs/readme/${name}.jpg`)
  }
} finally {
  await browser.close()
}
