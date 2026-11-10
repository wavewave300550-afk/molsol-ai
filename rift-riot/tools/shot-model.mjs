// Dev helper: node tools/shot-model.mjs <model> <out.png> [extra query]
// Renders front-3/4, side, and race-camera (behind) views into one contact sheet.
import { loadPlaywright, GL_ARGS } from './_pw.mjs';
const { chromium } = await loadPlaywright();
const [model, out, extra = ''] = process.argv.slice(2);
const base = process.env.URL || 'http://localhost:5173';
const b = await chromium.launch({ args: GL_ARGS });
const views = [ 'yaw=0.75&h=3.5', 'yaw=1.6&h=2.2', 'yaw=3.14&h=4.3&d=10', 'yaw=-2.3&h=3' ];
const page = await b.newPage({ viewport: { width: 520, height: 520 } });
const shots = [];
for (const v of views) {
  await page.goto(`${base}/preview.html?m=${model}&${v}&${extra}`);
  await page.waitForFunction('window.__ready === true', null, { timeout: 20000 });
  shots.push((await page.screenshot()).toString('base64'));
}
await page.setViewportSize({ width: 1040, height: 1040 });
await page.setContent(`<body style="margin:0;display:grid;grid-template-columns:520px 520px">${shots.map((s) => `<img src="data:image/png;base64,${s}">`).join('')}</body>`);
await page.screenshot({ path: out });
await b.close();
