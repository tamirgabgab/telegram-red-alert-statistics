// Visual check of the dashboard: screenshots at desktop and mobile width, light and dark, every tab.
//
// Usage (with the dashboard running: streamlit run dashboard.py):
//   npm install --no-save playwright && npx playwright install chromium   # once
//   node tools/screenshots.js [url] [out_dir]
// Defaults: http://localhost:8501 and ./screenshots/ (git-ignored).
// Prints horizontal overflow, Streamlit exceptions and page errors per case; exits 1 if any were found.

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const url = process.argv[2] || 'http://localhost:8501';
const outDir = process.argv[3] || path.join(process.cwd(), 'screenshots');
const CASES = [
  ['desktop-light', { width: 1280, height: 900 }, 'light'],
  ['desktop-dark', { width: 1280, height: 900 }, 'dark'],
  // Streamlit scrolls inside its own container on narrow screens, so a tall viewport stands in for fullPage.
  ['mobile-light', { width: 375, height: 2200 }, 'light'],
  ['mobile-dark', { width: 375, height: 2200 }, 'dark'],
];

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  let problems = 0;
  for (const [name, viewport, colorScheme] of CASES) {
    const page = await browser.newPage({ viewport, colorScheme, locale: 'he-IL' });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(url, { waitUntil: 'networkidle' });
    await page.waitForSelector('.ra-kpis', { timeout: 60000 });
    await page.waitForTimeout(3000);

    const tabs = await page.$$('[role="tab"]');
    for (let i = 0; i < tabs.length; i++) {
      if (i > 0) {
        await tabs[i].click();
        await page.waitForTimeout(2000);
      }
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      const exceptions = await page.$$eval('[data-testid="stException"]', els => els.length);
      if (overflow > 0 || exceptions > 0) problems++;
      const file = path.join(outDir, `${name}-tab${i}.png`);
      await page.screenshot({ path: file, fullPage: true });
      console.log(`${name} tab${i}: overflowX=${overflow} exceptions=${exceptions} -> ${file}`);
    }
    if (errors.length) {
      problems++;
      console.log(`${name}: page errors: ${errors.join(' | ')}`);
    }
    await page.close();
  }
  await browser.close();
  process.exit(problems ? 1 : 0);
})();
