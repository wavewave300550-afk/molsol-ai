// End-to-end smoke test in headless Chromium (phone-sized, touch enabled).
// Needs the dev server (npm run dev) or a preview of the build: URL=http://localhost:4173 npm run smoke
import { loadPlaywright, GL_ARGS } from './_pw.mjs';

const { chromium } = await loadPlaywright();
const base = process.env.URL || 'http://localhost:5173';
const shots = process.env.SHOTS || '';
const browser = await chromium.launch({ args: GL_ARGS });
const ctx = await browser.newContext({ viewport: { width: 844, height: 390 }, hasTouch: true, isMobile: true });
const page = await ctx.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(String(e)));
page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));

let failed = 0;
const check = (name, ok, info = '') => {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${info ? '  — ' + info : ''}`);
  if (!ok) failed++;
};
const G = (fn, arg) => page.evaluate(fn, arg);
const shot = async (n) => shots && page.screenshot({ path: `${shots}/${n}.png` });

await page.goto(base + '/?laps=1');
await page.waitForFunction(() => window.__riftriot?.app.state === 'title', null, { timeout: 60000 });
check('title screen shows', await page.isVisible('#btnStart'));
await shot('01-title');

// ── select ──
await page.tap('#btnStart');
check('character select opens', await page.isVisible('#select'));
const roster = await page.$$eval('#roster button', (b) => b.map((x) => ({ id: x.dataset.id, img: x.style.backgroundImage.length > 100 })));
check('six racers on the roster, all free', roster.length === 6, roster.map((r) => r.id).join(','));
check('roster shows rendered 3D thumbnails', roster.every((r) => r.img));
for (const r of roster) {
  await page.tap(`#roster button[data-id="${r.id}"]`);
  const name = await page.textContent('#selName');
  const shown = await G(() => window.__riftriot.view.showcaseId);
  if (shown !== r.id || !name) check(`select ${r.id}`, false);
}
check('every racer selectable, showcase model switches', true);
await page.tap('#roster button[data-id="gator"]');
await shot('02-select');

// ── race ──
await page.tap('#btnRace');
let st = await G(() => ({ state: window.__riftriot.app.state, phase: window.__riftriot.app.race.phase, id: window.__riftriot.app.race.player.def.id }));
check('race starts with the chosen racer', st.state === 'race' && st.id === 'gator', JSON.stringify(st));
check('countdown before GO', st.phase === 'countdown');
await page.tap('#btnSkill');
await page.waitForTimeout(100);
check('skill blocked before GO', (await G(() => window.__riftriot.app.race.player.sk.uses)) === 0);
await page.waitForFunction(() => window.__riftriot.app.race.phase === 'racing', null, { timeout: 15000 });

// multi-touch: hold steer + drift together, then tap skill, while checking the page never moves
const pad = await page.$('#steerPad');
const drift = await page.$('#btnDrift');
const pb = await pad.boundingBox();
const db = await drift.boundingBox();
const cdp = await ctx.newCDPSession(page);
const tp = (id, b, fx = 0.5) => ({ x: b.x + b.width * fx, y: b.y + b.height / 2, id });
await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [tp(1, pb, 0.95)] });
await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [tp(1, pb, 0.95), tp(2, db)] });
await page.waitForTimeout(400);
const ctl = await G(() => ({ steer: window.__riftriot.input.touchSteer, drift: window.__riftriot.input.touchDrift, auto: window.__riftriot.input.autoGas }));
await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [tp(1, pb, 0.05), tp(2, db)] });
await page.waitForTimeout(200);
const ctl2 = await G(() => window.__riftriot.input.touchSteer);
await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
check('two-finger steer + drift at once', ctl.steer > 0.5 && ctl.drift === true && ctl.auto === true, JSON.stringify(ctl));
check('steer follows the thumb (right → left)', ctl2 < -0.5, String(ctl2));
const view = await G(() => ({ sx: window.scrollX, sy: window.scrollY, scale: window.visualViewport ? window.visualViewport.scale : 1 }));
check('page did not scroll or zoom', view.sx === 0 && view.sy === 0 && view.scale === 1, JSON.stringify(view));
await page.tap('#btnSkill');
await page.waitForTimeout(150);
const sk = await G(() => ({ uses: window.__riftriot.app.race.player.sk.uses, phase: window.__riftriot.app.race.player.sk.phase }));
check('skill button fires the skill', sk.uses === 1 && sk.phase === 'active', JSON.stringify(sk));
await page.waitForTimeout(600);
await shot('03-race-skill');

// ── pause freezes everything ──
await page.tap('#btnPause');
const p0 = await G(() => { const r = window.__riftriot.app.race; return { t: r.time, cd: r.player.sk.cd, ai: r.racers.map((x) => x.x + x.z).join(), paused: window.__riftriot.app.paused }; });
await page.waitForTimeout(1500);
const p1 = await G(() => { const r = window.__riftriot.app.race; return { t: r.time, cd: r.player.sk.cd, ai: r.racers.map((x) => x.x + x.z).join() }; });
check('pause stops race clock, cooldowns and AI', p0.paused && p0.t === p1.t && p0.cd === p1.cd && p0.ai === p1.ai);
await shot('04-pause');
await page.tap('#btnResume');
await page.waitForTimeout(500);
check('resume continues the race', (await G(() => window.__riftriot.app.race.time)) > p1.t);

