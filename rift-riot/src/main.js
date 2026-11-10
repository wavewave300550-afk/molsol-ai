// RIFT RIOT — application shell: boot, screens, the frame loop.
import * as THREE from 'three';
import { BALANCE } from './data/balance.js';
import { RACERS, RACER_BY_ID } from './data/racers.js';
import { Track } from './sim/track.js';
import { RIFT_JUNCTION } from './sim/trackData.js';
import { Race, FixedLoop } from './sim/race.js';
import { GameView } from './render/view.js';
import { GameAudio } from './audio/audio.js';
import { Input } from './ui/input.js';
import { Hud, SKILL_ICON, fmtTime } from './ui/hud.js';

const $ = (id) => document.getElementById(id);
const ui = $('ui');
const canvas = $('game');

const QUALITY = {
  low: { label: 'ต่ำ', maxPR: 1, particleRate: 0.5 },
  mid: { label: 'กลาง', maxPR: 1.5, particleRate: 0.8 },
  high: { label: 'สูง', maxPR: 2, particleRate: 1 },
  auto: { label: 'อัตโนมัติ', maxPR: 2, particleRate: 1 },
};
const store = {
  get(k, d) {
    try {
      const v = localStorage.getItem('riftriot.' + k);
      return v === null ? d : v;
    } catch {
      return d;
    }
  },
  set(k, v) {
    try {
      localStorage.setItem('riftriot.' + k, v);
    } catch {
      /* private mode: settings just do not persist */
    }
  },
};

const app = {
  state: 'loading',
  paused: false,
  race: null,
  loop: null,
  selected: store.get('racer', 'boonsong'),
  quality: store.get('quality', 'auto'),
  pr: 1,
  fps: 60,
  frameMs: [],
  resultsShown: false,
  resultsTimer: 0,
  finalLapAnnounced: false,
  seed: (Date.now() % 100000) + 1,
};

// ── boot ────────────────────────────────────────────────────────────────────
const PARAMS = new URLSearchParams(location.search);
const AUTOPILOT = PARAMS.has('autopilot'); // dev/test only: the AI drives your racer
const LAPS = PARAMS.has('laps') ? Math.max(1, Number(PARAMS.get('laps')) || 3) : BALANCE.race.laps;
const touch = matchMedia('(pointer: coarse)').matches || 'ontouchstart' in window;
document.body.classList.toggle('touch', touch);

let renderer;
try {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
} catch (err) {
  $('loadingText').textContent = 'อุปกรณ์นี้เปิด WebGL ไม่ได้ ลองใช้ Safari หรือ Chrome รุ่นใหม่';
  throw err;
}
renderer.outputColorSpace = THREE.SRGBColorSpace;
const track = new Track(RIFT_JUNCTION);
const qCfg = QUALITY[app.quality] || QUALITY.auto;
const mobile = touch && Math.min(screen.width, screen.height) < 820;
const view = new GameView(renderer, track, { particles: mobile ? 380 : 560, particleRate: qCfg.particleRate, detail: mobile ? 0.7 : 1 });
const audio = new GameAudio();
const input = new Input(ui);
const hud = new Hud(ui, track);

function applyQuality() {
  const q = QUALITY[app.quality] || QUALITY.auto;
  app.pr = Math.min(window.devicePixelRatio || 1, q.maxPR);
  view.effects.rate = q.particleRate;
  $('btnQuality').textContent = 'ภาพ: ' + q.label;
  resize();
}
function resize() {
  const w = window.innerWidth;
  const h = window.innerHeight;
  renderer.setPixelRatio(app.pr);
  renderer.setSize(w, h, false);
  view.resize();
  const portrait = h > w * 1.1;
  const showRotate = portrait && touch && !app.rotateDismissed && app.state === 'race';
  $('rotate').classList.toggle('hidden', !showRotate);
  if (showRotate && !app.rotateTimer) {
    // a gentle hint, not a blocker: it goes away by itself
    app.rotateTimer = setTimeout(() => {
      app.rotateDismissed = true;
      $('rotate').classList.add('hidden');
    }, 5000);
  }
}
window.addEventListener('resize', resize);
window.addEventListener('orientationchange', () => setTimeout(resize, 250));
if (window.visualViewport) window.visualViewport.addEventListener('resize', resize);

// ── screens ─────────────────────────────────────────────────────────────────
function show(id) {
  for (const s of ['loading', 'title', 'select', 'hud', 'pause', 'results']) $(s).classList.toggle('hidden', s !== id && !(id === 'pause' && s === 'hud') && !(id === 'results' && s === 'hud'));
}

