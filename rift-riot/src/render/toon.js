// Shared cartoon look: stepped toon shading, vertex-coloured merged parts.
// A whole rigid body part (dozens of primitives) becomes ONE draw call.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

let gradientMap = null;
export function getGradientMap() {
  if (!gradientMap) {
    const data = new Uint8Array([120, 120, 120, 255, 185, 185, 185, 255, 235, 235, 235, 255, 255, 255, 255, 255]);
    gradientMap = new THREE.DataTexture(data, 4, 1, THREE.RGBAFormat);
    gradientMap.minFilter = gradientMap.magFilter = THREE.NearestFilter;
    gradientMap.needsUpdate = true;
  }
  return gradientMap;
}

let toonMat = null;
let toonMatDouble = null;
let glowMat = null;
export function toon() {
  return (toonMat ??= new THREE.MeshToonMaterial({ vertexColors: true, gradientMap: getGradientMap() }));
}
export function toonDouble() {
  return (toonMatDouble ??= new THREE.MeshToonMaterial({ vertexColors: true, gradientMap: getGradientMap(), side: THREE.DoubleSide }));
}
/** Unlit vertex colours: lamps, flames, eyes that must stay bright. */
export function glow() {
  return (glowMat ??= new THREE.MeshBasicMaterial({ vertexColors: true }));
}

const _m = new THREE.Matrix4();
const _q = new THREE.Quaternion();
const _e = new THREE.Euler();
const _p = new THREE.Vector3();
const _s = new THREE.Vector3();
const _c = new THREE.Color();

