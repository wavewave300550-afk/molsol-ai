// Pooled visual effects. Nothing here allocates per frame during a race and
// everything is reset between races, so repeated races never accumulate objects.
import * as THREE from 'three';
import { BALANCE } from '../data/balance.js';
import { Part } from './toon.js';

const K = BALANCE.skills;
const V = BALANCE.vehicle;

const PVS = `
attribute float size; attribute float alpha; attribute float shape; attribute vec3 pcolor;
varying float vAlpha; varying float vShape; varying vec3 vColor;
uniform float scale;
void main(){
  vAlpha = alpha; vShape = shape; vColor = pcolor;
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  gl_PointSize = min(220.0, size * 0.062 * scale / max(0.1, -mv.z));
  gl_Position = projectionMatrix * mv;
}`;
const PFS = `
varying float vAlpha; varying float vShape; varying vec3 vColor;
void main(){
  vec2 p = gl_PointCoord - 0.5;
  float a = 0.0;
  if (vShape < 0.5) { a = smoothstep(0.5, 0.22, length(p)); }
  else if (vShape < 1.5) { // heart
    vec2 q = vec2(p.x * 2.5, -p.y * 2.5 + 0.25);
    float h = q.x*q.x + q.y*q.y - 1.0;
    a = step(h*h*h - q.x*q.x*q.y*q.y*q.y, 0.0);
  }
  else if (vShape < 2.5) { // sparkle
    float d = abs(p.x) * abs(p.y) * 60.0 + length(p) * 1.6;
    a = clamp(1.0 - d, 0.0, 1.0);
  }
  else { a = step(max(abs(p.x), abs(p.y)), 0.38); }
  if (a * vAlpha < 0.02) discard;
  gl_FragColor = vec4(vColor, a * vAlpha);
}`;