// hidden tab → auto pause
await G(() => {
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
  document.dispatchEvent(new Event('visibilitychange'));
});
check('switching away pauses the race', await G(() => window.__riftriot.app.paused));
await G(() => {
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => false });
  document.dispatchEvent(new Event('visibilitychange'));
});
await page.tap('#btnResume');

// ── finish: let the AI drive the player's racer and fast-forward the simulation ──
await G(() => {
  const a = window.__riftriot.app;
  a.race.autopilot = true;
  for (let i = 0; i < 60 * 200 && a.race.phase !== 'finished'; i++) a.race.step(1 / 60);
});
await page.waitForSelector('#results:not(.hidden)', { timeout: 15000 });
const res = await G(() => ({ rows: window.__riftriot.app.race.results(), place: window.__riftriot.app.race.player.place, time: window.__riftriot.app.race.player.finishTime }));
const li = await page.$$eval('#resList li', (l) => l.map((x) => x.textContent));
check('results screen lists all six', li.length === 6, li.join(' | '));
check('player result is a real recorded finish', res.place >= 1 && res.time > 0, JSON.stringify({ place: res.place, time: res.time }));
check('unfinished racers are not given fake times', res.rows.every((r) => (r.finished ? r.time > 0 : r.time === null)));
await shot('05-results');
// let the rest of the field finish, results update with their real times
await G(() => {
  const a = window.__riftriot.app;
  for (let i = 0; i < 60 * 70 && !a.race.done; i++) a.race.step(1 / 60);
});
await page.waitForTimeout(400);
const done = await G(() => window.__riftriot.app.race.results());
check('field finishes; order is 1..6 by real time', done.map((r) => r.place).join() === '1,2,3,4,5,6' && done.every((r, i) => !i || !r.finished || !done[i - 1].finished || r.time >= done[i - 1].time));

// ── race again a few times: nothing accumulates ──
const mem = [];
for (let k = 0; k < 3; k++) {
  await page.tap('#btnAgain');
  await page.waitForTimeout(200);
  await G(() => {
    const a = window.__riftriot.app;
    a.race.autopilot = true;
    for (let i = 0; i < 60 * 200 && a.race.phase !== 'finished'; i++) {
      a.race.step(1 / 60);
      if (i % 30 === 0) {
        window.__riftriot.view.update(1 / 60, 1);
        window.__riftriot.view.handleEvents(a.race.events);
        a.race.events.length = 0;
      }
    }
  });
  await page.waitForSelector('#results:not(.hidden)', { timeout: 15000 });
  mem.push(await G(() => ({ geo: window.__riftriot.renderer.info.memory.geometries, tex: window.__riftriot.renderer.info.memory.textures, kids: window.__riftriot.view.scene.children.length, slick: window.__riftriot.view.effects.slickMesh.count, parts: window.__riftriot.view.effects.particles.n })));
}
check('repeat races do not leak geometry/textures/scene objects', mem[2].geo <= mem[0].geo + 2 && mem[2].tex <= mem[0].tex + 2 && mem[2].kids === mem[0].kids, JSON.stringify(mem));

// ── back to select and to title ──
await page.tap('#btnPick');
check('back to character select', await page.isVisible('#select'));
await page.tap('#btnBack');
check('back to title', await page.isVisible('#title'));

// keyboard on a desktop-sized page
await page.tap('#btnStart');
await page.tap('#btnRace');
await page.waitForFunction(() => window.__riftriot.app.race.phase === 'racing', null, { timeout: 15000 });
await page.keyboard.down('KeyW');
await page.keyboard.down('KeyD');
await page.waitForTimeout(300);
const kb = await G(() => ({ ...window.__riftriot.app.race.player.input }));
await page.keyboard.press('KeyE');
await page.waitForTimeout(100);
const kbSkill = await G(() => window.__riftriot.app.race.player.sk.uses);
await page.keyboard.press('Escape');
const kbPause = await G(() => window.__riftriot.app.paused);
await page.keyboard.up('KeyW');
await page.keyboard.up('KeyD');
check('keyboard: W throttle, D steer, E skill, Esc pause', kb.throttle === 1 && kb.steer === 1 && kbSkill === 1 && kbPause, JSON.stringify({ kb, kbSkill, kbPause }));

const fps = await G(() => window.__riftriot.app.fps);
console.log(`info  measured fps in this headless software-GL browser: ${fps.toFixed(1)} (not representative of a phone GPU)`);
check('no page errors', errors.length === 0, errors.slice(0, 5).join(' | '));
await browser.close();
console.log(failed ? `\n${failed} check(s) FAILED` : '\nall checks passed');
process.exit(failed ? 1 : 0);
