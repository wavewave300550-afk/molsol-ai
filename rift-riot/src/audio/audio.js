// All sound is synthesised with WebAudio — no samples, nothing borrowed.
// The context is created/resumed from a user gesture (the start button) as
// mobile browsers require, and suspended when the page is hidden.
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

const ENGINE = {
  // tone = pitched part, noise = rolling part, tick = rhythmic part (per metre travelled)
  boonsong: { wave: 'triangle', f0: 55, f1: 95, tone: 0.1, noise: 0.16, noiseF: 900, tick: 0.16, tickRate: 0.11, tickF: 1800, tickQ: 6 },
  baby: { wave: 'sawtooth', f0: 110, f1: 330, tone: 0.11, noise: 0.03, noiseF: 2500, tick: 0, tickRate: 0, tickF: 0, lp: 1500 },
  celestine: { wave: 'sine', f0: 220, f1: 330, tone: 0.02, noise: 0.11, noiseF: 500, tick: 0.09, tickRate: 0.5, tickF: 3200, tickQ: 12 },
  granny: { wave: 'sine', f0: 80, f1: 110, tone: 0.0, noise: 0.03, noiseF: 700, tick: 0.2, tickRate: 0.75, tickF: 950, tickQ: 3 },
  lovers: { wave: 'sine', f0: 196, f1: 196, tone: 0.045, noise: 0.14, noiseF: 420, tick: 0.05, tickRate: 0.2, tickF: 600, tickQ: 2, chord: [1, 1.26, 1.5] },
  gator: { wave: 'triangle', f0: 68, f1: 104, tone: 0.16, noise: 0.05, noiseF: 300, tick: 0, tickRate: 0, tickF: 0, wobble: 5 },
};

export class GameAudio {
  constructor() {
    this.ctx = null;
    this.volume = 0.8;
    this.muted = false;
    try {
      const v = localStorage.getItem('riftriot.volume');
      const m = localStorage.getItem('riftriot.muted');
      if (v !== null) this.volume = clamp(Number(v), 0, 1);
      if (m !== null) this.muted = m === '1';
    } catch {
      /* storage unavailable: defaults */
    }
    this.engine = null;
    this.driftNode = null;
    this.musicOn = false;
    this.timer = null;
    this.step = 0;
    this.nextTime = 0;
    this.tickAcc = 0;
  }

