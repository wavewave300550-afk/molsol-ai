// In-race HUD. DOM writes are cached so nothing is touched unless a value changed.
import { BALANCE } from '../data/balance.js';
import { SKILLS } from '../sim/skills.js';

export const SKILL_ICON = { railMaker: '🛤️', tantrum: '😭', pirouette: '🩰', slingshot: '🤸', eternalLove: '💗', hurricane: '🌀' };

export function fmtTime(t) {
  if (t == null) return '—';
  const m = Math.floor(t / 60);
  const s = t - m * 60;
  return `${m}:${s < 10 ? '0' : ''}${s.toFixed(2)}`;
}

export class Hud {
  constructor(root, track) {
    const q = (id) => root.querySelector(id);
    this.el = {
      pos: q('#hudPos'),
      lap: q('#hudLap'),
      laps: q('#hudLaps'),
      time: q('#hudTime'),
      speed: q('#hudSpeed'),
      charge: q('#hudCharge'),
      chargeBox: q('.charge'),
      banner: q('#banner'),
      warn: q('#warn'),
      toast: q('#toast'),
      skill: q('#btnSkill'),
      ring: q('#skillRing'),
      icon: q('#skillIcon'),
      num: q('#skillNum'),
      map: q('#minimap'),
    };
    this.cache = {};
    this.track = track;
    this.bannerT = 0;
    this.toastT = 0;
    this.frame = 0;
    this._buildMap();
  }

  _set(key, el, value, prop = 'textContent') {
    if (this.cache[key] !== value) {
      this.cache[key] = value;
      el[prop] = value;
    }
  }

  _buildMap() {
    const S = this.track.samples;
    let minX = Infinity;
    let maxX = -Infinity;
    let minZ = Infinity;
    let maxZ = -Infinity;
    for (const s of S) {
      minX = Math.min(minX, s.x);
      maxX = Math.max(maxX, s.x);
      minZ = Math.min(minZ, s.z);
      maxZ = Math.max(maxZ, s.z);
    }
    const size = this.el.map.width;
    const pad = 12;
    const k = (size - pad * 2) / Math.max(maxX - minX, maxZ - minZ);
    // screen-right must match the driver's right: flip X (see track.js right vector)
    this.mapX = (x) => size - (pad + (x - minX) * k + (size - pad * 2 - (maxX - minX) * k) / 2);
    this.mapY = (z) => size - (pad + (z - minZ) * k + (size - pad * 2 - (maxZ - minZ) * k) / 2);
    const bg = document.createElement('canvas');
    bg.width = bg.height = size;
    const g = bg.getContext('2d');
    g.lineJoin = g.lineCap = 'round';
    const path = () => {
      g.beginPath();
      S.forEach((s, i) => (i ? g.lineTo(this.mapX(s.x), this.mapY(s.z)) : g.moveTo(this.mapX(s.x), this.mapY(s.z))));
      g.closePath();
    };
    const br = this.track.branch;
    const branch = () => {
      g.beginPath();
      g.moveTo(this.mapX(br.ax), this.mapY(br.az));
      g.lineTo(this.mapX(br.ax + br.tx * br.length), this.mapY(br.az + br.tz * br.length));
    };
    g.strokeStyle = 'rgba(28,26,34,0.85)';
    g.lineWidth = 11;
    path();
    g.stroke();
    if (br) {
      branch();
      g.stroke();
    }
    g.strokeStyle = '#fff7ef';
    g.lineWidth = 5;
    path();
    g.stroke();
    if (br) {
      g.strokeStyle = '#ffb02e';
      g.setLineDash([6, 5]);
      g.lineWidth = 4;
      branch();
      g.stroke();
      g.setLineDash([]);
    }
    g.fillStyle = '#1c1a22';
    g.fillRect(this.mapX(S[0].x) - 7, this.mapY(S[0].z) - 2, 14, 4);
    this.mapBg = bg;
    this.mapCtx = this.el.map.getContext('2d');
  }

  start(race) {
    this.cache = {};
    this.el.laps.textContent = String(race.laps);
    this.el.icon.textContent = SKILL_ICON[race.player.def.skill];
    this.el.banner.classList.add('hidden');
    this.el.warn.classList.add('hidden');
    this.el.toast.classList.add('hidden');
    this.bannerT = this.toastT = 0;
    this.lastCount = 4;
  }

  banner(text, small = false, time = 1.1) {
    const b = this.el.banner;
    b.textContent = text;
    b.classList.toggle('small', small);
    b.classList.remove('hidden');
    // restart the pop animation
    b.style.animation = 'none';
    void b.offsetWidth;
    b.style.animation = '';
    this.bannerT = time;
  }

