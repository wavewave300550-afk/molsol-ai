// Presentation layer: turns simulation state into posed models, effects and a camera.
// It only READS the race. The gameplay root (position + heading) is never driven
// by a visual: spinning booths, rolling shells and pirouettes all happen below it.
import * as THREE from 'three';
import { BALANCE } from '../data/balance.js';
import { MODEL_BUILDERS } from './models/index.js';
import { RACERS } from '../data/racers.js';
import { TrackView } from './trackView.js';
import { Effects } from './effects.js';
import { angleDiff, clamp, damp, lerp } from '../sim/math.js';

const V = BALANCE.vehicle;
const CAM = BALANCE.camera;

function makeAnimState() {
  return { t: 0, dt: 0, speed: 0, speedN: 0, dist: 0, steer: 0, yawRate: 0, drift: 0, slip: 0, airborne: false, air: 0, vy: 0, skillPhase: 'idle', skillFrac: 0, skillT: 0, boost: 0, slick: 0, pushed: 0, mood: '', lookBack: 0 };
}

export class GameView {
  constructor(renderer, track, quality) {
    this.renderer = renderer;
    this.track = track;
    this.quality = quality;
    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.Fog('#f3b4cc', 340, 1500);
    this.scene.background = new THREE.Color('#5b2a86');
    this.scene.add(new THREE.HemisphereLight('#fff3e2', '#8f74c8', 1.55));
    const sun = new THREE.DirectionalLight('#ffffff', 1.85);
    sun.position.set(0.5, 1, 0.35);
    this.scene.add(sun);
    this.camera = new THREE.PerspectiveCamera(CAM.fov, 1, 0.5, 2200);
    this.trackView = new TrackView(track, quality);
    this.scene.add(this.trackView.group);
    this.effects = new Effects(this.scene, quality);

    // every racer model is built once and reused for the menu and for every race
    this.models = {};
    this.holders = {};
    this.anim = {};
    const shadowGeo = new THREE.CircleGeometry(1, 20);
    shadowGeo.rotateX(-Math.PI / 2);
    this.shadows = {};
    for (const def of RACERS) {
      const model = MODEL_BUILDERS[def.id]();
      const holder = new THREE.Group(); // gameplay root: position + heading only
      const tilt = new THREE.Group(); // lean, pitch, squash — purely cosmetic
      tilt.add(model.root);
      holder.add(tilt);
      holder.visible = false;
      this.scene.add(holder);
      this.models[def.id] = model;
      this.holders[def.id] = { holder, tilt, roll: 0, pitch: 0, squash: 0, yawOff: 0 };
      this.anim[def.id] = makeAnimState();
      const sh = new THREE.Mesh(shadowGeo, new THREE.MeshBasicMaterial({ color: '#1a0f33', transparent: true, opacity: 0.3, depthWrite: false }));
      sh.renderOrder = 2;
      sh.visible = false;
      this.scene.add(sh);
      this.shadows[def.id] = sh;
    }
    // showcase podium (character select) — off to the side of the plaza
    const s0 = track.samples[track.uToIndex(1.2)];
    this.stage = new THREE.Vector3(s0.x + s0.rx * -(s0.hw + 13), s0.y + 0.2, s0.z + s0.rz * -(s0.hw + 13));
    const podium = new THREE.Mesh(new THREE.CylinderGeometry(5.2, 5.8, 0.7, 28), new THREE.MeshToonMaterial({ color: '#6c5ce7' }));
    podium.position.copy(this.stage).add(new THREE.Vector3(0, -0.35, 0));
    const podiumTop = new THREE.Mesh(new THREE.CylinderGeometry(4.9, 4.9, 0.06, 28), new THREE.MeshBasicMaterial({ color: '#ffd23f' }));
    podiumTop.position.copy(this.stage).add(new THREE.Vector3(0, 0.02, 0));
    this.scene.add(podium, podiumTop);

    this.race = null;
    this.target = null;
    this.mode = 'chase';
    this.camYaw = 0;
    this.camY = 0;
    this.camPos = new THREE.Vector3();
    this.camLook = new THREE.Vector3();
    this.shake = 0;
    this.time = 0;
    this.showcaseId = null;
    this.showYaw = 0;
    this.orbit = 0;
    this.tvTimer = 0;
    this.tvSide = 1;
    this.lastRank = {};
    this.moodT = {};
    this._bridge = { solid: true, warn: false };
    this.resize();
  }