  /** Must be called from a user gesture. Safe to call repeatedly. */
  unlock() {
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      this.ctx = new AC();
      this.master = this.ctx.createGain();
      this.comp = this.ctx.createDynamicsCompressor();
      this.comp.threshold.value = -14;
      this.comp.ratio.value = 6;
      this.master.connect(this.comp).connect(this.ctx.destination);
      this.sfx = this.ctx.createGain();
      this.sfx.gain.value = 0.9;
      this.sfx.connect(this.master);
      this.music = this.ctx.createGain();
      this.music.gain.value = 0.3;
      this.music.connect(this.master);
      const len = this.ctx.sampleRate;
      this.noiseBuf = this.ctx.createBuffer(1, len, len);
      const d = this.noiseBuf.getChannelData(0);
      for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
      this._applyVolume();
    }
    if (this.ctx.state === 'suspended' && !document.hidden) this.ctx.resume();
  }

  _applyVolume() {
    if (this.master) this.master.gain.value = this.muted ? 0 : this.volume * 0.9;
    try {
      localStorage.setItem('riftriot.volume', String(this.volume));
      localStorage.setItem('riftriot.muted', this.muted ? '1' : '0');
    } catch {
      /* ignore */
    }
  }
  setVolume(v) {
    this.volume = clamp(v, 0, 1);
    this._applyVolume();
  }
  setMuted(m) {
    this.muted = m;
    this._applyVolume();
  }
  suspend() {
    if (this.ctx && this.ctx.state === 'running') this.ctx.suspend();
  }
  resume() {
    if (this.ctx && this.ctx.state === 'suspended' && !document.hidden) this.ctx.resume();
  }

  // ── building blocks ──
  _env(g, t, a, peak, d) {
    g.gain.cancelScheduledValues(t);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(Math.max(0.0002, peak), t + a);
    g.gain.exponentialRampToValueAtTime(0.0001, t + a + d);
  }
  tone(freq, dur, vol = 0.2, type = 'sine', when = 0, slide = 0, dest = null) {
    if (!this.ctx) return;
    const t = this.ctx.currentTime + when;
    const o = this.ctx.createOscillator();
    const g = this.ctx.createGain();
    o.type = type;
    o.frequency.setValueAtTime(freq, t);
    if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(20, freq * slide), t + dur);
    this._env(g, t, 0.008, vol, dur);
    o.connect(g).connect(dest || this.sfx);
    o.start(t);
    o.stop(t + dur + 0.05);
  }
  noise(dur, vol = 0.2, freq = 1000, q = 1, when = 0, slide = 0, type = 'bandpass') {
    if (!this.ctx) return;
    const t = this.ctx.currentTime + when;
    const s = this.ctx.createBufferSource();
    s.buffer = this.noiseBuf;
    s.loop = true;
    const f = this.ctx.createBiquadFilter();
    f.type = type;
    f.frequency.setValueAtTime(freq, t);
    if (slide) f.frequency.exponentialRampToValueAtTime(Math.max(40, freq * slide), t + dur);
    f.Q.value = q;
    const g = this.ctx.createGain();
    this._env(g, t, 0.01, vol, dur);
    s.connect(f).connect(g).connect(this.sfx);
    s.start(t, Math.random());
    s.stop(t + dur + 0.05);
  }

  // ── UI ──
  click() {
    this.tone(660, 0.07, 0.12, 'triangle');
  }
  select() {
    this.tone(520, 0.08, 0.14, 'triangle');
    this.tone(780, 0.1, 0.12, 'triangle', 0.06);
  }
  countBeep(final) {
    if (final) {
      this.tone(880, 0.5, 0.25, 'square');
      this.tone(1320, 0.5, 0.12, 'triangle');
    } else this.tone(440, 0.16, 0.22, 'square');
  }
  lap(final) {
    const notes = final ? [660, 880, 1100, 1320] : [660, 880];
    notes.forEach((f, i) => this.tone(f, 0.16, 0.16, 'triangle', i * 0.09));
  }
  finish(win) {
    const notes = win ? [523, 659, 784, 1047, 784, 1047] : [523, 659, 784, 659];
    notes.forEach((f, i) => this.tone(f, 0.22, 0.2, 'square', i * 0.13));
  }
  denied() {
    this.tone(180, 0.12, 0.14, 'square');
  }

  // ── world events (vol already scaled by distance) ──
  event(e, vol, isPlayer) {
    if (!this.ctx || vol <= 0.02) return;
    switch (e.type) {
      case 'skill':
        this._skill(e.skill, vol);
        break;
      case 'tantrumWave':
        this.noise(0.3, 0.3 * vol, 300, 0.7, 0, 0.3, 'lowpass');
        break;
      case 'slingLaunch': {
        // cartoon spring: rising boing with a wobble
        const t = this.ctx.currentTime;
        const o = this.ctx.createOscillator();
        const lfo = this.ctx.createOscillator();
        const lg = this.ctx.createGain();
        const g = this.ctx.createGain();
        o.type = 'triangle';
        o.frequency.setValueAtTime(140, t);
        o.frequency.exponentialRampToValueAtTime(620, t + 0.45);
        lfo.frequency.value = 26;
        lg.gain.value = 60;
        lfo.connect(lg).connect(o.frequency);
        this._env(g, t, 0.01, 0.28 * vol, 0.6);
        o.connect(g).connect(this.sfx);
        o.start(t);
        lfo.start(t);
        o.stop(t + 0.7);
        lfo.stop(t + 0.7);
        break;
      }
      case 'land':
        this.noise(0.18, 0.3 * vol, 160, 0.8, 0, 0.5, 'lowpass');
        this.tone(90, 0.16, 0.25 * vol, 'sine', 0, 0.5);
        break;
      case 'cupHit':
        this.tone(1900, 0.25, 0.14 * vol, 'sine');
        this.tone(2850, 0.2, 0.1 * vol, 'sine', 0.02);
        this.noise(0.1, 0.16 * vol, 3000, 2);
        break;
      case 'wallHit':
        this.noise(0.14, 0.25 * vol * clamp(e.power / 14, 0.3, 1), 240, 0.8, 0, 0.5, 'lowpass');
        break;
      case 'bump':
        this.tone(130, 0.1, 0.18 * vol, 'triangle', 0, 0.6);
        break;
      case 'pushed':
        if (isPlayer) this.tone(300, 0.2, 0.2, 'sawtooth', 0, 0.4);
        break;
      case 'fall':
        if (isPlayer) this.tone(900, 0.8, 0.16, 'sine', 0, 0.15);
        break;
      case 'respawn':
        if (isPlayer) {
          this.tone(400, 0.12, 0.14, 'triangle');
          this.tone(800, 0.2, 0.14, 'triangle', 0.08);
        }
        break;
      case 'railEnd':
        this.tone(1400, 0.1, 0.08 * vol, 'square', 0, 0.5);
        break;
    }
  }

  _skill(id, vol) {
    switch (id) {
      case 'railMaker':
        // rails clanking into place
        for (let i = 0; i < 6; i++) {
          this.tone(900 + i * 140, 0.12, 0.11 * vol, 'square', i * 0.06, 0.8);
          this.noise(0.05, 0.12 * vol, 3500, 4, i * 0.06);
        }
        break;
      case 'tantrum': {
        // one short "WAAH": voiced saw through a vowel filter, level-capped and low-passed
        const t = this.ctx.currentTime;
        const o = this.ctx.createOscillator();
        const vib = this.ctx.createOscillator();
        const vg = this.ctx.createGain();
        const f = this.ctx.createBiquadFilter();
        const lp = this.ctx.createBiquadFilter();
        const g = this.ctx.createGain();
        o.type = 'sawtooth';
        o.frequency.setValueAtTime(430, t);
        o.frequency.linearRampToValueAtTime(560, t + 0.18);
        o.frequency.linearRampToValueAtTime(390, t + 0.55);
        vib.frequency.value = 9;
        vg.gain.value = 22;
        vib.connect(vg).connect(o.frequency);
        f.type = 'bandpass';
        f.frequency.value = 1050;
        f.Q.value = 2.2;
        lp.type = 'lowpass';
        lp.frequency.value = 2600;
        this._env(g, t, 0.05, 0.3 * vol, 0.5);
        o.connect(f).connect(lp).connect(g).connect(this.sfx);
        o.start(t);
        vib.start(t);
        o.stop(t + 0.62);
        vib.stop(t + 0.62);
        break;
      }
      case 'pirouette':
        [784, 988, 1175, 1568, 1976].forEach((fq, i) => this.tone(fq, 0.3, 0.1 * vol, 'triangle', i * 0.07));
        this.noise(0.6, 0.05 * vol, 6000, 3, 0.1, 1.6);
        break;
      case 'slingshot':
        this.tone(220, 0.22, 0.14 * vol, 'triangle', 0, 0.6); // coil down; the boing comes on launch
        break;
      case 'eternalLove':
        for (let i = 0; i < 7; i++) this.tone(500 + Math.random() * 900, 0.09, 0.09 * vol, 'sine', i * 0.08 + Math.random() * 0.03, 1.5);
        [392, 494, 587].forEach((fq) => this.tone(fq, 1.2, 0.05 * vol, 'sine', 0.05));
        break;
      case 'hurricane':
        this.noise(3.8, 0.24 * vol, 500, 1.2, 0, 1.8);
        this.noise(3.8, 0.1 * vol, 1400, 3, 0.2, 0.6);
        this.tone(190, 0.5, 0.08 * vol, 'sawtooth', 0, 0.55); // door creak
        break;
    }
  }

  // ── continuous player sounds ──
  startEngine(id) {
    this.stopEngine();
    if (!this.ctx) return;
    const cfg = ENGINE[id] || ENGINE.baby;
    const ctx = this.ctx;
    const out = ctx.createGain();
    out.gain.value = 0;
    out.connect(this.sfx);
    const oscs = [];
    const toneG = ctx.createGain();
    toneG.gain.value = cfg.tone;
    let toneOut = toneG;
    if (cfg.lp) {
      const lp = ctx.createBiquadFilter();
      lp.type = 'lowpass';
      lp.frequency.value = cfg.lp;
      toneG.connect(lp);
      toneOut = lp;
    }
    toneOut.connect(out);
    const mult = cfg.chord || [1, 2.01];
    mult.forEach((m, i) => {
      const o = ctx.createOscillator();
      o.type = cfg.wave;
      o.frequency.value = cfg.f0 * m;
      const g = ctx.createGain();
      g.gain.value = i === 0 ? 1 : cfg.chord ? 0.8 : 0.35;
      o.connect(g).connect(toneG);
      o.start();
      oscs.push({ o, m });
    });
    let lfo = null;
    if (cfg.wobble) {
      lfo = ctx.createOscillator();
      lfo.frequency.value = cfg.wobble;
      const lg = ctx.createGain();
      lg.gain.value = 5;
      lfo.connect(lg);
      for (const { o } of oscs) lg.connect(o.frequency);
      lfo.start();
    }
    const ns = ctx.createBufferSource();
    ns.buffer = this.noiseBuf;
    ns.loop = true;
    const nf = ctx.createBiquadFilter();
    nf.type = 'bandpass';
    nf.frequency.value = cfg.noiseF;
    nf.Q.value = 0.8;
    const ng = ctx.createGain();
    ng.gain.value = 0;
    ns.connect(nf).connect(ng).connect(out);
    ns.start();
    // drift scrub shares the engine bus
    const ds = ctx.createBufferSource();
    ds.buffer = this.noiseBuf;
    ds.loop = true;
    const df = ctx.createBiquadFilter();
    df.type = 'bandpass';
    df.frequency.value = 1900;
    df.Q.value = 4;
    const dg = ctx.createGain();
    dg.gain.value = 0;
    ds.connect(df).connect(dg).connect(this.sfx);
    ds.start();
    this.engine = { cfg, out, oscs, lfo, ns, nf, ng, ds, dg, df };
    this.tickAcc = 0;
  }

  stopEngine() {
    const e = this.engine;
    if (!e) return;
    try {
      for (const { o } of e.oscs) o.stop();
      e.lfo?.stop();
      e.ns.stop();
      e.ds.stop();
      e.out.disconnect();
      e.dg.disconnect();
    } catch {
      /* already stopped */
    }
    this.engine = null;
  }

  /** Called every frame while racing. */
  updateEngine(r, dt, maxSpeed) {
    const e = this.engine;
    if (!e || !this.ctx) return;
    const t = this.ctx.currentTime;
    const sp = clamp(Math.abs(r.vf) / maxSpeed, 0, 1.3);
    const cfg = e.cfg;
    const on = r.respawning ? 0 : 1;
    e.out.gain.setTargetAtTime(on * (0.25 + sp * 0.75), t, 0.08);
    const f = cfg.f0 + (cfg.f1 - cfg.f0) * sp + (r.boostTimer > 0 ? 20 : 0);
    for (const { o, m } of e.oscs) o.frequency.setTargetAtTime(f * m, t, 0.06);
    e.ng.gain.setTargetAtTime(cfg.noise * sp, t, 0.08);
    e.nf.frequency.setTargetAtTime(cfg.noiseF * (0.6 + sp), t, 0.1);
    const drifting = r.drift !== 0 && r.grounded && !r.respawning;
    e.dg.gain.setTargetAtTime(drifting ? 0.07 + (r.driftCharged ? 0.04 : 0) : r.slickAmount > 0.5 ? 0.04 : 0, t, 0.05);
    e.df.frequency.setTargetAtTime(r.driftCharged ? 2600 : 1900, t, 0.1);
    // rhythmic layer: lever clacks, tiptoes, scuttling hands and feet
    if (cfg.tick > 0 && !r.respawning && (r.grounded || r.onRail)) {
      this.tickAcc += Math.abs(r.vf) * dt * cfg.tickRate;
      if (this.tickAcc >= 1) {
        this.tickAcc = 0;
        this.noise(0.035, cfg.tick * (0.6 + sp * 0.4), cfg.tickF * (0.9 + Math.random() * 0.2), cfg.tickQ || 2);
      }
    }
  }

  boost() {
    this.noise(0.45, 0.2, 800, 1, 0, 3);
    this.tone(300, 0.3, 0.1, 'sawtooth', 0, 2.2);
  }

  // ── music: a small original loop, sequenced ahead of the clock ──
  startMusic() {
    if (!this.ctx || this.musicOn) return;
    this.musicOn = true;
    this.step = 0;
    this.nextTime = this.ctx.currentTime + 0.1;
    this.timer = setInterval(() => this._schedule(), 60);
  }
  stopMusic() {
    this.musicOn = false;
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
  }
  setMusicLevel(v) {
    if (this.music) this.music.gain.setTargetAtTime(v, this.ctx.currentTime, 0.2);
  }
  _schedule() {
    if (!this.ctx || this.ctx.state !== 'running') return;
    const spb = 60 / 148 / 2; // eighth notes
    const bass = [110, 110, 165, 110, 131, 131, 196, 131, 147, 147, 220, 147, 98, 98, 147, 196];
    const lead = [659, 0, 784, 880, 0, 784, 659, 0, 587, 0, 659, 784, 0, 659, 523, 0, 698, 0, 880, 988, 0, 880, 698, 0, 784, 0, 659, 587, 523, 0, 587, 0];
    while (this.nextTime < this.ctx.currentTime + 0.2) {
      const when = this.nextTime - this.ctx.currentTime;
      const s = this.step;
      const b = bass[Math.floor(s / 2) % bass.length];
      if (s % 2 === 0) this.tone(b, spb * 1.7, 0.2, 'triangle', when, 0, this.music);
      else this.tone(b * 2, spb * 0.7, 0.07, 'square', when, 0, this.music);
      const l = lead[s % lead.length];
      if (l) this.tone(l, spb * 0.9, 0.09, 'square', when, 0, this.music);
      if (s % 4 === 2) this._hat(when);
      this.nextTime += spb;
      this.step++;
    }
  }
  _hat(when) {
    const t = this.ctx.currentTime + when;
    const s = this.ctx.createBufferSource();
    s.buffer = this.noiseBuf;
    const f = this.ctx.createBiquadFilter();
    f.type = 'highpass';
    f.frequency.value = 6000;
    const g = this.ctx.createGain();
    this._env(g, t, 0.003, 0.07, 0.05);
    s.connect(f).connect(g).connect(this.music);
    s.start(t, Math.random() * 0.5);
    s.stop(t + 0.1);
  }
}