  toast(text, time = 1.6) {
    this.el.toast.textContent = text;
    this.el.toast.classList.remove('hidden');
    this.toastT = time;
  }

  update(race, dt) {
    const p = race.player;
    const e = this.el;
    this.frame++;
    this._set('pos', e.pos, String(p.finished ? p.place : p.rank));
    this._set('lap', e.lap, String(Math.min(race.laps, Math.max(1, p.lap))));
    const t = p.finished ? p.finishTime : race.time;
    const m = Math.floor(t / 60);
    const s = t - m * 60;
    this._set('time', e.time, `${m}:${s < 10 ? '0' : ''}${s.toFixed(1)}`);
    this._set('speed', e.speed, String(Math.round(Math.abs(p.vf) * 3.6 * 1.6)));
    // drift charge (shared mechanic): fills while a proper drift is held
    const ch = p.drift !== 0 ? Math.min(1, p.driftTime / BALANCE.drift.chargeTime) : 0;
    this._set('charge', e.charge.style, `${Math.round(ch * 100)}%`, 'width');
    const full = p.driftCharged || p.boostTimer > 0;
    if (this.cache.full !== full) {
      this.cache.full = full;
      e.chargeBox.classList.toggle('full', full);
    }

    // skill button: active time and cooldown are shown as two different states
    const sk = p.sk;
    const cfg = SKILLS[p.def.skill].cfg;
    let state = 'ready';
    let frac = 1;
    let num = '';
    if (race.phase === 'countdown') {
      state = 'cool';
      frac = 0;
    } else if (sk.phase !== 'idle' && sk.activeTotal > 0) {
      state = 'active';
      frac = Math.max(0, sk.active / sk.activeTotal);
      if (cfg.duration) num = Math.max(0, sk.active).toFixed(1);
    } else if (sk.cd > 0) {
      state = 'cool';
      frac = 1 - sk.cd / cfg.cooldown;
      num = String(Math.ceil(sk.cd));
    }
    if (this.cache.skState !== state) {
      this.cache.skState = state;
      e.skill.classList.toggle('ready', state === 'ready');
      e.skill.classList.toggle('active', state === 'active');
      e.skill.classList.toggle('cool', state === 'cool');
    }
    this._set('ring', e.ring.style, String(Math.round(289 * (1 - frac))), 'strokeDashoffset');
    this._set('num', e.num, num);

    // warnings
    let warn = '';
    if (p.respawning) warn = 'กลับสนาม…';
    else if (p.wrongWay) warn = '⚠ ย้อนศร! กลับรถ';
    if (this.cache.warn !== warn) {
      this.cache.warn = warn;
      e.warn.textContent = warn;
      e.warn.classList.toggle('hidden', !warn);
    }
    if (this.bannerT > 0) {
      this.bannerT -= dt;
      if (this.bannerT <= 0) e.banner.classList.add('hidden');
    }
    if (this.toastT > 0) {
      this.toastT -= dt;
      if (this.toastT <= 0) e.toast.classList.add('hidden');
    }
    if (race.phase === 'countdown') {
      const n = Math.ceil(race.countdown);
      if (n !== this.lastCount && n >= 1 && n <= 3) {
        this.lastCount = n;
        this.banner(String(n), false, 0.9);
        return n;
      }
    }
    if (this.frame % 2 === 0) this._drawMap(race);
    return 0;
  }

  _drawMap(race) {
    const g = this.mapCtx;
    const size = this.el.map.width;
    g.clearRect(0, 0, size, size);
    g.drawImage(this.mapBg, 0, 0);
    for (const r of race.racers) {
      if (r.isPlayer) continue;
      g.fillStyle = r.def.color;
      g.strokeStyle = '#1c1a22';
      g.lineWidth = 2;
      g.beginPath();
      g.arc(this.mapX(r.x), this.mapY(r.z), 5.5, 0, 7);
      g.fill();
      g.stroke();
    }
    const p = race.player;
    g.fillStyle = '#ffffff';
    g.strokeStyle = '#1c1a22';
    g.lineWidth = 3;
    g.beginPath();
    g.arc(this.mapX(p.x), this.mapY(p.z), 8, 0, 7);
    g.fill();
    g.stroke();
    g.fillStyle = p.def.color;
    g.beginPath();
    g.arc(this.mapX(p.x), this.mapY(p.z), 4.5, 0, 7);
    g.fill();
  }
}
