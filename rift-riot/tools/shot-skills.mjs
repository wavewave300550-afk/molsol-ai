// Dev helper: one in-race screenshot per racer with the skill active (autopilot drives).
// node tools/shot-skills.mjs <out.png> [delayMs] [afterSkillMs]
import { loadPlaywright, GL_ARGS } from './_pw.mjs';
const { chromium } = await loadPlaywright();
const out = process.argv[2];
const delay = Number(process.argv[3] || 6500);
const after = Number(process.argv[4] || 700);
const only = process.argv[5];
const base = process.env.URL || 'http://localhost:5173';
const b = await chromium.launch({ args: GL_ARGS });
const ids = only ? [only] : ['boonsong', 'baby', 'celestine', 'granny', 'lovers', 'gator'];
const shots = [];
const errors = [];
for (const id of ids) {
  const ctx = await b.newContext({ viewport: { width: 844, height: 390 }, hasTouch: true, isMobile: true });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => errors.push(id + ': ' + e));
  await page.goto(base + '/?autopilot=1');
  await page.waitForFunction('window.__riftriot && window.__riftriot.app.state === "title"', null, { timeout: 60000 });
  await page.evaluate((i) => { const g = window.__riftriot; g.selectRacer(i, true); g.startRace(); }, id);
  await page.waitForTimeout(delay);
  await page.tap('#btnSkill');
  await page.waitForTimeout(after);
  shots.push((await page.screenshot()).toString('base64'));
  await ctx.close();
}
const page = await b.newPage({ viewport: { width: 844 * Math.min(2, ids.length), height: 390 * Math.ceil(ids.length / 2) } });
await page.setContent(`<body style="margin:0;display:grid;grid-template-columns:repeat(${Math.min(2, ids.length)},844px)">${shots.map((s) => `<img src="data:image/png;base64,${s}">`).join('')}</body>`);
await page.screenshot({ path: out });
if (errors.length) console.log('ERRORS\n' + errors.join('\n'));
await b.close();