function startAttract() {
  // an all-AI race runs behind the title screen (also a nice soak test)
  app.race = new Race(track, { playerId: null, seed: app.seed++ });
  app.race.countdown = 0.5;
  app.loop = new FixedLoop(app.race);
  view.setRace(app.race, 'tv');
}

function goTitle() {
  app.state = 'title';
  app.paused = false;
  input.enabled = false;
  audio.stopEngine();
  startAttract();
  show('title');
  $('titleHint').textContent = touch
    ? 'เร่งอัตโนมัติ • นิ้วซ้ายเลี้ยว • นิ้วขวาดริฟต์และใช้สกิล'
    : 'W/↑ เร่ง • A D เลี้ยว • Space ดริฟต์ • E สกิล • Esc พักเกม (แตะจอได้เช่นกัน)';
}

const STAT_LABEL = { speed: 'ความเร็ว', accel: 'อัตราเร่ง', turn: 'ความคล่อง', stability: 'ความมั่นคง' };
function selectRacer(id, silent) {
  app.selected = id;
  store.set('racer', id);
  const d = RACER_BY_ID[id];
  $('selNo').textContent = `ผู้เข้าแข่งขัน ${d.no}`;
  $('selName').textContent = d.name;
  $('selTh').textContent = d.nameTh;
  $('selRide').textContent = `${d.ride} — ${d.rideTh}`;
  $('selIcon').textContent = SKILL_ICON[d.skill];
  $('selSkillName').textContent = `${d.skillName} — ${d.skillNameTh}`;
  $('selSkillDesc').textContent = d.skillDesc;
  const st = $('selStats');
  st.textContent = '';
  for (const k of Object.keys(STAT_LABEL)) {
    const lab = document.createElement('span');
    lab.textContent = STAT_LABEL[k];
    const bar = document.createElement('div');
    bar.className = 'bar';
    const fill = document.createElement('i');
    // stats differ only slightly; stretch the display range so the character still reads
    const lo = k === 'speed' ? 0.96 : 0.82;
    const hi = k === 'speed' ? 1.03 : 1.18;
    fill.style.width = Math.round(Math.max(0.12, Math.min(1, (d.stats[k] - lo) / (hi - lo))) * 100) + '%';
    bar.appendChild(fill);
    st.append(lab, bar);
  }
  for (const b of $('roster').children) b.classList.toggle('on', b.dataset.id === id);
  view.setShowcase(id);
  if (!silent) audio.select();
}

function goSelect() {
  app.state = 'select';
  app.paused = false;
  app.race = null;
  app.loop = null;
  input.enabled = false;
  audio.stopEngine();
  audio.setMusicLevel(0.3);
  show('select');
  selectRacer(app.selected, true);
  resize();
}

function startRace() {
  app.state = 'race';
  app.paused = false;
  app.resultsShown = false;
  app.resultsTimer = 0;
  app.finalLapAnnounced = false;
  app.race = new Race(track, { playerId: app.selected, seed: app.seed++, autopilot: AUTOPILOT, laps: LAPS });
  app.loop = new FixedLoop(app.race);
  view.setRace(app.race, 'chase');
  hud.start(app.race);
  input.reset();
  input.enabled = true;
  audio.unlock();
  audio.startEngine(app.selected);
  audio.startMusic();
  audio.setMusicLevel(0.3);
  show('hud');
  $('btnAuto').textContent = 'เร่งอัตโนมัติ: ' + (input.autoGas ? 'เปิด' : 'ปิด');
  resize();
}

function setPaused(p) {
  if (app.state !== 'race' || app.resultsShown) return;
  app.paused = p;
  input.enabled = !p;
  input.reset();
  if (p) {
    show('pause');
    audio.setMusicLevel(0.08);
    audio.updateEngine({ vf: 0, respawning: true, drift: 0, slickAmount: 0, boostTimer: 0 }, 0, 1);
  } else {
    show('hud');
    audio.resume();
    audio.setMusicLevel(0.3);
  }
}

function showResults() {
  app.resultsShown = true;
  input.enabled = false;
  view.mode = 'orbit';
  audio.stopEngine();
  const place = app.race.player.place;
  $('resTitle').textContent = place === 1 ? '🏆 ชนะเลิศ!' : `เข้าเส้นชัยอันดับ ${place}`;
  renderResults();
  show('results');
}

