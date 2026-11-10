// Builds everything you can see of RIFT JUNCTION from the track data:
// road, barriers, islands, the shortcut span, sliding teacups and scenery.
// Static geometry is merged into a handful of draw calls for mobile GPUs.
import * as THREE from 'three';
import { Part, toon, toonDouble, glow, getGradientMap } from './toon.js';
import { BALANCE } from '../data/balance.js';

const SEC = {
  plaza: { road: '#b3a6dc', wallA: '#ff5d6c', wallB: '#fff7ef', ground: '#8fd39a', cliff: '#7a5fa8', edge: '#ffd23f' },
  tea: { road: '#ffd0e0', wallA: '#ff9ec4', wallB: '#b8f1e0', ground: '#fff2c9', cliff: '#d98fb5', edge: '#ff7fb0' },
  bridge: { road: '#6c62c9', wallA: '#7ef9ff', wallB: '#b79bff', ground: '#3a2f6b', cliff: '#2a2250', edge: '#7ef9ff' },
  neon: { road: '#3f478f', wallA: '#ff4fd8', wallB: '#34e7ff', ground: '#232a5c', cliff: '#151a3d', edge: '#ff4fd8' },
};

function canvasTex(w, h, draw, opts = {}) {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  const g = c.getContext('2d');
  draw(g, w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  if (opts.repeat) {
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
  }
  t.anisotropy = 4;
  return t;
}

function roadTexture() {
  return canvasTex(
    256,
    256,
    (g, w, h) => {
      g.fillStyle = '#d8d8d8';
      g.fillRect(0, 0, w, h);
      // soft speckle so the surface shows speed
      for (let i = 0; i < 500; i++) {
        g.fillStyle = `rgba(${Math.random() < 0.5 ? '255,255,255' : '120,120,120'},0.16)`;
        g.fillRect(Math.random() * w, Math.random() * h, 3 + Math.random() * 5, 2 + Math.random() * 3);
      }
      g.fillStyle = '#ffffff';
      g.fillRect(8, 0, 9, h);
      g.fillRect(w - 17, 0, 9, h);
      g.fillRect(w / 2 - 4, 0, 8, h * 0.45);
      g.fillStyle = 'rgba(255,255,255,0.55)';
      g.fillRect(w * 0.25 - 2, h * 0.5, 4, h * 0.3);
      g.fillRect(w * 0.75 - 2, h * 0.5, 4, h * 0.3);
    },
    { repeat: true }
  );
}

function bannerTexture(text, sub, bg, fg) {
  return canvasTex(512, 128, (g, w, h) => {
    g.fillStyle = bg;
    g.fillRect(0, 0, w, h);
    const s = 16;
    for (let x = 0; x < w; x += s) {
      for (let y = 0; y < 2; y++) {
        g.fillStyle = (x / s + y) % 2 ? '#ffffff' : '#1c1a22';
        g.fillRect(x, y * s, s, s);
        g.fillRect(x, h - (y + 1) * s, s, s);
      }
    }
    g.fillStyle = fg;
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    g.font = '900 54px "Arial Black", Impact, system-ui, sans-serif';
    g.fillText(text, w / 2, sub ? h / 2 - 8 : h / 2);
    if (sub) {
      g.font = '700 22px system-ui, "Thonburi", sans-serif';
      g.fillText(sub, w / 2, h / 2 + 30);
    }
  });
}

function signTexture(lines, bg, fg) {
  return canvasTex(256, 256, (g, w, h) => {
    g.fillStyle = bg;
    g.beginPath();
    g.roundRect(6, 6, w - 12, h - 12, 26);
    g.fill();
    g.lineWidth = 10;
    g.strokeStyle = fg;
    g.stroke();
    g.fillStyle = fg;
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    lines.forEach((l, i) => {
      g.font = `900 ${l.size}px "Arial Black", system-ui, "Thonburi", sans-serif`;
      g.fillText(l.text, w / 2, l.y ?? (h * (i + 1)) / (lines.length + 1));
    });
  });
}

/** Ribbon helper: quads between consecutive cross-sections [ax,ay,az,bx,by,bz]. */
function ribbon(rows, colors, closed, uvFn) {
  const n = rows.length;
  const pos = new Float32Array(n * 6);
  const col = new Float32Array(n * 6);
  const uv = uvFn ? new Float32Array(n * 4) : null;
  const c = new THREE.Color();
  for (let i = 0; i < n; i++) {
    pos.set(rows[i], i * 6);
    c.set(colors[i]);
    col.set([c.r, c.g, c.b, c.r, c.g, c.b], i * 6);
    if (uv) uv.set(uvFn(i), i * 4);
  }
  const idx = [];
  const m = closed ? n : n - 1;
  for (let i = 0; i < m; i++) {
    const a = i * 2;
    const b = ((i + 1) % n) * 2;
    idx.push(a, b, a + 1, a + 1, b, b + 1);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  if (uv) geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  geo.setIndex(idx);
  geo.computeVertexNormals();
  return geo;
}

// ── scenery props (each returns a Part built around the origin) ───────────────
const props = {
  pagoda(p = new Part()) {
    for (let i = 0; i < 3; i++) {
      const w = 7 - i * 1.6;
      p.box(w, 3.2, w, i % 2 ? '#f4e3c0' : '#e8553d', { p: [0, 2 + i * 4.4, 0] });
      p.cone(w * 0.95, 1.6, '#2f7d6d', { p: [0, 4.4 + i * 4.4, 0], r: [0, Math.PI / 4, 0] }, 4);
    }
    p.cyl(0.15, 0.15, 3, '#ffd23f', { p: [0, 15.5, 0] }, 6);
    return p;
  },
  turret(p = new Part()) {
    p.cyl(3, 3.4, 12, '#cfc7e8', { p: [0, 6, 0] }, 12);
    p.cyl(3.6, 3.6, 1.2, '#b7add9', { p: [0, 12.4, 0] }, 12);
    p.cone(3.9, 6, '#6c5ce7', { p: [0, 16, 0] }, 12);
    p.box(0.1, 2.4, 0.1, '#ffffff', { p: [0, 20, 0] });
    p.box(1.6, 0.9, 0.08, '#ff5d6c', { p: [0.8, 20.6, 0] });
    p.box(1.2, 2.2, 0.3, '#3b2f66', { p: [0, 7, 3.2] });
    return p;
  },
  rocket(p = new Part()) {
    p.cyl(2, 2.3, 10, '#f5f5fa', { p: [0, 7, 0] }, 12);
    p.cone(2, 4.5, '#ff5d6c', { p: [0, 14.2, 0] }, 12);
    p.sph(0.9, '#7ef9ff', { p: [0, 9, 1.8], s: [1, 1, 0.5] });
    for (let i = 0; i < 3; i++) {
      const a = (i / 3) * Math.PI * 2;
      p.box(0.3, 4, 2.6, '#ff8a2a', { p: [Math.sin(a) * 2.6, 3, Math.cos(a) * 2.6], r: [0, a, 0] });
    }
    p.cyl(1.2, 1.8, 1.6, '#4c5560', { p: [0, 1.4, 0] }, 10);
    return p;
  },
  mushroom(p = new Part()) {
    p.cyl(1.8, 2.3, 5, '#fff3dc', { p: [0, 2.5, 0] }, 10);
    p.sph(4.6, '#ff5d6c', { p: [0, 5, 0], s: [1, 0.62, 1] }, 14, 8);
    for (let i = 0; i < 6; i++) {
      const a = (i / 6) * Math.PI * 2;
      p.sph(0.8, '#ffffff', { p: [Math.sin(a) * 3, 6.6, Math.cos(a) * 3], s: [1, 0.4, 1] });
    }
    p.box(1.2, 2.2, 0.3, '#7a4b2c', { p: [0, 1.1, 2.2] });
    return p;
  },
  clockTower(p = new Part()) {
    p.box(4, 16, 4, '#d9b382', { p: [0, 8, 0] });
    p.cyl(1.7, 1.7, 0.3, '#fff9e8', { p: [0, 13, 2.05], r: [Math.PI / 2, 0, 0] }, 16);
    p.box(0.18, 1.3, 0.1, '#1c1a22', { p: [0, 13.5, 2.25] });
    p.box(0.9, 0.18, 0.1, '#1c1a22', { p: [0.4, 13, 2.25] });
    p.cone(3.6, 4, '#3f6fb5', { p: [0, 18, 0], r: [0, Math.PI / 4, 0] }, 4);
    return p;
  },
  lamp(p = new Part()) {
    p.cyl(0.12, 0.18, 4.4, '#4c5560', { p: [0, 2.2, 0] }, 6);
    p.sph(0.4, '#ffe9a3', { p: [0, 4.6, 0] }, 8, 6);
    return p;
  },
  crossing(p = new Part()) {
    p.cyl(0.14, 0.18, 4.4, '#f5f5fa', { p: [0, 2.2, 0] }, 6);
    p.box(2.6, 0.36, 0.1, '#fff7ef', { p: [0, 4.2, 0], r: [0, 0, 0.6] });
    p.box(2.6, 0.36, 0.1, '#fff7ef', { p: [0, 4.2, 0], r: [0, 0, -0.6] });
    p.sph(0.3, '#ff3b3b', { p: [0.45, 3.2, 0.1] }, 8, 6);
    p.sph(0.3, '#ff3b3b', { p: [-0.45, 3.2, 0.1] }, 8, 6);
    return p;
  },
  grandstand(p = new Part()) {
    const hues = ['#ff5d6c', '#ffd23f', '#34e7ff', '#8fd39a', '#b79bff', '#ff8a2a'];
    for (let r = 0; r < 4; r++) {
      p.box(18, 1.1, 2.2, r % 2 ? '#7a6ab8' : '#6558a6', { p: [0, 0.55 + r * 1.1, -r * 2.2] });
      for (let i = 0; i < 9; i++) {
        p.sph(0.55, hues[(i * 3 + r) % hues.length], { p: [-8 + i * 2, 1.9 + r * 1.1, -r * 2.2], s: [1, 1.25, 1] }, 7, 5);
      }
    }
    p.box(18.6, 0.3, 9.6, '#ff5d6c', { p: [0, 8.2, -3.3], r: [0.12, 0, 0] });
    p.cyl(0.2, 0.2, 8, '#4c5560', { p: [9, 4, 1] }, 6);
    p.cyl(0.2, 0.2, 8, '#4c5560', { p: [-9, 4, 1] }, 6);
    return p;
  },
  teapot(p = new Part(), body = '#7fd6c2') {
    p.sph(5, body, { p: [0, 4.4, 0], s: [1, 0.86, 1] }, 16, 10);
    p.cyl(2.6, 3, 0.8, '#fff7ef', { p: [0, 0.5, 0] }, 14);
    p.sph(2.4, '#fff7ef', { p: [0, 8.2, 0], s: [1, 0.36, 1] }, 12, 6);
    p.sph(0.7, '#ff7fb0', { p: [0, 9.4, 0] }, 8, 6);
    p.tube([4.2, 4, 0], [7.6, 7.4, 0], 1.1, 0.6, body, 8);
    p.torus(2.2, 0.5, body, { p: [-5.2, 4.6, 0] }, 12, 6);
    for (let i = 0; i < 8; i++) {
      const a = (i / 8) * Math.PI * 2;
      p.sph(0.55, '#ffffff', { p: [Math.sin(a) * 4.7, 4.4, Math.cos(a) * 4.7], s: [1, 1, 0.4], r: [0, a, 0] }, 6, 5);
    }
    return p;
  },
  cupStack(p = new Part(), tint = '#ff9ec4') {
    for (let i = 0; i < 3; i++) {
      const y = i * 2.6;
      p.cyl(2.6, 2.6, 0.25, '#fff7ef', { p: [0, y + 0.15, 0] }, 14);
      p.cyl(2.0, 1.3, 2.1, i % 2 ? '#fff7ef' : tint, { p: [(i % 2) * 0.5 - 0.25, y + 1.35, 0] }, 14);
      p.torus(0.7, 0.2, i % 2 ? '#fff7ef' : tint, { p: [2.3 + (i % 2) * 0.5 - 0.25, y + 1.4, 0] }, 10, 5);
    }
    return p;
  },
  cake(p = new Part()) {
    const g = (r, h, y, c) => p.add(new THREE.CylinderGeometry(r, r, h, 3, 1), c, { p: [0, y, 0], r: [0, 0.5, 0], s: [1, 1, 0.75] });
    g(5, 1.6, 0.8, '#ffe2b0');
    g(5, 0.5, 1.85, '#ff7fb0');
    g(5, 1.6, 2.9, '#ffe2b0');
    g(5.1, 0.7, 4.05, '#fff7ef');
    p.sph(0.8, '#e23b3b', { p: [0.4, 4.9, 0.3] }, 8, 6);
    p.cyl(4.6, 4.6, 0.25, '#b8f1e0', { p: [0, 0.05, 0] }, 16);
    return p;
  },
  macarons(p = new Part()) {
    const cs = ['#ff9ec4', '#b8f1e0', '#ffe58a', '#c9a5ff', '#ffb88a'];
    for (let i = 0; i < 5; i++) {
      const y = i * 1.5;
      p.sph(2.2, cs[i], { p: [0, y + 0.45, 0], s: [1, 0.2, 1] }, 12, 5);
      p.cyl(2.0, 2.0, 0.34, '#fff7ef', { p: [0, y + 0.78, 0] }, 12);
      p.sph(2.2, cs[i], { p: [0, y + 1.1, 0], s: [1, 0.2, 1] }, 12, 5);
    }
    return p;
  },
  sugar(p = new Part()) {
    p.box(2.4, 2.4, 2.4, '#ffffff', { p: [0, 1.2, 0] });
    p.box(2.4, 2.4, 2.4, '#fdf6ff', { p: [1.6, 3.6, 0.4], r: [0, 0.5, 0] });
    p.box(2.4, 2.4, 2.4, '#ffffff', { p: [2.9, 1.2, -0.6], r: [0, 0.3, 0] });
    return p;
  },
  lollipop(p = new Part(), c1 = '#ff5d6c') {
    p.cyl(0.22, 0.22, 7, '#fff7ef', { p: [0, 3.5, 0] }, 6);
    p.cyl(2.2, 2.2, 0.6, c1, { p: [0, 8.4, 0], r: [Math.PI / 2, 0, 0] }, 16);
    p.torus(1.3, 0.22, '#ffffff', { p: [0, 8.4, 0.32] }, 14, 5);
    p.torus(1.3, 0.22, '#ffffff', { p: [0, 8.4, -0.32] }, 14, 5);
    return p;
  },
  crystal(p = new Part(), c = '#34e7ff') {
    p.cyl(0.9, 1.5, 9, c, { p: [0, 4.5, 0], r: [0, 0.3, 0.08] }, 6);
    p.cone(0.9, 2.2, '#ffffff', { p: [-0.36, 10, 0], r: [0, 0.3, 0.08] }, 6);
    p.cyl(0.6, 1.0, 5, c, { p: [1.8, 2.5, 0.6], r: [0.2, 0, -0.3] }, 6);
    p.cyl(0.5, 0.9, 4, c, { p: [-1.6, 2, -0.5], r: [-0.2, 0, 0.35] }, 6);
    return p;
  },
  neonPalm(p = new Part(), c = '#ff4fd8') {
    p.tube([0, 0, 0], [0.8, 8, 0], 0.4, 0.25, '#2b3170', 6);
    for (let i = 0; i < 6; i++) {
      const a = (i / 6) * Math.PI * 2;
      p.box(0.5, 0.14, 3.6, c, { p: [0.8 + Math.sin(a) * 1.6, 7.6, Math.cos(a) * 1.6], r: [0.5, a, 0] });
    }
    p.sph(0.5, '#ffe14f', { p: [0.8, 7.9, 0] }, 6, 5);
    return p;
  },
  billboard(p = new Part(), c = '#34e7ff') {
    p.cyl(0.3, 0.3, 7, '#2b3170', { p: [-3, 3.5, 0] }, 6);
    p.cyl(0.3, 0.3, 7, '#2b3170', { p: [3, 3.5, 0] }, 6);
    p.box(9, 4.4, 0.5, '#151a3d', { p: [0, 8.6, 0] });
    p.box(8.2, 0.5, 0.6, c, { p: [0, 10.2, 0] });
    p.box(8.2, 0.5, 0.6, c, { p: [0, 7.0, 0] });
    p.box(5, 0.5, 0.6, '#ffe14f', { p: [-1, 8.6, 0] });
    return p;
  },
  shard(p = new Part(), c = '#6c62c9') {
    p.add(new THREE.DodecahedronGeometry(2.2, 0), c, { s: [1.2, 0.7, 1] });
    p.add(new THREE.ConeGeometry(1.6, 4, 5), '#3a2f6b', { p: [0, -2.4, 0], r: [Math.PI, 0, 0] });
    return p;
  },
};

export class TrackView {
  constructor(track, quality = {}) {
    this.track = track;
    this.group = new THREE.Group();
    this.anim = [];
    this.time = 0;
    this._tmp = { x: 0, y: 0, z: 0, lat: 0, heading: 0, hw: 0 };
    this._sky();
    this._road();
    this._walls();
    this._islands();
    this._branch();
    this._startGate();
    this._teacups();
    this._scenery(quality.detail ?? 1);
  }

  _sky() {
    const geo = new THREE.SphereGeometry(900, 24, 14);
    const pos = geo.attributes.position;
    const col = new Float32Array(pos.count * 3);
    const top = new THREE.Color('#2a1a63');
    const mid = new THREE.Color('#8a3fb0');
    const hor = new THREE.Color('#ffb0bf');
    const low = new THREE.Color('#5b2a86');
    const c = new THREE.Color();
    for (let i = 0; i < pos.count; i++) {
      const y = pos.getY(i) / 900;
      if (y > 0.35) c.copy(mid).lerp(top, (y - 0.35) / 0.65);
      else if (y > 0) c.copy(hor).lerp(mid, y / 0.35);
      else c.copy(hor).lerp(low, Math.min(1, -y / 0.4));
      col.set([c.r, c.g, c.b], i * 3);
    }
    geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
    const sky = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide, fog: false, depthWrite: false }));
    sky.renderOrder = -10;
    this.sky = sky;
    this.group.add(sky);
    // stars
    const n = 320;
    const sp = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2;
      const y = 0.12 + Math.random() * 0.85;
      const r = Math.sqrt(1 - y * y);
      sp.set([Math.cos(a) * r * 850, y * 850, Math.sin(a) * r * 850], i * 3);
    }
    const sg = new THREE.BufferGeometry();
    sg.setAttribute('position', new THREE.BufferAttribute(sp, 3));
    const stars = new THREE.Points(sg, new THREE.PointsMaterial({ color: '#fff6d6', size: 2.2, sizeAttenuation: false, fog: false, depthWrite: false }));
    this.group.add(stars);
    this.stars = stars;
    // planets and moons from other dimensions
    const pl = new Part();
    pl.sph(60, '#ff9ec4', { p: [-420, 260, 520] }, 18, 12);
    pl.torus(95, 6, '#ffe58a', { p: [-420, 260, 520], r: [1.2, 0.3, 0] }, 28, 4);
    pl.sph(34, '#7ef9ff', { p: [560, 330, -300] }, 14, 10);
    pl.sph(22, '#ffd23f', { p: [200, 420, 640] }, 12, 8);
    pl.sph(80, '#b79bff', { p: [700, 150, 380] }, 18, 12);
    const planets = pl.build(new THREE.MeshToonMaterial({ vertexColors: true, gradientMap: getGradientMap(), fog: false }));
    this.group.add(planets);
  }

  _road() {
    const S = this.track.samples;
    const rows = [];
    const cols = [];
    for (const s of S) {
      rows.push([s.x - s.rx * s.hw, s.y, s.z - s.rz * s.hw, s.x + s.rx * s.hw, s.y, s.z + s.rz * s.hw]);
      cols.push(SEC[s.sec].road);
    }
    const geo = ribbon(rows, cols, true, (i) => [0, S[i].s / 9, 1, S[i].s / 9]);
    const mat = new THREE.MeshToonMaterial({ vertexColors: true, map: roadTexture(), gradientMap: getGradientMap(), side: THREE.DoubleSide });
    this.roadMat = mat;
    const road = new THREE.Mesh(geo, mat);
    this.group.add(road);
  }

  _walls() {
    const S = this.track.samples;
    const n = S.length;
    const H = 1.35;
    const T = 0.7;
    const p = new Part();
    const glowP = new Part();
    for (const side of [1, -1]) {
      let run = [];
      const flush = () => {
        if (run.length > 1) {
          // inner face, top, outer face as three ribbons
          const inner = [];
          const top = [];
          const outer = [];
          const c1 = [];
          const c2 = [];
          run.forEach((s, k) => {
            const ix = s.x + s.rx * s.hw * side;
            const iz = s.z + s.rz * s.hw * side;
            const ox = s.x + s.rx * (s.hw + T) * side;
            const oz = s.z + s.rz * (s.hw + T) * side;
            inner.push([ix, s.y - 0.05, iz, ix, s.y + H, iz]);
            top.push([ix, s.y + H, iz, ox, s.y + H, oz]);
            outer.push([ox, s.y + H, oz, ox, s.y - 1.5, oz]);
            const stripe = Math.floor(s.s / 4) % 2 === 0;
            c1.push(stripe ? SEC[s.sec].wallA : SEC[s.sec].wallB);
            c2.push(stripe ? SEC[s.sec].wallB : SEC[s.sec].wallA);
            void k;
          });
          p.geos.push(ribbon(inner, c1, false), ribbon(top, c2, false), ribbon(outer, c1, false));
        }
        run = [];
      };
      for (let i = 0; i <= n; i++) {
        const s = S[i % n];
        if (s.wall) run.push(s);
        else flush();
      }
      flush();
      // open edges: a glowing kerb line and light posts instead of a wall
      let glowRun = [];
      const flushGlow = () => {
        if (glowRun.length > 1) {
          const rows = glowRun.map((s) => {
            const ix = s.x + s.rx * (s.hw - 0.5) * side;
            const iz = s.z + s.rz * (s.hw - 0.5) * side;
            const ox = s.x + s.rx * s.hw * side;
            const oz = s.z + s.rz * s.hw * side;
            return [ix, s.y + 0.04, iz, ox, s.y + 0.04, oz];
          });
          glowP.geos.push(ribbon(rows, glowRun.map((s) => (Math.floor(s.s / 3) % 2 ? '#7ef9ff' : '#ffffff')), false));
          // thick slab edge so the bridge reads as a floating road
          const skirt = glowRun.map((s) => {
            const ox = s.x + s.rx * s.hw * side;
            const oz = s.z + s.rz * s.hw * side;
            return [ox, s.y, oz, ox - s.rx * side * 1.2, s.y - 1.6, oz - s.rz * side * 1.2];
          });
          p.geos.push(ribbon(skirt, glowRun.map(() => '#3a2f6b'), false));
        }
        glowRun = [];
      };
      for (let i = 0; i <= n; i++) {
        const s = S[i % n];
        if (!s.wall) {
          glowRun.push(s);
          if (i % 7 === 0) {
            const ox = s.x + s.rx * (s.hw - 0.25) * side;
            const oz = s.z + s.rz * (s.hw - 0.25) * side;
            p.cyl(0.12, 0.16, 0.9, '#b79bff', { p: [ox, s.y + 0.45, oz] }, 5);
            glowP.sph(0.26, '#7ef9ff', { p: [ox, s.y + 1.0, oz] }, 6, 5);
          }
        } else flushGlow();
      }
      flushGlow();
    }
    // chevrons on the outside of tight bends so corners read early
    for (let i = 0; i < n; i += 5) {
      const s = S[i];
      if (!s.wall || Math.abs(s.curv) < 0.017) continue;
      const side = s.curv > 0 ? -1 : 1; // outside of the bend
      const x = s.x + s.rx * (s.hw + 0.9) * side;
      const z = s.z + s.rz * (s.hw + 0.9) * side;
      const yaw = s.heading + (side > 0 ? -Math.PI / 2 : Math.PI / 2);
      const board = new Part();
      board.box(3.2, 1.5, 0.16, '#1c1a22', { p: [0, 0, 0] });
      const dir = -side; // arrow points toward the inside of the bend
      for (let k = 0; k < 2; k++) {
        const g = new THREE.Shape();
        const w = 0.55;
        g.moveTo(-w * dir, 0.55);
        g.lineTo(0.15 * dir, 0);
        g.lineTo(-w * dir, -0.55);
        g.lineTo(-w * dir + 0.45 * dir, -0.55);
        g.lineTo(0.6 * dir, 0);
        g.lineTo(-w * dir + 0.45 * dir, 0.55);
        board.add(new THREE.ShapeGeometry(g), '#ffe14f', { p: [(k - 0.5) * 1.3 * dir, 0, 0.1] });
        board.add(new THREE.ShapeGeometry(g), '#ffe14f', { p: [(k - 0.5) * 1.3 * dir, 0, -0.1] });
      }
      glowP.merge(board, { p: [x, s.y + 2.5, z], r: [0, yaw, 0] });
    }
    const walls = p.build(toonDouble());
    this.group.add(walls);
    const glowMesh = glowP.build(new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide }));
    this.group.add(glowMesh);
  }

  _islands() {
    const S = this.track.samples;
    const n = S.length;
    const open = this.track.def.open;
    const np = this.track.def.points.length;
    const taper = (u) => {
      // islands fade out toward the open bridge
      if (!open) return 1;
      const d0 = (open.from - u + np) % np;
      const d1 = (u - open.to + np) % np;
      if (u >= open.from && u <= open.to) return 0;
      return Math.min(1, Math.min(d0, d1) / 0.9);
    };
    const p = new Part();
    const W = 30;
    for (const side of [1, -1]) {
      const top = [];
      const cliff = [];
      const tc = [];
      const cc = [];
      let any = false;
      const flush = () => {
        if (top.length > 1) {
          p.geos.push(ribbon(top.slice(), tc.slice(), false), ribbon(cliff.slice(), cc.slice(), false));
          any = true;
        }
        top.length = cliff.length = tc.length = cc.length = 0;
      };
      for (let i = 0; i <= n; i++) {
        const s = S[i % n];
        const k = taper(s.u);
        if (k <= 0.02) {
          flush();
          continue;
        }
        const w = 3 + W * k + Math.sin(s.s * 0.05 + side) * 4 * k;
        const ix = s.x + s.rx * (s.hw + 0.3) * side;
        const iz = s.z + s.rz * (s.hw + 0.3) * side;
        const ox = s.x + s.rx * (s.hw + w) * side;
        const oz = s.z + s.rz * (s.hw + w) * side;
        const y = s.y - 0.08;
        top.push([ix, y, iz, ox, y - 0.4, oz]);
        cliff.push([ox, y - 0.4, oz, ox - s.rx * side * 7, y - 16, oz - s.rz * side * 7]);
        const check = s.sec === 'tea' && Math.floor(s.s / 6) % 2 === 0;
        tc.push(check ? '#ffd9e8' : SEC[s.sec].ground);
        cc.push(SEC[s.sec].cliff);
      }
      flush();
      void any;
    }
    this.group.add(p.build(toonDouble()));
  }

  _branch() {
    const br = this.track.branch;
    if (!br) return;
    const B = BALANCE.track.bridge;
    const mk = (s0, s1, color, y = 0.02) => {
      const rows = [];
      const cols = [];
      const uvs = [];
      for (let s = s0; s <= s1 + 0.01; s += 2) {
        const cx = br.ax + br.tx * s;
        const cz = br.az + br.tz * s;
        const cy = br.ay + ((br.by - br.ay) * s) / br.length + y;
        rows.push([cx - br.rx * br.hw, cy, cz - br.rz * br.hw, cx + br.rx * br.hw, cy, cz + br.rz * br.hw]);
        cols.push(color);
        uvs.push([0, s / 9, 1, s / 9]);
      }
      return ribbon(rows, cols, false, (i) => uvs[i]);
    };
    const mat = this.roadMat;
    this.group.add(new THREE.Mesh(mk(8, br.gap0, '#ffc46b'), mat));
    this.group.add(new THREE.Mesh(mk(br.gap1, br.length - 8, '#ffc46b'), mat));
    // the phasing span over the gap
    const spanTex = canvasTex(
      128,
      128,
      (g, w, h) => {
        g.fillStyle = '#7ef9ff';
        g.fillRect(0, 0, w, h);
        g.strokeStyle = '#ffffff';
        g.lineWidth = 6;
        for (let i = -1; i < 4; i++) {
          g.beginPath();
          g.moveTo(i * 48, 0);
          g.lineTo(i * 48 + 64, h);
          g.moveTo(i * 48 + 64, 0);
          g.lineTo(i * 48, h);
          g.stroke();
        }
      },
      { repeat: true }
    );
    this.spanMat = new THREE.MeshBasicMaterial({ map: spanTex, transparent: true, opacity: 0.85, side: THREE.DoubleSide, depthWrite: false });
    const span = new THREE.Mesh(mk(br.gap0, br.gap1, '#ffffff', 0.0), this.spanMat);
    span.material.vertexColors = false;
    this.span = span;
    this.group.add(span);

    // edges, slab sides, torn ends
    const p = new Part();
    const gp = new Part();
    for (const side of [1, -1]) {
      for (const [a, b] of [
        [10, br.gap0],
        [br.gap1, br.length - 10],
      ]) {
        const rows = [];
        const sk = [];
        for (let s = a; s <= b + 0.01; s += 2) {
          const cx = br.ax + br.tx * s + br.rx * br.hw * side;
          const cz = br.az + br.tz * s + br.rz * br.hw * side;
          rows.push([cx - br.rx * side * 0.45, br.ay + 0.06, cz - br.rz * side * 0.45, cx, br.ay + 0.06, cz]);
          sk.push([cx, br.ay, cz, cx - br.rx * side, br.ay - 1.5, cz - br.rz * side]);
        }
        gp.geos.push(ribbon(rows, rows.map((_, i) => (i % 2 ? '#ffe14f' : '#ff8a2a')), false));
        p.geos.push(ribbon(sk, sk.map(() => '#7a4a2c'), false));
      }
    }
    // jagged broken ends at the gap + warning lamps
    this.lampMats = [];
    for (const [s, dir] of [
      [br.gap0, 1],
      [br.gap1, -1],
    ]) {
      const cx = br.ax + br.tx * s;
      const cz = br.az + br.tz * s;
      for (let i = -3; i <= 3; i++) {
        p.cone(1.0, 2.2 + (i % 2) * 0.8, '#ffc46b', { p: [cx + br.rx * i * 1.8, br.ay - 0.2, cz + br.rz * i * 1.8 + br.tz * dir * 0.6], r: [dir * Math.PI * 0.5 * (br.tz < 0 ? -1 : 1), 0, 0] }, 4);
      }
    }
    for (const s of [14, br.gap0 - 22, br.gap0 - 4]) {
      for (const side of [1, -1]) {
        const cx = br.ax + br.tx * s + br.rx * (br.hw + 0.5) * side;
        const cz = br.az + br.tz * s + br.rz * (br.hw + 0.5) * side;
        p.cyl(0.16, 0.2, 3.4, '#4c5560', { p: [cx, br.ay + 1.7, cz] }, 6);
        const lm = new THREE.MeshBasicMaterial({ color: '#4cd964' });
        const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.55, 10, 8), lm);
        lamp.position.set(cx, br.ay + 3.6, cz);
        this.group.add(lamp);
        this.lampMats.push(lm);
      }
    }
    this.group.add(p.build(toonDouble()));
    this.group.add(gp.build(new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide })));

    // shortcut sign over the entry
    const tex = signTexture(
      [
        { text: 'ทางลัด', size: 62, y: 70 },
        { text: 'SHORTCUT', size: 34, y: 132 },
        { text: '⚠ สะพานเปิด-ปิด', size: 26, y: 196 },
      ],
      '#ffb02e',
      '#1c1a22'
    );
    const sign = new THREE.Mesh(new THREE.PlaneGeometry(7, 7), new THREE.MeshBasicMaterial({ map: tex, side: THREE.DoubleSide }));
    const sx = br.ax + br.tx * 16;
    const sz = br.az + br.tz * 16;
    sign.position.set(sx, br.ay + 9.5, sz);
    sign.rotation.y = br.heading + Math.PI;
    this.group.add(sign);
    const sp = new Part();
    sp.cyl(0.25, 0.3, 9, '#4c5560', { p: [sx + br.rx * (br.hw + 0.6), br.ay + 4.5, sz + br.rz * (br.hw + 0.6)] }, 6);
    sp.cyl(0.25, 0.3, 9, '#4c5560', { p: [sx - br.rx * (br.hw + 0.6), br.ay + 4.5, sz - br.rz * (br.hw + 0.6)] }, 6);
    sp.box(br.hw * 2 + 2, 0.4, 0.4, '#4c5560', { p: [sx, br.ay + 6.2, sz], r: [0, br.heading, 0] });
    this.group.add(sp.build());
    void B;
  }

  _startGate() {
    const s = this.track.samples[0];
    const p = new Part();
    for (const side of [1, -1]) {
      const x = s.x + s.rx * (s.hw + 1.4) * side;
      const z = s.z + s.rz * (s.hw + 1.4) * side;
      p.cyl(0.8, 1.0, 9.5, '#6c5ce7', { p: [x, s.y + 4.75, z] }, 10);
      p.sph(1.1, '#ffd23f', { p: [x, s.y + 10, z] }, 10, 8);
      p.torus(1.0, 0.25, '#ff5d6c', { p: [x, s.y + 3, z], r: [Math.PI / 2, 0, 0] }, 12, 5);
      p.torus(1.0, 0.25, '#34e7ff', { p: [x, s.y + 6, z], r: [Math.PI / 2, 0, 0] }, 12, 5);
    }
    this.group.add(p.build());
    const w = (s.hw + 1.4) * 2;
    const banner = new THREE.Mesh(
      new THREE.PlaneGeometry(w, w / 4),
      new THREE.MeshBasicMaterial({ map: bannerTexture('RIFT RIOT', 'ศึกซิ่งป่วนจักรวาล', '#2a1a63', '#ffd23f'), side: THREE.DoubleSide })
    );
    banner.position.set(s.x, s.y + 8.2, s.z);
    banner.rotation.y = s.heading + Math.PI;
    this.group.add(banner);
    // chequered line on the road
    const tex = canvasTex(256, 32, (g, W, H) => {
      for (let x = 0; x < 16; x++) for (let y = 0; y < 2; y++) {
        g.fillStyle = (x + y) % 2 ? '#ffffff' : '#1c1a22';
        g.fillRect(x * 16, y * 16, 16, 16);
      }
      void W;
      void H;
    });
    const line = new THREE.Mesh(new THREE.PlaneGeometry(s.hw * 2, 2.6), new THREE.MeshBasicMaterial({ map: tex }));
    line.rotation.set(-Math.PI / 2, 0, -s.heading);
    line.position.set(s.x, s.y + 0.03, s.z);
    this.group.add(line);
  }

  _teacups() {
    const track = this.track;
    const C = BALANCE.track.teacup;
    this.cups = [];
    const hazard = canvasTex(
      128,
      64,
      (g, w, h) => {
        g.fillStyle = '#fff7ef';
        g.fillRect(0, 0, w, h);
        g.fillStyle = '#ff5d8f';
        for (let i = -2; i < 8; i++) {
          g.beginPath();
          g.moveTo(i * 32, 0);
          g.lineTo(i * 32 + 16, 0);
          g.lineTo(i * 32 + 48, h);
          g.lineTo(i * 32 + 32, h);
          g.fill();
        }
      },
      { repeat: true }
    );
    hazard.repeat.set(4, 1);
    const warnTex = signTexture(
      [
        { text: '⚠', size: 96, y: 92 },
        { text: 'ถ้วยชาข้ามถนน', size: 30, y: 190 },
      ],
      '#fff7ef',
      '#e23b6c'
    );
    const tints = ['#ff7fb0', '#7fd6c2', '#ffd23f'];
    track.teacups.forEach((cup, k) => {
      const a = track.samples[cup.i];
      // painted crossing zone = exactly where the cup can be
      const zone = new THREE.Mesh(
        new THREE.PlaneGeometry((cup.amp + C.radius) * 2, 5),
        new THREE.MeshBasicMaterial({ map: hazard, transparent: true, opacity: 0.8, depthWrite: false })
      );
      zone.rotation.set(-Math.PI / 2, 0, -a.heading);
      zone.position.set(a.x, a.y + 0.04, a.z);
      zone.renderOrder = 1;
      this.group.add(zone);
      // warning boards ahead of the crossing, both sides
      const before = track.samples[(cup.i - 24 + track.n) % track.n];
      for (const side of [1, -1]) {
        const sign = new THREE.Mesh(new THREE.PlaneGeometry(3.4, 3.4), new THREE.MeshBasicMaterial({ map: warnTex, side: THREE.DoubleSide }));
        sign.position.set(before.x + before.rx * (before.hw + 1.2) * side, before.y + 4.4, before.z + before.rz * (before.hw + 1.2) * side);
        sign.rotation.y = before.heading + Math.PI;
        this.group.add(sign);
      }
      const p = new Part();
      p.cyl(C.radius * 1.25, C.radius * 1.05, 0.25, '#fff7ef', { p: [0, 0.14, 0] }, 18);
      p.cyl(C.radius, C.radius * 0.62, C.height - 0.5, tints[k % 3], { p: [0, 0.3 + (C.height - 0.5) / 2, 0] }, 18);
      p.torus(C.radius * 0.99, 0.12, '#ffffff', { p: [0, C.height - 0.2, 0], r: [Math.PI / 2, 0, 0] }, 18, 5);
      p.cyl(C.radius * 0.9, C.radius * 0.9, 0.08, '#b5651d', { p: [0, C.height - 0.42, 0] }, 16); // tea
      p.torus(0.8, 0.22, tints[k % 3], { p: [C.radius + 0.45, C.height * 0.55, 0] }, 10, 5);
      for (let i = 0; i < 6; i++) {
        const an = (i / 6) * Math.PI * 2;
        p.sph(0.3, '#ffffff', { p: [Math.sin(an) * C.radius * 0.82, C.height * 0.55, Math.cos(an) * C.radius * 0.82], s: [1, 1, 0.4], r: [0, an, 0] }, 6, 5);
      }
      const mesh = p.build();
      this.group.add(mesh);
      const shadow = new THREE.Mesh(new THREE.CircleGeometry(C.radius * 1.35, 16), new THREE.MeshBasicMaterial({ color: '#000000', transparent: true, opacity: 0.22, depthWrite: false }));
      shadow.rotation.x = -Math.PI / 2;
      this.group.add(shadow);
      this.cups.push({ cup, mesh, shadow });
    });
  }

  _scenery(detail) {
    const track = this.track;
    const P = this.track.def.points.length;
    const part = new Part();
    const glowPart = new Part();
    const tmp = {};
    let seed = 7;
    const rnd = () => {
      seed = (seed * 16807) % 2147483647;
      return seed / 2147483647;
    };
    /** place a prop beside the road at control parameter u, `off` metres beyond the wall */
    const put = (maker, u, side, off, scale = 1, yawAdd = 0, arg) => {
      const i = track.uToIndex(((u % P) + P) % P);
      const s = track.samples[i];
      const x = s.x + s.rx * (s.hw + off) * side;
      const z = s.z + s.rz * (s.hw + off) * side;
      const sub = maker(new Part(), arg);
      part.merge(sub, { p: [x, s.y - 0.4, z], r: [0, s.heading + (side > 0 ? -Math.PI / 2 : Math.PI / 2) + yawAdd, 0], s: scale });
      void tmp;
    };
    // Section 1 — plaza: architecture from many worlds
    put(props.grandstand, 0.25, 1, 9, 1, 0);
    put(props.grandstand, 27.75, -1, 9, 1, 0);
    put(props.pagoda, 0.9, -1, 16, 1.1);
    put(props.turret, 1.35, 1, 15, 1);
    put(props.rocket, 1.9, -1, 17, 1.1);
    put(props.mushroom, 2.5, 1, 13, 1.1);
    put(props.clockTower, 3.1, -1, 16, 1, 0.3);
    put(props.mushroom, 3.6, 1, 17, 0.8);
    put(props.turret, 26.5, -1, 18, 0.9);
    put(props.rocket, 27.2, 1, 16, 0.9);
    put(props.pagoda, 26.9, 1, 20, 0.8);
    for (let u = 0.2; u < 4; u += 0.45) {
      put(props.lamp, u, 1, 3.6, 1);
      put(props.lamp, u + 0.2, -1, 3.6, 1);
    }
    put(props.crossing, 0.55, 1, 3.4, 1.2);
    put(props.crossing, 0.55, -1, 3.4, 1.2);
    // Section 2 — the giant tea table
    put(props.teapot, 4.9, 1, 14, 1.15, 0.6);
    put(props.cupStack, 5.3, -1, 11, 1.2);
    put(props.cake, 5.9, 1, 13, 1.3);
    put(props.macarons, 6.3, -1, 10, 1.2);
    put(props.sugar, 6.9, 1, 9, 1.4);
    put(props.teapot, 7.3, -1, 15, 1.0, -0.8, '#ff9ec4');
    put(props.cupStack, 7.7, 1, 10, 1.3, 0, '#7fd6c2');
    put(props.cake, 8.3, -1, 12, 1.1);
    put(props.macarons, 8.8, 1, 11, 1.3);
    put(props.teapot, 9.3, -1, 14, 1.1, 0.2, '#ffe58a');
    put(props.sugar, 9.6, 1, 9, 1.2);
    for (let u = 4.7; u < 9.9; u += 0.36) {
      put(props.lollipop, u, 1, 3 + rnd() * 2, 0.8 + rnd() * 0.5, 0, ['#ff5d6c', '#7fd6c2', '#ffd23f', '#c9a5ff'][Math.floor(rnd() * 4)]);
      put(props.lollipop, u + 0.18, -1, 3 + rnd() * 2, 0.8 + rnd() * 0.5, 0, ['#ff5d6c', '#7fd6c2', '#ffd23f', '#c9a5ff'][Math.floor(rnd() * 4)]);
    }
    // Section 4 — neon dimension
    const neons = ['#34e7ff', '#ff4fd8', '#b79bff', '#7dffb0'];
    for (let u = 18.2; u < 25.9; u += 0.3 / Math.max(0.5, detail)) {
      const c = neons[Math.floor(rnd() * 4)];
      const side = rnd() < 0.5 ? 1 : -1;
      const kind = rnd();
      if (kind < 0.5) put(props.crystal, u, side, 5 + rnd() * 14, 0.8 + rnd() * 1.1, rnd() * 3, c);
      else if (kind < 0.8) put(props.neonPalm, u, side, 4 + rnd() * 6, 1 + rnd() * 0.4, rnd() * 3, c);
      else put(props.billboard, u, side, 6 + rnd() * 4, 1, 0, c);
    }
    // neon arches over the road (well above every racer)
    for (const u of [18.6, 20.5, 22.5, 24.5]) {
      const s = track.samples[track.uToIndex(u)];
      const arch = new Part();
      arch.torus(s.hw + 2.2, 0.45, neons[Math.floor(u) % 4], {}, 20, 5, Math.PI);
      glowPart.merge(arch, { p: [s.x, s.y - 0.2, s.z], r: [0, s.heading, 0] });
    }
    this.group.add(part.build());
    if (!glowPart.empty) this.group.add(glowPart.build(glow()));

    // Section 3 — floating shards around the broken bridge (instanced, slowly bobbing)
    const count = Math.round(46 * detail);
    const shardGeo = props.shard(new Part()).build().geometry;
    const inst = new THREE.InstancedMesh(shardGeo, toon(), count);
    const m = new THREE.Matrix4();
    const q = new THREE.Quaternion();
    const e = new THREE.Euler();
    const v = new THREE.Vector3();
    const sc = new THREE.Vector3();
    const br = track.branch;
    this.shards = [];
    for (let i = 0; i < count; i++) {
      const s = track.samples[track.uToIndex(10.6 + rnd() * 7)];
      const side = rnd() < 0.5 ? 1 : -1;
      const off = s.hw + 9 + rnd() * 50;
      let x = s.x + s.rx * off * side;
      let z = s.z + s.rz * off * side;
      // keep the driving surfaces clear
      if (br && Math.abs((x - br.ax) * br.rx + (z - br.az) * br.rz) < br.hw + 6) x += 18 * (rnd() < 0.5 ? 1 : -1);
      const y = s.y - 4 - rnd() * 22 + (rnd() < 0.3 ? 16 + rnd() * 14 : 0);
      e.set(rnd() * 3, rnd() * 3, rnd() * 3);
      q.setFromEuler(e);
      const k = 0.6 + rnd() * 2.2;
      m.compose(v.set(x, y, z), q, sc.set(k, k, k));
      inst.setMatrixAt(i, m);
      this.shards.push({ x, y, z, k, rx: e.x, ry: e.y, rz: e.z, ph: rnd() * 6 });
      void z;
    }
    inst.instanceMatrix.needsUpdate = true;
    this.shardMesh = inst;
    this.group.add(inst);

    // the rift itself: a slow vortex far below the bridge
    const vortexTex = canvasTex(256, 256, (g, w, h) => {
      const grd = g.createRadialGradient(w / 2, h / 2, 4, w / 2, h / 2, w / 2);
      grd.addColorStop(0, '#ffffff');
      grd.addColorStop(0.18, '#7ef9ff');
      grd.addColorStop(0.5, '#b44fff');
      grd.addColorStop(1, 'rgba(60,20,120,0)');
      g.fillStyle = grd;
      g.fillRect(0, 0, w, h);
      g.strokeStyle = 'rgba(255,255,255,0.5)';
      g.lineWidth = 5;
      for (let k = 0; k < 5; k++) {
        g.beginPath();
        for (let t = 0; t < 60; t++) {
          const a = (k / 5) * Math.PI * 2 + t * 0.09;
          const r = 8 + t * 1.9;
          g.lineTo(w / 2 + Math.cos(a) * r, h / 2 + Math.sin(a) * r);
        }
        g.stroke();
      }
    });
    const vortex = new THREE.Mesh(new THREE.PlaneGeometry(300, 300), new THREE.MeshBasicMaterial({ map: vortexTex, transparent: true, depthWrite: false, fog: false }));
    vortex.rotation.x = -Math.PI / 2;
    vortex.position.set(br ? br.ax + 40 : 400, 10 - 60, br ? br.az + br.tz * br.length * 0.5 : 20);
    this.vortex = vortex;
    this.group.add(vortex);

    // portal rings around the plaza
    this.portals = [];
    const ringColors = ['#34e7ff', '#ff4fd8', '#7dffb0', '#ffb02e'];
    [
      [0.6, 1, 26],
      [1.6, -1, 28],
      [27.4, -1, 27],
      [3.3, 1, 24],
    ].forEach(([u, side, off], k) => {
      const s = track.samples[track.uToIndex(u)];
      const x = s.x + s.rx * (s.hw + off) * side;
      const z = s.z + s.rz * (s.hw + off) * side;
      const ring = new Part();
      ring.torus(7, 0.9, ringColors[k], {}, 24, 6);
      const rm = ring.build(glow());
      rm.position.set(x, s.y + 9, z);
      rm.rotation.y = s.heading + 0.6 * side;
      this.group.add(rm);
      const disc = new THREE.Mesh(new THREE.CircleGeometry(6.5, 24), new THREE.MeshBasicMaterial({ map: vortexTex, transparent: true, depthWrite: false, side: THREE.DoubleSide, color: ringColors[k] }));
      disc.position.copy(rm.position);
      disc.rotation.y = rm.rotation.y;
      this.group.add(disc);
      this.portals.push(disc);
    });
  }

  update(dt, raceTime, bridge) {
    this.time += dt;
    const t = this.time;
    const track = this.track;
    for (const c of this.cups) {
      track.teacupPos(c.cup, raceTime, this._tmp);
      c.mesh.position.set(this._tmp.x, this._tmp.y, this._tmp.z);
      c.mesh.rotation.y = raceTime * 2.2 + c.cup.phase;
      c.shadow.position.set(this._tmp.x, this._tmp.y + 0.05, this._tmp.z);
    }
    if (this.span && bridge) {
      const blink = bridge.warn ? (Math.sin(t * 22) > 0 ? 1 : 0.25) : 1;
      this.span.visible = bridge.solid;
      this.spanMat.opacity = 0.85 * blink;
      this.spanMat.map.offset.y = t * 0.4;
      const col = !bridge.solid ? '#ff3b3b' : bridge.warn ? (Math.sin(t * 22) > 0 ? '#ffb02e' : '#5a3a10') : '#4cd964';
      for (const m of this.lampMats) m.color.set(col);
    }
    if (this.vortex) this.vortex.rotation.z = t * 0.12;
    for (let i = 0; i < this.portals.length; i++) this.portals[i].rotation.z = t * (0.5 + i * 0.13) * (i % 2 ? -1 : 1);
    this.stars.rotation.y = t * 0.004;
  }
}
