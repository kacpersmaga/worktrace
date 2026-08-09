// Captures every dashboard tab of the demo datasets into docs/images. Needs the API and web app running.
// Usage: node screenshots.mjs [baseUrl]
import { mkdir } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const out = resolve(root, 'docs/images')
const base = process.argv[2] ?? 'http://localhost:3000'
const tabs = ['overview', 'map', 'bottlenecks', 'variants', 'automation', 'people', 'quality']
const demos = { 'accounts-payable': 'ap', 'kyp-pilot-day': 'kyp' }

await mkdir(out, { recursive: true })
const browser = await chromium.launch()
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })
  await page.goto(base)
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: resolve(out, 'home.jpg'), type: 'jpeg', quality: 90 })
  for (const [demo, short] of Object.entries(demos)) {
    for (const tab of tabs) {
      await page.goto(`${base}/analysis/demo-${demo}?tab=${tab}`)
      await page.getByRole('navigation', { name: 'Analysis sections' }).waitFor({ timeout: 180_000 })
      await page.waitForTimeout(tab === 'map' ? 2500 : 800)
      await page.screenshot({ path: resolve(out, `${short}-${tab}.jpg`), type: 'jpeg', quality: 90 })
      await page.screenshot({ path: resolve(out, `${short}-${tab}-full.jpg`), type: 'jpeg', quality: 85, fullPage: true })
      console.log(`  docs/images/${short}-${tab}.jpg`)
    }
  }
  await page.goto(`${base}/analysis/demo-accounts-payable?tab=map`)
  await page.getByRole('tab', { name: 'BPMN model' }).click()
  await page.locator('.djs-container').waitFor({ timeout: 60_000 })
  await page.waitForTimeout(1500)
  await page.screenshot({ path: resolve(out, 'ap-bpmn.jpg'), type: 'jpeg', quality: 90 })
} finally {
  await browser.close()
}