class Particles {
  constructor(max) {
    this.max = max;
    this.n = 0;
    this.pos = new Float32Array(max * 3);
    this.col = new Float32Array(max * 3);
    this.size = new Float32Array(max);
    this.alpha = new Float32Array(max);
    this.shape = new Float32Array(max);
    this.vel = new Float32Array(max * 3);
    this.life = new Float32Array(max);
    this.maxLife = new Float32Array(max);
    this.grav = new Float32Array(max);
    this.drag = new Float32Array(max);
    this.grow = new Float32Array(max);
    this.baseSize = new Float32Array(max);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(this.pos, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('pcolor', new THREE.BufferAttribute(this.col, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('size', new THREE.BufferAttribute(this.size, 1).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('alpha', new THREE.BufferAttribute(this.alpha, 1).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('shape', new THREE.BufferAttribute(this.shape, 1).setUsage(THREE.DynamicDrawUsage));
    this.mat = new THREE.ShaderMaterial({ vertexShader: PVS, fragmentShader: PFS, transparent: true, depthWrite: false, uniforms: { scale: { value: 600 } } });
    this.points = new THREE.Points(g, this.mat);
    this.points.frustumCulled = false;
    this.points.renderOrder = 20;
    this.geo = g;
  }
  spawn(x, y, z, vx, vy, vz, life, size, r, g, b, shape = 0, grav = 0, drag = 0, grow = 0) {
    let i = this.n;
    if (i >= this.max) {
      i = Math.floor(Math.random() * this.max); // pool is full: recycle, never grow
    } else this.n++;
    this.pos.set([x, y, z], i * 3);
    this.vel.set([vx, vy, vz], i * 3);
    this.col.set([r, g, b], i * 3);
    this.life[i] = this.maxLife[i] = life;
    this.baseSize[i] = size;
    this.shape[i] = shape;
    this.grav[i] = grav;
    this.drag[i] = drag;
    this.grow[i] = grow;
  }
  update(dt) {
    let n = this.n;
    for (let i = 0; i < n; i++) {
      this.life[i] -= dt;
      if (this.life[i] <= 0) {
        // swap-remove
        n--;
        if (i !== n) {
          this.pos.copyWithin(i * 3, n * 3, n * 3 + 3);
          this.vel.copyWithin(i * 3, n * 3, n * 3 + 3);
          this.col.copyWithin(i * 3, n * 3, n * 3 + 3);
          this.life[i] = this.life[n];
          this.maxLife[i] = this.maxLife[n];
          this.baseSize[i] = this.baseSize[n];
          this.shape[i] = this.shape[n];
          this.grav[i] = this.grav[n];
          this.drag[i] = this.drag[n];
          this.grow[i] = this.grow[n];
        }
        i--;
        continue;
      }
      const k = 1 - this.drag[i] * dt;
      this.vel[i * 3] *= k;
      this.vel[i * 3 + 1] = this.vel[i * 3 + 1] * k - this.grav[i] * dt;
      this.vel[i * 3 + 2] *= k;
      this.pos[i * 3] += this.vel[i * 3] * dt;
      this.pos[i * 3 + 1] += this.vel[i * 3 + 1] * dt;
      this.pos[i * 3 + 2] += this.vel[i * 3 + 2] * dt;
      const f = this.life[i] / this.maxLife[i];
      this.alpha[i] = Math.min(1, f * 2.2);
      this.size[i] = this.baseSize[i] * (1 + this.grow[i] * (1 - f));
    }
    this.n = n;
    this.geo.setDrawRange(0, n);
    for (const k of ['position', 'pcolor', 'size', 'alpha', 'shape']) this.geo.attributes[k].needsUpdate = true;
  }
  clear() {
    this.n = 0;
    this.geo.setDrawRange(0, 0);
  }
}

function textTexture(text, color) {
  const c = document.createElement('canvas');
  c.width = 256;
  c.height = 128;
  const g = c.getContext('2d');
  g.font = '900 78px "Arial Black", system-ui, "Thonburi", sans-serif';
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.lineWidth = 14;
  g.lineJoin = 'round';
  g.strokeStyle = '#1c1a22';
  g.strokeText(text, 128, 66);
  g.fillStyle = color;
  g.fillText(text, 128, 66);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

export class Effects {
  constructor(scene, quality = {}) {
    this.scene = scene;
    this.group = new THREE.Group();
    scene.add(this.group);
    this.particles = new Particles(quality.particles ?? 520);
    this.rate = quality.particleRate ?? 1;
    this.group.add(this.particles.points);
    this.t = 0;
    this.acc = new Map(); // per-racer emission accumulators

    // expanding ground rings (tantrum wave, landings, respawn)
    this.rings = [];
    const ringGeo = new THREE.RingGeometry(0.86, 1, 40);
    ringGeo.rotateX(-Math.PI / 2);
    for (let i = 0; i < 8; i++) {
      const m = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ color: '#ffffff', transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide }));
      m.visible = false;
      m.renderOrder = 15;
      this.group.add(m);
      this.rings.push({ m, t: 0, life: 0, r0: 0, r1: 1, follow: null });
    }
    // tantrum shock dome
    this.dome = new THREE.Mesh(
      new THREE.SphereGeometry(1, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2),
      new THREE.MeshBasicMaterial({ color: '#ff5a3c', transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide })
    );
    this.dome.visible = false;
    this.dome.renderOrder = 14;
    this.group.add(this.dome);
    this.domeT = 0;
    this.domeR = 10;

    // slick patches
    const slickC = document.createElement('canvas');
    slickC.width = slickC.height = 128;
    const sg = slickC.getContext('2d');
    const grd = sg.createRadialGradient(64, 64, 6, 64, 64, 62);
    grd.addColorStop(0, 'rgba(255,190,220,0.75)');
    grd.addColorStop(0.75, 'rgba(255,120,175,0.7)');
    grd.addColorStop(0.9, 'rgba(255,255,255,0.95)'); // bright rim = true edge of the effect
    grd.addColorStop(1, 'rgba(255,90,150,0.0)');
    sg.fillStyle = grd;
    sg.fillRect(0, 0, 128, 128);
    sg.fillStyle = 'rgba(255,255,255,0.8)';
    sg.beginPath();
    sg.ellipse(44, 44, 16, 8, -0.6, 0, 7);
    sg.fill();
    const slickTex = new THREE.CanvasTexture(slickC);
    slickTex.colorSpace = THREE.SRGBColorSpace;
    const sgeo = new THREE.PlaneGeometry(2, 2);
    sgeo.rotateX(-Math.PI / 2);
    this.slickMesh = new THREE.InstancedMesh(sgeo, new THREE.MeshBasicMaterial({ map: slickTex, transparent: true, depthWrite: false }), K.eternalLove.maxPatches);
    this.slickMesh.count = 0;
    this.slickMesh.frustumCulled = false;
    this.slickMesh.renderOrder = 3;
    this.group.add(this.slickMesh);

    // rails: sleepers with little trestle legs + two steel rails
    const sl = new Part();
    sl.box(2.7, 0.14, 0.36, '#ffffff', { p: [0, -0.16, 0] });
    sl.box(0.14, 0.55, 0.14, '#ffffff', { p: [1.0, -0.5, 0] });
    sl.box(0.14, 0.55, 0.14, '#ffffff', { p: [-1.0, -0.5, 0] });
    const sleeperGeo = sl.build().geometry;
    sleeperGeo.deleteAttribute('color');
    const railP = new Part();
    railP.box(0.14, 0.16, 1.75, '#ffffff', { p: [1.12, -0.02, 0] });
    railP.box(0.14, 0.16, 1.75, '#ffffff', { p: [-1.12, -0.02, 0] });
    const railGeo = railP.build().geometry;
    railGeo.deleteAttribute('color');
    const maxPieces = Math.ceil((K.railMaker.duration * V.maxSpeed * 1.2) / K.railMaker.pieceSpacing) + 16;
    this.sleepers = new THREE.InstancedMesh(sleeperGeo, new THREE.MeshToonMaterial({ color: '#ffffff' }), maxPieces);
    this.railBars = new THREE.InstancedMesh(railGeo, new THREE.MeshToonMaterial({ color: '#ffffff' }), maxPieces);
    for (const im of [this.sleepers, this.railBars]) {
      im.count = 0;
      im.frustumCulled = false;
      im.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(maxPieces * 3), 3);
      this.group.add(im);
    }
    this.maxPieces = maxPieces;

    // hurricane funnel + its true radius painted on the ground
    const hc = document.createElement('canvas');
    hc.width = 256;
    hc.height = 128;
    const hg = hc.getContext('2d');
    hg.strokeStyle = 'rgba(255,255,255,0.85)';
    hg.lineWidth = 9;
    for (let i = -2; i < 6; i++) {
      hg.beginPath();
      hg.moveTo(i * 64, 128);
      hg.bezierCurveTo(i * 64 + 40, 90, i * 64 + 50, 40, i * 64 + 110, 0);
      hg.stroke();
    }
    const htex = new THREE.CanvasTexture(hc);
    htex.wrapS = THREE.RepeatWrapping;
    htex.colorSpace = THREE.SRGBColorSpace;
    this.funnelTex = htex;
    const R = K.hurricane.radius;
    const funnel = new THREE.Mesh(
      new THREE.CylinderGeometry(R * 0.95, 1.6, 7.5, 24, 1, true),
      new THREE.MeshBasicMaterial({ map: htex, transparent: true, opacity: 0.5, depthWrite: false, side: THREE.DoubleSide, color: '#cfefff' })
    );
    funnel.position.y = 3.75;
    const hring = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ color: '#9fe8ff', transparent: true, opacity: 0.8, depthWrite: false, side: THREE.DoubleSide }));
    hring.scale.setScalar(R);
    hring.position.y = 0.08;
    this.hurricane = new THREE.Group();
    this.hurricane.add(funnel, hring);
    this.hurricane.visible = false;
    this.hurricane.renderOrder = 16;
    this.funnel = funnel;
    this.group.add(this.hurricane);

