// Records a short walk through the demo dataset and turns it into docs/readme/demo.gif (needs ffmpeg on PATH).
// Usage: node record-demo.mjs [baseUrl]
import { execFileSync } from 'node:child_process'
import { mkdtemp, readdir, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const base = process.argv[2] ?? 'http://localhost:3000'
const size = { width: 1440, height: 900 }
const videos = await mkdtemp(join(tmpdir(), 'worktrace-demo-'))

const browser = await chromium.launch()
const context = await browser.newContext({ viewport: size, recordVideo: { dir: videos, size } })
const page = await context.newPage()
const pause = (ms) => page.waitForTimeout(ms)
const tab = (name) => page.getByRole('navigation', { name: 'Analysis sections' }).getByRole('button', { name })

await page.goto(base)
await page.waitForLoadState('networkidle')
await pause(1200)
await page.getByText('Accounts payable team').click()
await page.getByRole('navigation', { name: 'Analysis sections' }).waitFor({ timeout: 120_000 })
await pause(2200)
await tab('Process map').click()
await pause(2000)
const paths = page.getByRole('slider').nth(1)
await paths.focus()
for (let step = 0; step < 3; step++) {
  await page.keyboard.press('ArrowLeft')
  await pause(450)
}
await pause(1200)
await page.getByRole('tab', { name: 'Waiting time' }).click()
await pause(1800)
await tab('Bottlenecks').click()
await pause(2200)
await page.getByRole('button', { name: /Request approval/ }).first().click()
await pause(2200)
await tab('Automation').click()
await pause(2400)
await tab('People').click()
await page.mouse.wheel(0, 650)
await pause(2400)
await context.close()
await browser.close()

const [video] = await readdir(videos)
const palette = join(videos, 'palette.png')
const source = join(videos, video)
const filters = 'fps=10,scale=1100:-1:flags=lanczos'
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', source, '-vf', `${filters},palettegen=stats_mode=diff`, palette])
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', source, '-i', palette, '-lavfi', `${filters} [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=5`, resolve(root, 'docs/readme/demo.gif')])
await rm(videos, { recursive: true, force: true })
console.log('  docs/readme/demo.gif')