function renderResults() {
  const list = $('resList');
  const rows = app.race.results();
  const sig = rows.map((r) => r.id + (r.finished ? r.time.toFixed(2) : 'x' + r.place)).join('|') + app.race.done;
  if (sig === app.resSig) return;
  app.resSig = sig;
  list.textContent = '';
  for (const r of rows) {
    const li = document.createElement('li');
    if (r.isPlayer) li.className = 'me';
    const p = document.createElement('span');
    p.className = 'p';
    p.textContent = r.finished ? String(r.place) : '–';
    const n = document.createElement('span');
    n.textContent = r.name + (r.isPlayer ? ' (คุณ)' : '');
    const sm = document.createElement('small');
    sm.textContent = r.nameTh + (r.bestLap ? ` • รอบเร็วสุด ${fmtTime(r.bestLap)}` : '');
    n.appendChild(sm);
    const t = document.createElement('span');
    t.className = 't';
    // only real recorded times; unfinished racers are shown as still racing / not finished
    t.textContent = r.finished ? fmtTime(r.time) : app.race.done ? 'ไม่จบการแข่งขัน' : `กำลังแข่ง รอบ ${r.lap}`;
    li.append(p, n, t);
    list.appendChild(li);
  }
}

// ── buttons ─────────────────────────────────────────────────────────────────
function tap(id, fn) {
  $(id).addEventListener('click', (e) => {
    e.preventDefault();
    audio.unlock();
    audio.click();
    fn();
  });
}
function syncMute() {
  const label = audio.muted ? '🔇 เสียง: ปิด' : '🔊 เสียง: เปิด';
  $('btnMute').textContent = label;
  $('btnMuteTitle').textContent = label;
  $('volume').value = String(Math.round(audio.volume * 100));
}
tap('btnStart', () => {
  audio.startMusic();
  goSelect();
});
tap('btnBack', goTitle);
tap('btnRace', startRace);
tap('btnResume', () => setPaused(false));
tap('btnRestart', startRace);
tap('btnQuit', goSelect);
tap('btnAgain', startRace);
tap('btnPick', goSelect);
tap('btnMute', () => {
  audio.setMuted(!audio.muted);
  syncMute();
});
tap('btnMuteTitle', () => {
  audio.setMuted(!audio.muted);
  syncMute();
});
tap('btnQuality', () => {
  const order = ['auto', 'low', 'mid', 'high'];
  app.quality = order[(order.indexOf(app.quality) + 1) % order.length];
  store.set('quality', app.quality);
  applyQuality();
});
tap('btnAuto', () => {
  input.autoGas = !input.autoGas;
  $('btnAuto').textContent = 'เร่งอัตโนมัติ: ' + (input.autoGas ? 'เปิด' : 'ปิด');
});
tap('btnRotateOk', () => {
  app.rotateDismissed = true;
  resize();
});
$('volume').addEventListener('input', (e) => {
  audio.unlock();
  audio.setVolume(Number(e.target.value) / 100);
  if (audio.muted && audio.volume > 0) audio.setMuted(false);
  syncMute();
});

// leaving the tab / switching apps: freeze the race exactly where it is
function onHide() {
  if (app.state === 'race' && !app.paused && !app.resultsShown && app.race.phase !== 'countdown') setPaused(true);
  audio.suspend();
}
document.addEventListener('visibilitychange', () => {
  if (document.hidden) onHide();
  else {
    last = performance.now();
    audio.resume();
  }
});
window.addEventListener('pagehide', onHide);