    // comic text pops
    this.texCache = new Map();
    this.pops = [];
    for (let i = 0; i < 6; i++) {
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ transparent: true, depthWrite: false, depthTest: false }));
      s.visible = false;
      s.renderOrder = 30;
      this.group.add(s);
      this.pops.push({ s, t: 0, life: 0 });
    }
    this._m = new THREE.Matrix4();
    this._q = new THREE.Quaternion();
    this._e = new THREE.Euler();
    this._p = new THREE.Vector3();
    this._s = new THREE.Vector3();
    this._c = new THREE.Color();
  }

  reset() {
    this.particles.clear();
    for (const r of this.rings) {
      r.m.visible = false;
      r.life = 0;
    }
    this.dome.visible = false;
    this.domeT = 0;
    this.slickMesh.count = 0;
    this.sleepers.count = 0;
    this.railBars.count = 0;
    this.hurricane.visible = false;
    for (const p of this.pops) {
      p.s.visible = false;
      p.life = 0;
    }
    this.acc.clear();
  }

  ring(x, y, z, r0, r1, life, color, follow = null) {
    const r = this.rings.find((q) => q.life <= 0) || this.rings[0];
    r.m.material.color.set(color);
    r.m.position.set(x, y + 0.1, z);
    r.t = 0;
    r.life = life;
    r.r0 = r0;
    r.r1 = r1;
    r.follow = follow;
    r.m.visible = true;
  }

  pop(text, color, x, y, z, size = 4) {
    const key = text + color;
    let tex = this.texCache.get(key);
    if (!tex) {
      tex = textTexture(text, color);
      this.texCache.set(key, tex);
    }
    const p = this.pops.find((q) => q.life <= 0) || this.pops[0];
    p.s.material.map = tex;
    p.s.material.needsUpdate = true;
    p.s.position.set(x, y, z);
    p.size = size;
    p.t = 0;
    p.life = 0.95;
    p.s.visible = true;
  }

  burst(x, y, z, n, speed, life, size, color, shape = 0, grav = 0, up = 0.5) {
    this._c.set(color);
    n = Math.max(1, Math.round(n * this.rate));
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2;
      const u = Math.random();
      const sp = speed * (0.4 + Math.random() * 0.6);
      this.particles.spawn(x, y, z, Math.cos(a) * sp * (1 - u * up), sp * u * up * 2, Math.sin(a) * sp * (1 - u * up), life * (0.6 + Math.random() * 0.4), size * (0.7 + Math.random() * 0.6), this._c.r, this._c.g, this._c.b, shape, grav, 1.5, 0.6);
    }
  }

  /** React to simulation events (already filtered to what happened this frame). */
  onEvent(e, isNearPlayer) {
    const r = e.racer;
    switch (e.type) {
      case 'tantrumWave':
        // the ring and dome grow to exactly the push radius
        this.ring(r.x, r.gy, r.z, 0.5, e.radius, 0.38, '#ff5a3c');
        this.ring(r.x, r.gy, r.z, 0.2, e.radius, 0.5, '#ffd23f');
        this.dome.visible = true;
        this.dome.position.set(r.x, r.gy, r.z);
        this.domeT = 0.36;
        this.domeR = e.radius;
        this.pop('แง้!!!', '#ff5a3c', r.x, r.y + 5, r.z, 6);
        this.burst(r.x, r.y + 2.6, r.z, 18, 16, 0.5, 10, '#ffd23f', 2, 0, 0.3);
        break;
      case 'slingLaunch':
        this.ring(r.x, r.gy, r.z, 0.5, 4, 0.4, '#e9e4f5');
        this.burst(r.x, r.gy + 0.3, r.z, 14, 8, 0.6, 12, '#d9cfee', 0, 3, 0.5);
        this.pop('โบอิ้ง!', '#c9a5ff', r.x, r.y + 3.5, r.z, 5);
        break;
      case 'land':
        this.ring(r.x, r.gy, r.z, 0.5, 4.5, 0.4, '#ffffff');
        this.burst(r.x, r.gy + 0.3, r.z, 16, 9, 0.6, 12, '#e9e4f5', 0, 3, 0.4);
        break;
      case 'cupHit':
        this.burst(r.x, r.y + 1.5, r.z, 14, 12, 0.6, 9, '#ffffff', 3, 18, 0.7);
        if (isNearPlayer) this.pop('เพล้ง!', '#ffffff', r.x, r.y + 4, r.z, 4.5);
        break;
      case 'wallHit':
        this.burst(r.x, r.y + 1, r.z, 8, 9, 0.35, 7, '#ffe14f', 2, 10, 0.6);
        break;
      case 'pushed':
        this.burst(r.x, r.y + 1.6, r.z, 8, 10, 0.4, 9, '#ffffff', 2, 0, 0.5);
        if (r.isPlayer) this.pop('ปึ้ก!', '#ffe14f', r.x, r.y + 4.2, r.z, 4);
        break;
      case 'respawn':
        this.ring(r.x, r.gy, r.z, 4, 0.6, 0.5, '#7ef9ff');
        this.burst(r.x, r.y + 1.5, r.z, 16, 7, 0.7, 9, '#7ef9ff', 2, -3, 0.9);
        break;
      case 'railEnd':
        this.burst(r.x, r.y, r.z, 10, 6, 0.4, 7, '#ffe9a3', 2, 6, 0.5);
        break;
      case 'skill':
        if (e.skill === 'pirouette') this.pop('✦', '#ffd6e8', r.x, r.y + 5, r.z, 4);
        if (e.skill === 'eternalLove') this.pop('♥', '#ff5d8f', r.x, r.y + 5.6, r.z, 4);
        if (e.skill === 'hurricane') this.pop('วู้ววว', '#9fe8ff', r.x, r.y + 5.4, r.z, 5);
        if (e.skill === 'railMaker') this.pop('แก๊ง!', '#ffe9a3', r.x, r.y + 4.6, r.z, 4);
        break;
    }
  }

  _emit(r, key, rate, dt, fn) {
    const k = r.idx + key;
    let a = (this.acc.get(k) || 0) + rate * this.rate * dt;
    while (a >= 1) {
      a -= 1;
      fn();
    }
    this.acc.set(k, a);
  }

  /** Continuous, state-driven effects. `views` gives interpolated draw poses. */
  update(dt, race, camera, pixelScale) {
    this.t += dt;
    const t = this.t;
    const P = this.particles;
    P.mat.uniforms.scale.value = pixelScale;

    let hurricaneOn = false;
    let pieces = 0;
    const m = this._m;
    for (const r of race.racers) {
      if (r.respawning) continue;
      const fx = Math.sin(r.heading);
      const fz = Math.cos(r.heading);
      const rx = -fz;
      const rz = fx;
      const speedN = r.speed / V.maxSpeed;
      // drift: smoke, then sparks once the boost is earned
      if (r.drift !== 0 && r.grounded) {
        const charged = r.driftCharged;
        this._emit(r, 'd', charged ? 50 : 26, dt, () => {
          const side = Math.random() < 0.5 ? 1 : -1;
          const px = r.x - fx * 1.4 + rx * side * 1.0;
          const pz = r.z - fz * 1.4 + rz * side * 1.0;
          if (charged) P.spawn(px, r.y + 0.3, pz, -fx * 4 + (Math.random() - 0.5) * 5, 3 + Math.random() * 4, -fz * 4 + (Math.random() - 0.5) * 5, 0.35, 8, 1, 0.75, 0.2, 2, 14, 0, 0);
          else P.spawn(px, r.y + 0.3, pz, (Math.random() - 0.5) * 2, 1.2, (Math.random() - 0.5) * 2, 0.5, 13, 0.95, 0.95, 1, 0, 0, 1, 1.4);
        });
      }
      if (r.boostTimer > 0) {
        this._emit(r, 'b', 60, dt, () => {
          P.spawn(r.x - fx * 2 + rx * (Math.random() - 0.5) * 2, r.y + 0.6 + Math.random(), r.z - fz * 2 + rz * (Math.random() - 0.5) * 2, -fx * 10, 0.5, -fz * 10, 0.3, 11, 1, 0.6 + Math.random() * 0.3, 0.15, 0, 0, 0, 0.5);
        });
      }
      if (r.slickAmount > 0.3 && r.speed > 4) {
        this._emit(r, 's', 22, dt, () => {
          P.spawn(r.x + (Math.random() - 0.5) * 2, r.y + 0.3, r.z + (Math.random() - 0.5) * 2, (Math.random() - 0.5) * 4, 2 + Math.random() * 2, (Math.random() - 0.5) * 4, 0.6, 8, 1, 0.75, 0.88, 0, -1, 1, 0.4);
        });
      }
      const sk = r.sk;
      switch (r.def.skill) {
        case 'railMaker': {
          // laid track behind + a preview of where the rail is going
          const c = K.railMaker;
          const fade = r.onRail ? 1 : r.railFade / c.fadeTime;
          if (r.railPts.length && fade > 0) {
            for (const pt of r.railPts) {
              if (pieces >= this.maxPieces) break;
              this._e.set(0, pt.heading, 0);
              this._q.setFromEuler(this._e);
              m.compose(this._p.set(pt.x, pt.y - 0.42 - (1 - fade) * 1.6, pt.z), this._q, this._s.set(fade, fade, 1));
              this.sleepers.setMatrixAt(pieces, m);
              this.railBars.setMatrixAt(pieces, m);
              this.sleepers.setColorAt(pieces, this._c.set('#a8692f'));
              this.railBars.setColorAt(pieces, this._c.set('#aeb9c4'));
              pieces++;
            }
          }
          if (r.onRail) {
            // preview follows the current steering curve: this is where the rail will be
            let h = r.heading;
            let px = r.x;
            let pz = r.z;
            const steps = Math.floor(c.previewLength / c.pieceSpacing);
            const curve = r.speed > 1 ? (r.yawRate / r.speed) * c.pieceSpacing : 0;
            for (let i = 0; i < steps && pieces < this.maxPieces; i++) {
              h += curve;
              px += Math.sin(h) * c.pieceSpacing;
              pz += Math.cos(h) * c.pieceSpacing;
              const k = 1 - i / steps;
              this._e.set(0, h, 0);
              this._q.setFromEuler(this._e);
              m.compose(this._p.set(px, r.y - 0.42, pz), this._q, this._s.set(0.6 + k * 0.4, 0.6 + k * 0.4, 1));
              this.sleepers.setMatrixAt(pieces, m);
              this.railBars.setMatrixAt(pieces, m);
              this.sleepers.setColorAt(pieces, this._c.set('#ffd98a'));
              this.railBars.setColorAt(pieces, this._c.set('#fff3c4'));
              pieces++;
            }
            this._emit(r, 'r', 40, dt, () => {
              const side = Math.random() < 0.5 ? 1 : -1;
              P.spawn(r.x + rx * side * 1.1 - fx * 1.2, r.y - 0.3, r.z + rz * side * 1.1 - fz * 1.2, -fx * 5 + (Math.random() - 0.5) * 4, 2 + Math.random() * 3, -fz * 5 + (Math.random() - 0.5) * 4, 0.3, 7, 1, 0.85, 0.4, 2, 12, 0, 0);
            });
          }
          break;
        }
        case 'pirouette':
          if (sk.phase === 'active') {
            // two ribbons of stage light spiralling round the ball
            this._emit(r, 'p', 90, dt, () => {
              const a = t * 9 + (Math.random() < 0.5 ? 0 : Math.PI);
              const h = 1.9 + Math.sin(t * 5 + a) * 1.4;
              const pink = Math.random() < 0.5;
              P.spawn(r.x + Math.cos(a) * 2.2, r.y + h, r.z + Math.sin(a) * 2.2, -fx * 3, 0.4, -fz * 3, 0.45, 9, 1, pink ? 0.7 : 0.95, pink ? 0.85 : 1, 2, 0, 0, 0);
            });
          }
          break;
        case 'eternalLove':
          if (sk.phase === 'active') {
            this._emit(r, 'h', 26, dt, () => {
              const side = Math.random() < 0.5 ? 1 : -1;
              P.spawn(r.x - fx * 2.6 + rx * side, r.y + 1.3, r.z - fz * 2.6 + rz * side, (Math.random() - 0.5) * 3 - fx * 2, 2.5 + Math.random() * 2, (Math.random() - 0.5) * 3 - fz * 2, 1.3, 14, 1, 0.45 + Math.random() * 0.25, 0.65 + Math.random() * 0.2, 1, -1.5, 0.6, 0.5);
            });
          }
          break;
        case 'hurricane':
          if (sk.phase === 'active') {
            hurricaneOn = true;
            this.hurricane.position.set(r.x, r.gy, r.z);
            this._emit(r, 'u', 46, dt, () => {
              const a = Math.random() * Math.PI * 2;
              const rad = 2 + Math.random() * (K.hurricane.radius - 2);
              const paper = Math.random() < 0.35;
              P.spawn(r.x + Math.cos(a) * rad, r.y + 0.3 + Math.random() * 5, r.z + Math.sin(a) * rad, -Math.sin(a) * 15 + r.vx, 1.5, Math.cos(a) * 15 + r.vz, 0.5, paper ? 8 : 12, paper ? 1 : 0.8, paper ? 1 : 0.95, 1, paper ? 3 : 0, 0, 0, 0.3);
            });
          }
          break;
        case 'tantrum':
          if (sk.phase === 'windup') {
            this._emit(r, 't', 60, dt, () => {
              const a = Math.random() * Math.PI * 2;
              P.spawn(r.x + Math.cos(a) * 3, r.y + 2.8, r.z + Math.sin(a) * 3, -Math.cos(a) * 12, 0, -Math.sin(a) * 12, 0.2, 8, 1, 0.4, 0.3, 0, 0, 0, 0);
            });
          }
          break;
      }
      // stroller turbo smoke + hovering potty wash (cheap ambience, near camera only)
      if (speedN > 0.3 && camera && (r.x - camera.position.x) ** 2 + (r.z - camera.position.z) ** 2 < 3600) {
        if (r.def.id === 'baby')
          this._emit(r, 'e', 14, dt, () => P.spawn(r.x - fx * 3 + rx * (Math.random() - 0.5) * 2, r.y + 1.3, r.z - fz * 3 + rz * (Math.random() - 0.5) * 2, -fx * 3, 1.5, -fz * 3, 0.5, 12, 0.5, 0.5, 0.55, 0, -1, 1, 1.5));
        if (r.def.id === 'gator')
          this._emit(r, 'e', 12, dt, () => P.spawn(r.x + (Math.random() - 0.5) * 1.6, r.y + 0.4, r.z + (Math.random() - 0.5) * 1.6, (Math.random() - 0.5) * 3, -1, (Math.random() - 0.5) * 3, 0.4, 10, 0.6, 0.95, 1, 0, 0, 1, 1));
      }
    }
    this.sleepers.count = pieces;
    this.railBars.count = pieces;
    if (pieces) {
      this.sleepers.instanceMatrix.needsUpdate = true;
      this.railBars.instanceMatrix.needsUpdate = true;
      this.sleepers.instanceColor.needsUpdate = true;
      this.railBars.instanceColor.needsUpdate = true;
    }

    this.hurricane.visible = hurricaneOn;
    if (hurricaneOn) {
      this.funnel.rotation.y = -t * 7;
      this.funnelTex.offset.y = 0;
    }

    // slick patches straight from the simulation list (visual edge = gameplay edge)
    const sl = race.slicks;
    const n = Math.min(sl.length, K.eternalLove.maxPatches);
    for (let i = 0; i < n; i++) {
      const p = sl[i];
      const age = K.eternalLove.patchLife - p.life;
      const k = Math.min(1, age * 6) * (p.life < 0.3 ? 0.6 + (p.life / 0.3) * 0.4 : 1);
      m.makeScale(p.r * k * 1.08, 1, p.r * k * 1.08);
      m.setPosition(p.x, p.y + 0.05 + (i % 5) * 0.004, p.z);
      this.slickMesh.setMatrixAt(i, m);
    }
    this.slickMesh.count = n;
    if (n) this.slickMesh.instanceMatrix.needsUpdate = true;

    for (const r of this.rings) {
      if (r.life <= 0) continue;
      r.t += dt;
      const f = Math.min(1, r.t / r.life);
      const e = 1 - (1 - f) * (1 - f);
      r.m.scale.setScalar(r.r0 + (r.r1 - r.r0) * e);
      r.m.material.opacity = (1 - f) * 0.9;
      if (f >= 1) {
        r.life = 0;
        r.m.visible = false;
      }
    }
    if (this.domeT > 0) {
      this.domeT -= dt;
      const f = 1 - Math.max(0, this.domeT) / 0.36;
      const e = 1 - (1 - f) * (1 - f);
      this.dome.scale.set(this.domeR * e, this.domeR * 0.45 * e, this.domeR * e);
      this.dome.material.opacity = (1 - f) * 0.33;
      if (this.domeT <= 0) this.dome.visible = false;
    }
    for (const p of this.pops) {
      if (p.life <= 0) continue;
      p.t += dt;
      const f = p.t / p.life;
      const sc = p.size * (0.5 + Math.min(1, f * 5) * 0.6);
      p.s.scale.set(sc, sc * 0.5, 1);
      p.s.position.y += dt * 2.2;
      p.s.material.opacity = f < 0.7 ? 1 : 1 - (f - 0.7) / 0.3;
      if (f >= 1) {
        p.life = 0;
        p.s.visible = false;
      }
    }
    P.update(dt);
  }
}