export class Part {
  constructor() {
    this.geos = [];
  }
  /** o: { p:[x,y,z], r:[rx,ry,rz], s: number | [sx,sy,sz] } */
  add(geo, color, o = {}) {
    const p = o.p || [0, 0, 0];
    const r = o.r || [0, 0, 0];
    const s = o.s === undefined ? [1, 1, 1] : typeof o.s === 'number' ? [o.s, o.s, o.s] : o.s;
    _e.set(r[0], r[1], r[2]);
    _q.setFromEuler(_e);
    _m.compose(_p.set(p[0], p[1], p[2]), _q, _s.set(s[0], s[1], s[2]));
    geo.applyMatrix4(_m);
    if (!geo.index) geo.setIndex([...Array(geo.attributes.position.count).keys()]);
    const n = geo.attributes.position.count;
    const arr = new Float32Array(n * 3);
    _c.set(color);
    for (let i = 0; i < n; i++) {
      arr[i * 3] = _c.r;
      arr[i * 3 + 1] = _c.g;
      arr[i * 3 + 2] = _c.b;
    }
    geo.setAttribute('color', new THREE.BufferAttribute(arr, 3));
    geo.deleteAttribute('uv');
    this.geos.push(geo);
    return this;
  }
  box(w, h, d, color, o) {
    return this.add(new THREE.BoxGeometry(w, h, d), color, o);
  }
  sph(r, color, o, ws = 14, hs = 10) {
    return this.add(new THREE.SphereGeometry(r, ws, hs), color, o);
  }
  cyl(rt, rb, h, color, o, seg = 12, open = false) {
    return this.add(new THREE.CylinderGeometry(rt, rb, h, seg, 1, open), color, o);
  }
  cone(r, h, color, o, seg = 10) {
    return this.add(new THREE.ConeGeometry(r, h, seg), color, o);
  }
  torus(R, r, color, o, seg = 16, tube = 6, arc = Math.PI * 2) {
    return this.add(new THREE.TorusGeometry(R, r, tube, seg, arc), color, o);
  }
  cap(r, len, color, o) {
    return this.add(new THREE.CapsuleGeometry(r, len, 3, 10), color, o);
  }
  /** Tapered tube between two points (static limbs, pipes, struts). */
  tube(a, b, r0, r1, color, seg = 8) {
    const dir = new THREE.Vector3(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
    const len = dir.length();
    const g = new THREE.CylinderGeometry(r1, r0, len, seg, 1);
    const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
    const e = new THREE.Euler().setFromQuaternion(q);
    return this.add(g, color, { p: [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2], r: [e.x, e.y, e.z] });
  }
  /** Bake another Part into this one with a transform (props placed around the track). */
  merge(other, o = {}) {
    const p = o.p || [0, 0, 0];
    const r = o.r || [0, 0, 0];
    const s = o.s === undefined ? [1, 1, 1] : typeof o.s === 'number' ? [o.s, o.s, o.s] : o.s;
    _e.set(r[0], r[1], r[2]);
    _q.setFromEuler(_e);
    _m.compose(_p.set(p[0], p[1], p[2]), _q, _s.set(s[0], s[1], s[2]));
    for (const g of other.geos) {
      g.applyMatrix4(_m);
      this.geos.push(g);
    }
    other.geos.length = 0;
    return this;
  }
  get empty() {
    return this.geos.length === 0;
  }
  build(material) {
    const geo = mergeGeometries(this.geos, false);
    for (const g of this.geos) g.dispose();
    this.geos.length = 0;
    const mesh = new THREE.Mesh(geo, material || toon());
    return mesh;
  }
}

/** Cartoon face helpers: eyes are a white ball + dark pupil, optionally lids. */
export function addEye(part, x, y, z, r, o = {}) {
  const dir = o.dir || [0, 0, 1];
  part.sph(r, o.white || '#ffffff', { p: [x, y, z], s: o.s || [1, 1.1, 0.7] });
  part.sph(r * (o.pupil || 0.5), o.iris || '#2a1a12', {
    p: [x + dir[0] * r * 0.55, y + dir[1] * r * 0.55, z + dir[2] * r * 0.55],
    s: [1, 1.1, 0.6],
  });
}

const _a = new THREE.Vector3();
const _b = new THREE.Vector3();
const _d = new THREE.Vector3();
const _pole = new THREE.Vector3();
const _mid = new THREE.Vector3();
const DOWN = new THREE.Vector3(0, -1, 0);

/** Two-bone limb solved analytically each frame (arms pumping, legs scuttling). */
export class Limb2 {
  constructor(parent, lenA, lenB, rA, rB, colorA, colorB, endBuilder) {
    this.a = lenA;
    this.b = lenB;
    const pa = new Part();
    pa.add(new THREE.CapsuleGeometry(rA, lenA, 3, 8), colorA, { p: [0, -lenA / 2, 0] });
    this.upper = pa.build();
    const pb = new Part();
    pb.add(new THREE.CapsuleGeometry(rB, lenB, 3, 8), colorB, { p: [0, -lenB / 2, 0] });
    if (endBuilder) endBuilder(pb, lenB);
    this.lower = pb.build();
    parent.add(this.upper, this.lower);
  }
  /** root & target are in the parent's space; pole steers where the joint bends. */
  solve(rx, ry, rz, tx, ty, tz, px, py, pz) {
    const a = this.a;
    const b = this.b;
    _a.set(rx, ry, rz);
    _b.set(tx, ty, tz);
    _d.subVectors(_b, _a);
    let dist = _d.length();
    const max = (a + b) * 0.999;
    if (dist > max) {
      _d.multiplyScalar(max / dist);
      dist = max;
      _b.addVectors(_a, _d);
    }
    if (dist < 1e-4) dist = 1e-4;
    _d.multiplyScalar(1 / dist);
    const cosA = Math.min(1, Math.max(-1, (a * a + dist * dist - b * b) / (2 * a * dist)));
    const sinA = Math.sqrt(1 - cosA * cosA);
    _pole.set(px, py, pz);
    _pole.addScaledVector(_d, -_pole.dot(_d));
    if (_pole.lengthSq() < 1e-6) _pole.set(0, 0, 1).addScaledVector(_d, -_d.z);
    _pole.normalize();
    _mid.copy(_a).addScaledVector(_d, a * cosA).addScaledVector(_pole, a * sinA);
    this.upper.position.copy(_a);
    _pole.subVectors(_mid, _a).normalize();
    this.upper.quaternion.setFromUnitVectors(DOWN, _pole);
    this.lower.position.copy(_mid);
    _pole.subVectors(_b, _mid).normalize();
    this.lower.quaternion.setFromUnitVectors(DOWN, _pole);
  }
}

export const C = {
  skinLight: '#ffd9c2',
  skinTan: '#e9b184',
  skinDark: '#6b4430',
  white: '#ffffff',
  black: '#1c1a22',
  steel: '#77828f',
  steelDark: '#4c5560',
  chrome: '#c9d2da',
  wood: '#b9793f',
  woodDark: '#8a5628',
  woodLight: '#d39a5a',
};