  resize() {
    const w = this.renderer.domElement.clientWidth || window.innerWidth;
    const h = this.renderer.domElement.clientHeight || window.innerHeight;
    this.aspect = w / h;
    this.camera.aspect = this.aspect;
    this.viewH = h;
    this._applyFov(CAM.fov);
  }

  _applyFov(base) {
    // keep a sensible horizontal view in portrait (phones held upright)
    let fov = base;
    if (this.aspect < 1.2) {
      const hf = THREE.MathUtils.degToRad(base * 0.92);
      fov = THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(hf / 2) / Math.max(0.45, this.aspect)));
      fov = Math.min(fov, 88);
    }
    this.camera.fov = fov;
    this.camera.updateProjectionMatrix();
  }

  setRace(race, mode = 'chase') {
    this.race = race;
    this.mode = mode;
    this.effects.reset();
    this.showcaseId = null;
    for (const def of RACERS) {
      this.holders[def.id].holder.visible = false;
      this.shadows[def.id].visible = false;
    }
    if (!race) return;
    for (const r of race.racers) {
      const h = this.holders[r.def.id];
      h.holder.visible = true;
      h.holder.scale.setScalar(1);
      h.roll = h.pitch = h.squash = 0;
      const a = this.anim[r.def.id];
      Object.assign(a, makeAnimState(), { t: a.t, dist: a.dist });
      this.lastRank[r.idx] = r.rank;
      this.moodT[r.idx] = 0;
      this.shadows[r.def.id].visible = true;
    }
    this.target = race.player || race.racers[0];
    this.camYaw = this.target.heading;
    this.camY = this.target.y;
    this.snap = true;
  }

  /** Character-select showcase: the chosen racer on the podium, running on the spot. */
  setShowcase(id) {
    this.race = null;
    this.mode = 'showcase';
    this.effects.reset();
    this.showcaseId = id;
    for (const def of RACERS) {
      const h = this.holders[def.id];
      const on = def.id === id;
      h.holder.visible = on;
      this.shadows[def.id].visible = on;
      if (on) {
        h.holder.position.copy(this.stage);
        h.tilt.rotation.set(0, 0, 0);
        h.tilt.scale.set(1, 1, 1);
        this.shadows[def.id].position.copy(this.stage).add(new THREE.Vector3(0, 0.06, 0));
        this.shadows[def.id].scale.setScalar(2.4);
      }
    }
  }

  handleEvents(events) {
    const pl = this.target;
    for (const e of events) {
      const r = e.racer;
      const near = r && pl ? (r.x - pl.x) ** 2 + (r.z - pl.z) ** 2 < 70 * 70 : false;
      if (r && near) this.effects.onEvent(e, true);
      else if (r && (e.type === 'tantrumWave' || e.type === 'skill')) this.effects.onEvent(e, false);
      if (r && r === pl && (e.type === 'wallHit' || e.type === 'cupHit' || e.type === 'pushed' || e.type === 'bump')) this.shake = Math.min(1, this.shake + 0.5);
      if (r && r === pl && e.type === 'respawn') this.snap = true;
    }
  }

  update(dt, alpha = 1) {
    this.time += dt;
    const race = this.race;
    if (race) {
      this.track.bridgeState(race.time, this._bridge);
      this.trackView.update(dt, race.time, this._bridge);
      for (const r of race.racers) this._poseRacer(r, dt, alpha);
      this.effects.update(dt, race, this.camera, this.viewH * 0.9);
    } else {
      this.trackView.update(dt, this.time, this.track.bridgeState(this.time, this._bridge));
      this.effects.update(dt, { racers: [], slicks: [] }, this.camera, this.viewH * 0.9);
    }
    if (this.mode === 'showcase') this._showcase(dt);
    else if (race) this._camera(dt);
    this.trackView.sky.position.copy(this.camera.position);
    this.trackView.stars.position.copy(this.camera.position);
  }

  _poseRacer(r, dt, alpha) {
    const id = r.def.id;
    const H = this.holders[id];
    const model = this.models[id];
    const a = this.anim[id];
    const px = r.px ?? r.x;
    const pz = r.pz ?? r.z;
    const py = r.py ?? r.y;
    const moving = race_phase(this.race) !== 'countdown';
    const k = moving && !r.respawning ? alpha : 1;
    const x = lerp(px, r.x, k);
    const z = lerp(pz, r.z, k);
    const y = lerp(py, r.y, k);
    const heading = r.heading;
    H.holder.position.set(x, y, z);
    H.holder.rotation.y = heading;
    r.drawX = x;
    r.drawY = y;
    r.drawZ = z;

    // cosmetic lean / pitch / squash — smoothed so the model has weight
    const speedN = r.speed / V.maxSpeed;
    const knock = Math.hypot(r.knockX, r.knockZ);
    const rollT = clamp(r.steer * 0.16 * Math.min(1, speedN * 1.4) + r.drift * 0.12, -0.3, 0.3) + (knock > 1.5 ? Math.sin(this.time * 30) * 0.08 : 0);
    H.roll = damp(H.roll, id === 'gator' ? 0 : rollT, 8, dt);
    const pitchT = -Math.atan(r.slope || 0) + (r.airborne && !r.onRail ? clamp(-r.vy * 0.02, -0.25, 0.3) : 0) - (r.boostTimer > 0 ? 0.06 : 0);
    H.pitch = damp(H.pitch, id === 'granny' && r.jumping ? 0 : pitchT, 7, dt);
    H.yawOff = damp(H.yawOff, r.drift * Math.min(0.45, r.slip) * -0.9, 7, dt);
    H.tilt.rotation.set(H.pitch, H.yawOff, H.roll);
    const st = 1 + (r.boostTimer > 0 ? 0.07 : 0);
    H.tilt.scale.set(1 / Math.sqrt(st), 1 / Math.sqrt(st), st);

    // animation inputs
    a.dt = dt;
    a.t += dt;
    a.speed = r.vf;
    a.speedN = clamp(Math.abs(r.vf) / V.maxSpeed, 0, 1.4);
    a.dist += r.vf * dt;
    a.steer = r.steer;
    a.yawRate = r.yawRate;
    a.drift = r.drift;
    a.slip = r.slip;
    a.airborne = r.airborne;
    a.air = r.y - r.gy;
    a.vy = r.vy;
    a.skillPhase = r.sk.phase;
    a.skillFrac = r.sk.activeTotal ? 1 - r.sk.active / r.sk.activeTotal : 0;
    a.boost = r.boostTimer > 0 ? 1 : 0;
    a.slick = r.slickAmount;
    a.pushed = damp(a.pushed, knock > 1.5 ? 1 : 0, 10, dt);
    // overtaken → a moment of fury (animation only)
    if (r.rank > (this.lastRank[r.idx] ?? r.rank)) this.moodT[r.idx] = 1.6;
    this.lastRank[r.idx] = r.rank;
    this.moodT[r.idx] = Math.max(0, (this.moodT[r.idx] || 0) - dt);
    a.mood = this.moodT[r.idx] > 0 ? 'angry' : '';
    // glance back when someone is close behind
    let look = 0;
    for (const o of this.race.racers) {
      if (o === r) continue;
      const d = r.progress - o.progress;
      if (d > 2 && d < 13) look = o.pm.d > r.pm.d ? -1 : 1;
    }
    a.lookBack = damp(a.lookBack, look, 5, dt);
    model.update(a);

    // falling / returning
    const vis = !(r.respawning && r.y < r.refY - 30);
    const blink = r.grace > 0 && !r.respawning ? Math.sin(this.time * 34) > -0.2 : true;
    H.holder.visible = vis && blink;
    const sh = this.shadows[id];
    const gy = r.gy;
    const lift = Math.max(0, y - gy);
    sh.visible = vis && lift < 12 && !(r.airborne && !r.onRail && !r.jumping && lift < 0.01 && r.vy < -1);
    if (sh.visible) {
      sh.position.set(x, gy + 0.06, z);
      const s = (id === 'celestine' ? 1.7 : 1.9) * (1 + lift * 0.08);
      sh.scale.set(s, 1, id === 'lovers' || id === 'boonsong' ? s * 1.25 : s);
      sh.rotation.y = heading;
      sh.material.opacity = 0.32 / (1 + lift * 0.25);
    }
  }

  _camera(dt) {
    const r = this.target;
    if (!r) return;
    const cam = this.camera;
    const model = this.models[r.def.id];
    const portrait = this.aspect < 1;
    const x = r.drawX ?? r.x;
    const z = r.drawZ ?? r.z;
    if (this.mode === 'chase') {
      const dist = (CAM.distance + (model.cam?.d || 0)) * (portrait ? 1.12 : 1);
      const height = CAM.height + (model.cam?.h || 0) + (portrait ? 0.8 : 0);
      if (r.respawning) {
        // do not dive into the rift with a falling racer: hold position and watch
        this.camLook.lerp(new THREE.Vector3(x, r.drawY ?? r.y, z), Math.min(1, dt * 6));
        cam.lookAt(this.camLook);
        return;
      }
      // follow the stable gameplay heading (never a spinning model)
      const yawT = r.heading + r.drift * Math.min(0.35, r.slip) * 0.5;
      if (this.snap) {
        this.camYaw = yawT;
        this.camY = r.gy;
      }
      this.camYaw += angleDiff(yawT, this.camYaw) * (1 - Math.exp(-CAM.yawFollow * dt));
      const yT = r.gy + Math.max(0, r.y - r.gy) * 0.45;
      this.camY = damp(this.camY, yT, 6, dt);
      const sx = Math.sin(this.camYaw);
      const cz = Math.cos(this.camYaw);
      const want = new THREE.Vector3(x - sx * dist, this.camY + height, z - cz * dist);
      if (this.snap) this.camPos.copy(want);
      else this.camPos.lerp(want, 1 - Math.exp(-CAM.posFollow * dt));
      this.camLook.set(x + sx * CAM.lookAhead, this.camY + 1.5 + (model.cam?.h || 0) * 0.4, z + cz * CAM.lookAhead);
      this.snap = false;
      cam.position.copy(this.camPos);
      if (this.shake > 0.01) {
        cam.position.x += (Math.random() - 0.5) * this.shake * 0.5;
        cam.position.y += (Math.random() - 0.5) * this.shake * 0.4;
        this.shake *= Math.exp(-6 * dt);
      }
      cam.lookAt(this.camLook);
      const over = clamp((r.speed - V.maxSpeed * 0.9) / (V.maxSpeed * 0.3), 0, 1);
      const boost = r.boostTimer > 0 ? 1 : 0;
      this.fovK = damp(this.fovK || 0, Math.max(over * 0.7, boost), 5, dt);
      this._applyFov(CAM.fov + CAM.boostFov * this.fovK);
    } else if (this.mode === 'orbit') {
      // results screen: slow orbit around the player
      this.orbit += dt * 0.35;
      const d = 13;
      cam.position.set(x + Math.sin(this.orbit) * d, (r.drawY ?? r.y) + 5, z + Math.cos(this.orbit) * d);
      cam.lookAt(x, (r.drawY ?? r.y) + 1.8, z);
      this._applyFov(52);
    } else if (this.mode === 'tv') {
      // attract mode: a roaming trackside camera on the leader
      this.tvTimer -= dt;
      const lead = this.race.ranking[0];
      if (this.tvTimer <= 0 || this.tvTarget !== lead) {
        this.tvTimer = 7;
        this.tvTarget = lead;
        this.tvSide = -this.tvSide;
        const s = this.track.sampleAt(lead.pm.s + 55);
        this.camPos.set(s.x + s.rx * (s.hw + 6) * this.tvSide, s.y + 7, s.z + s.rz * (s.hw + 6) * this.tvSide);
      }
      cam.position.copy(this.camPos);
      this.camLook.lerp(new THREE.Vector3(lead.drawX ?? lead.x, (lead.drawY ?? lead.y) + 1.5, lead.drawZ ?? lead.z), Math.min(1, dt * 5));
      cam.lookAt(this.camLook);
      this._applyFov(48);
    }
  }

  _showcase(dt) {
    const id = this.showcaseId;
    if (!id) return;
    const H = this.holders[id];
    const model = this.models[id];
    const a = this.anim[id];
    this.showYaw += dt * 0.5;
    H.holder.position.copy(this.stage);
    H.holder.rotation.y = this.showYaw;
    a.dt = dt;
    a.t += dt;
    a.speedN = 0.55;
    a.speed = V.maxSpeed * 0.55;
    a.dist += a.speed * dt;
    a.steer = Math.sin(a.t * 0.8) * 0.5;
    a.yawRate = a.steer * 0.6;
    a.drift = 0;
    a.slip = 0;
    a.airborne = false;
    a.air = 0;
    a.skillPhase = 'idle';
    a.boost = 0;
    a.mood = '';
    a.lookBack = 0;
    a.pushed = 0;
    model.update(a);
    const portrait = this.aspect < 1;
    const cam = this.camera;
    if (portrait) {
      // phone held upright: model fills the upper part of the screen, info card below
      const vfov = 46;
      cam.fov = vfov;
      cam.updateProjectionMatrix();
      const width = Math.max(model.height * 1.7, 6.8);
      const d = width / (2 * Math.tan(THREE.MathUtils.degToRad(vfov / 2)) * this.aspect) + 1.5;
      const viewH = 2 * d * Math.tan(THREE.MathUtils.degToRad(vfov / 2));
      const lookY = model.height * 0.5 - viewH * 0.17;
      cam.position.set(this.stage.x, this.stage.y + lookY + 1.6, this.stage.z + d);
      cam.lookAt(this.stage.x, this.stage.y + lookY, this.stage.z);
      return;
    }
    const d = 12.5 + (model.height - 3) * 1.2;
    // in landscape the model sits left of centre so the info panel has room
    const side = 3.4;
    const lookY = model.height * 0.45;
    cam.position.set(this.stage.x + side, this.stage.y + 3.6, this.stage.z + d);
    cam.lookAt(this.stage.x + side, this.stage.y + lookY, this.stage.z);
    this._applyFov(40);
  }

  /** Render one racer to a data URL (used once at boot for the roster thumbnails). */
  thumbnail(id, size = 160) {
    const r = this.renderer;
    const prev = { id: this.showcaseId, mode: this.mode, race: this.race };
    this.setShowcase(id);
    const H = this.holders[id];
    const model = this.models[id];
    const a = this.anim[id];
    a.dt = 1 / 30;
    a.speedN = 0.5;
    for (let i = 0; i < 20; i++) {
      a.t += a.dt;
      a.dist += 17 * a.dt;
      model.update(a);
    }
    H.holder.position.copy(this.stage);
    H.holder.rotation.y = 0.75;
    const cam = new THREE.PerspectiveCamera(32, 1, 0.5, 200);
    const d = 9.5 + model.height * 1.5;
    cam.position.set(this.stage.x + 2, this.stage.y + model.height * 0.75, this.stage.z + d);
    cam.lookAt(this.stage.x, this.stage.y + model.height * 0.46, this.stage.z);
    const rt = new THREE.WebGLRenderTarget(size, size, { samples: 4 });
    const bg = this.scene.background;
    const fog = this.scene.fog;
    this.scene.background = null;
    this.scene.fog = null;
    this.trackView.group.visible = false;
    const oldClear = r.getClearAlpha();
    r.setClearAlpha(0);
    r.setRenderTarget(rt);
    r.clear();
    r.render(this.scene, cam);
    const buf = new Uint8Array(size * size * 4);
    r.readRenderTargetPixels(rt, 0, 0, size, size, buf);
    r.setRenderTarget(null);
    r.setClearAlpha(oldClear);
    rt.dispose();
    this.trackView.group.visible = true;
    this.scene.background = bg;
    this.scene.fog = fog;
    const c = document.createElement('canvas');
    c.width = c.height = size;
    const g = c.getContext('2d');
    const img = g.createImageData(size, size);
    // render targets are linear: flip rows and encode to sRGB for the <img>
    const lut = new Uint8ClampedArray(256);
    for (let i = 0; i < 256; i++) lut[i] = Math.round(Math.pow(i / 255, 1 / 2.2) * 255);
    for (let y = 0; y < size; y++) {
      const src = (size - 1 - y) * size * 4;
      const dst = y * size * 4;
      for (let x = 0; x < size * 4; x += 4) {
        img.data[dst + x] = lut[buf[src + x]];
        img.data[dst + x + 1] = lut[buf[src + x + 1]];
        img.data[dst + x + 2] = lut[buf[src + x + 2]];
        img.data[dst + x + 3] = buf[src + x + 3];
      }
    }
    g.putImageData(img, 0, 0);
    this.showcaseId = prev.id;
    this.mode = prev.mode;
    this.race = prev.race;
    H.holder.visible = false;
    this.shadows[id].visible = false;
    return c.toDataURL('image/png');
  }

  render() {
    this.renderer.render(this.scene, this.camera);
  }
}

function race_phase(race) {
  return race ? race.phase : 'none';
}