// ── frame loop ──────────────────────────────────────────────────────────────
let last = performance.now();
let autoTimer = 0;
function frame(now) {
  requestAnimationFrame(frame);
  const rawDt = Math.min(0.1, Math.max(0, (now - last) / 1000));
  last = now;
  const race = app.race;

  if (app.state === 'race') {
    if (input.takePause()) setPaused(!app.paused);
    if (!app.paused) {
      if (!race.player.finished && !AUTOPILOT) input.apply(race.player.input);
      else if (AUTOPILOT && input.skillQueued) {
        race.player.input.skill = true;
        input.skillQueued = false;
      }
      app.loop.advance(rawDt);
      handleEvents(race);
      const count = hud.update(race, rawDt);
      if (count) audio.countBeep(false);
      audio.updateEngine(race.player, rawDt, BALANCE.vehicle.maxSpeed);
      if (race.phase === 'finished' && !app.resultsShown) {
        app.resultsTimer += rawDt;
        if (app.resultsTimer > 1.6) showResults();
      }
      if (app.resultsShown) renderResults();
      view.update(rawDt, app.loop.alpha);
    }
    // paused: simulation, skills, AI, effects and the clock all stand still
  } else if (app.state === 'title') {
    app.loop.advance(rawDt);
    race.events.length = 0;
    if (race.done || race.time > 240) startAttract();
    view.update(rawDt, app.loop.alpha);
  } else if (app.state === 'select') {
    view.update(rawDt, 1);
  }
  view.render();

  // measured frame rate → optional resolution scaling (never claims 60: it measures)
  app.frameMs.push(rawDt * 1000);
  if (app.frameMs.length > 60) app.frameMs.shift();
  autoTimer += rawDt;
  if (autoTimer > 2) {
    autoTimer = 0;
    const avg = app.frameMs.reduce((a, b) => a + b, 0) / app.frameMs.length;
    app.fps = 1000 / avg;
    if (app.quality === 'auto' && app.state === 'race' && !app.paused) {
      const cap = Math.min(window.devicePixelRatio || 1, QUALITY.auto.maxPR);
      if (avg > 23 && app.pr > 0.75) {
        app.pr = Math.max(0.75, app.pr - 0.25);
        view.effects.rate = Math.max(0.5, view.effects.rate - 0.15);
        resize();
      } else if (avg < 13 && app.pr < cap) {
        app.pr = Math.min(cap, app.pr + 0.25);
        resize();
      }
    }
    if (fpsEl) fpsEl.textContent = `${app.fps.toFixed(0)} fps • pr ${app.pr.toFixed(2)} • ${renderer.info.render.calls} calls • ${(renderer.info.render.triangles / 1000).toFixed(0)}k tris`;
  }
}

function handleEvents(race) {
  const ev = race.events;
  if (!ev.length) return;
  const p = race.player;
  view.handleEvents(ev);
  for (const e of ev) {
    const r = e.racer;
    const mine = r === p;
    let vol = 1;
    if (r && !mine) {
      const d = Math.hypot(r.x - p.x, r.z - p.z);
      vol = d > 110 ? 0 : 1 / (1 + d / 22);
    }
    switch (e.type) {
      case 'go':
        hud.banner('GO!', false, 0.9);
        audio.countBeep(true);
        break;
      case 'lap':
        if (mine) {
          const next = e.lap + 1;
          if (next === race.laps) hud.banner('รอบสุดท้าย!', true, 1.6);
          else if (next < race.laps) hud.banner(`รอบ ${next}/${race.laps}`, true, 1.3);
          audio.lap(next === race.laps);
        }
        break;
      case 'finish':
        if (mine) {
          hud.banner(e.place === 1 ? 'ชนะ!' : `อันดับ ${e.place}`, false, 2);
          audio.finish(e.place === 1);
        }
        break;
      case 'skillDenied':
        if (mine) {
          hud.toast(`ใช้สกิลไม่ได้: ${e.why}`);
          audio.denied();
        }
        break;
      case 'fall':
        if (mine) hud.toast(e.why === 'stuck' ? 'ติดค้าง — กลับสู่สนาม' : 'ตกสนาม!');
        audio.event(e, vol, mine);
        break;
      default:
        audio.event(e, vol, mine);
    }
  }
  if (p.boostTimer > 0 && !app.boosting) audio.boost();
  app.boosting = p.boostTimer > 0;
  ev.length = 0;
}

// ── go ──────────────────────────────────────────────────────────────────────
let fpsEl = null;
if (PARAMS.has('fps')) {
  fpsEl = document.createElement('div');
  fpsEl.style.cssText = 'position:fixed;left:50%;top:4px;transform:translateX(-50%);font:12px monospace;background:#000a;color:#fff;padding:2px 8px;border-radius:6px;z-index:9;pointer-events:none';
  document.body.appendChild(fpsEl);
}

function boot() {
  applyQuality();
  // roster buttons with real renders of each racer
  const roster = $('roster');
  for (const d of RACERS) {
    const b = document.createElement('button');
    b.dataset.id = d.id;
    b.className = 'tap';
    b.setAttribute('aria-label', d.name);
    try {
      b.style.backgroundImage = `url(${view.thumbnail(d.id, 160)})`;
    } catch {
      b.style.backgroundColor = d.color;
    }
    const n = document.createElement('span');
    n.textContent = d.no;
    b.appendChild(n);
    b.addEventListener('click', () => {
      audio.unlock();
      selectRacer(d.id);
    });
    roster.appendChild(b);
  }
  syncMute();
  goTitle();
  requestAnimationFrame(frame);
}
boot();

// small debug/test handle (used by tools/browser-smoke.mjs)
window.__riftriot = { app, view, audio, input, track, renderer, startRace, goSelect, goTitle, setPaused, selectRacer };
