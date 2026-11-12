// Bedrock geometry + animation preview (bundled with esbuild, driven by Playwright).
// Conventions follow the vanilla-derived rules documented in tools/gen/modelkit.py:
// raw coordinates, rotations X:-rx, Y:+ry, Z:-rz applied in Z*Y*X order, whole model mirrored in X.
import * as THREE from "three";

const DEG = Math.PI / 180;

function molang(expr, ctx) {
  if (typeof expr === "number") return expr;
  if (typeof expr !== "string") return 0;
  let js = expr
    .replace(/\bquery\./g, "q.").replace(/\bvariable\./g, "v.").replace(/\bcontext\./g, "c.")
    .replace(/\bmath\./g, "M.").replace(/\bq\.property\(\s*'([^']+)'\s*\)/g, (_, n) => `P(${JSON.stringify(n)})`)
    .replace(/(\d)f\b/g, "$1");
  try {
    // eslint-disable-next-line no-new-func
    const f = new Function("q", "v", "c", "M", "P", "this_", `return (${js.replace(/\bthis\b/g, "this_")});`);
    const r = f(ctx.q, ctx.v, ctx.c, ctx.M, ctx.P, 0);
    return typeof r === "boolean" ? (r ? 1 : 0) : Number.isFinite(r) ? r : 0;
  } catch (e) {
    return 0;
  }
}

const M = {
  sin: (d) => Math.sin(d * DEG), cos: (d) => Math.cos(d * DEG), abs: Math.abs, sqrt: Math.sqrt, pow: Math.pow,
  max: Math.max, min: Math.min, floor: Math.floor, round: Math.round, ceil: Math.ceil,
  mod: (a, b) => a % b, clamp: (x, a, b) => Math.min(b, Math.max(a, x)), lerp: (a, b, t) => a + (b - a) * t,
  pi: Math.PI, exp: Math.exp, random: (a, b) => (a + b) / 2, atan2: (y, x) => Math.atan2(y, x) / DEG,
};

function evalChannel(ch, t, ctx, defaultVal) {
  if (ch === undefined) return defaultVal;
  const val = (x) => (Array.isArray(x) ? x.map((e) => molang(e, ctx)) : [molang(x, ctx), molang(x, ctx), molang(x, ctx)]);
  if (Array.isArray(ch) || typeof ch !== "object") return val(ch);
  const keys = Object.keys(ch).map(Number).sort((a, b) => a - b);
  const get = (k) => {
    const e = ch[Object.keys(ch).find((kk) => Number(kk) === k)];
    return val(e && !Array.isArray(e) && typeof e === "object" ? e.post ?? e.pre : e);
  };
  if (t <= keys[0]) return get(keys[0]);
  if (t >= keys[keys.length - 1]) return get(keys[keys.length - 1]);
  for (let i = 0; i < keys.length - 1; i++) {
    if (t >= keys[i] && t <= keys[i + 1]) {
      const a = get(keys[i]), b = get(keys[i + 1]);
      const k = (t - keys[i]) / (keys[i + 1] - keys[i]);
      return a.map((x, j) => x + (b[j] - x) * k);
    }
  }
  return defaultVal;
}

function eulerRaw(r) {
  // Bedrock value [rx,ry,rz] -> standard right-handed rotation in raw coordinates.
  return new THREE.Euler(-r[0] * DEG, r[1] * DEG, -r[2] * DEG, "ZYX");
}

function faceUV(geo, faceIndex, uvRect, tw, th) {
  // BoxGeometry face order: +x (east?), -x, +y, -y, +z, -z. We remap per our naming.
  const uv = geo.attributes.uv;
  const [u, v, w, h] = uvRect;
  const u0 = u / tw, u1 = (u + w) / tw, v0 = 1 - v / th, v1 = 1 - (v + h) / th;
  const base = faceIndex * 4;
  // three's box face vertex order: (0,1) top-left, top-right, bottom-left, bottom-right in uv space
  uv.setXY(base + 0, u0, v0);
  uv.setXY(base + 1, u1, v0);
  uv.setXY(base + 2, u0, v1);
  uv.setXY(base + 3, u1, v1);
}

const FACE_INDEX = { east: 0, west: 1, up: 2, down: 3, south: 4, north: 5 };

export function buildModel(geoJson, textures, materialsFor) {
  const desc = geoJson.description;
  const tw = desc.texture_width, th = desc.texture_height;
  const root = new THREE.Group();
  const bones = {};
  const list = geoJson.bones;
  for (const b of list) {
    const node = new THREE.Group();
    node.userData = { pivot: b.pivot || [0, 0, 0], rest: b.rotation || [0, 0, 0], name: b.name };
    const content = new THREE.Group();
    node.add(content);
    node.userData.content = content;
    for (const c of b.cubes || []) {
      const s = c.size.map((x) => Math.max(x, 0.001));
      const inf = c.inflate || 0;
      const g = new THREE.BoxGeometry(s[0] + inf * 2, s[1] + inf * 2, s[2] + inf * 2);
      const faces = c.uv || {};
      const groups = [];
      const boxUV = Array.isArray(faces);
      for (const [face, idx] of Object.entries(FACE_INDEX)) {
        const f = boxUV ? null : faces[face];
        if (f) faceUV(g, idx, [f.uv[0], f.uv[1], f.uv_size[0], f.uv_size[1]], tw, th);
        groups.push(boxUV || !!f);
      }
      // hide faces without uv
      g.clearGroups();
      for (let i = 0; i < 6; i++) g.addGroup(i * 6, 6, groups[i] ? 0 : 1);
      const mats = [materialsFor(b.name), new THREE.MeshBasicMaterial({ visible: false })];
      const mesh = new THREE.Mesh(g, mats);
      const center = [c.origin[0] + c.size[0] / 2, c.origin[1] + c.size[1] / 2, c.origin[2] + c.size[2] / 2];
      if (c.rotation) {
        const pv = c.pivot || center;
        const holder = new THREE.Group();
        holder.position.set(pv[0], pv[1], pv[2]);
        holder.rotation.copy(eulerRaw(c.rotation));
        mesh.position.set(center[0] - pv[0], center[1] - pv[1], center[2] - pv[2]);
        holder.add(mesh);
        holder.userData.abs = true;
        content.add(holder);
      } else {
        mesh.position.set(center[0], center[1], center[2]);
        content.add(mesh);
      }
    }
    bones[b.name.toLowerCase()] = { node, def: b };
  }
  // hierarchy: node positioned at pivot (absolute) relative to parent pivot; content offset by -pivot
  for (const b of list) {
    const me = bones[b.name.toLowerCase()];
    const p = me.def.pivot || [0, 0, 0];
    const parent = b.parent ? bones[b.parent.toLowerCase()] : null;
    const pp = parent ? parent.def.pivot || [0, 0, 0] : [0, 0, 0];
    me.node.position.set(p[0] - pp[0], p[1] - pp[1], p[2] - pp[2]);
    me.node.userData.base = me.node.position.clone();
    me.node.userData.content.position.set(-p[0], -p[1], -p[2]);
    (parent ? parent.node : root).add(me.node);
  }
  const mirror = new THREE.Group();
  mirror.scale.set(-1, 1, 1);
  mirror.add(root);
  return { object: mirror, bones };
}

export function pose(model, anims, t, ctx) {
  for (const { node, def } of Object.values(model.bones)) {
    const rest = def.rotation || [0, 0, 0];
    let rot = [...rest], pos = [0, 0, 0], scl = [1, 1, 1];
    for (const a of anims) {
      const bb = a.bones || {};
      const key = Object.keys(bb).find((k) => k.toLowerCase() === def.name.toLowerCase());
      if (!key) continue;
      const len = a.animation_length || 0;
      let at = t;
      if (a.loop === true && len > 0) at = t % len;
      const c2 = { ...ctx, q: { ...ctx.q, anim_time: at } };
      const r = evalChannel(bb[key].rotation, at, c2, [0, 0, 0]);
      const p = evalChannel(bb[key].position, at, c2, [0, 0, 0]);
      const s = evalChannel(bb[key].scale, at, c2, [1, 1, 1]);
      rot = rot.map((x, i) => x + r[i]);
      pos = pos.map((x, i) => x + p[i]);
      scl = scl.map((x, i) => x * s[i]);
    }
    node.rotation.copy(eulerRaw(rot));
    node.position.set(node.userData.base.x + pos[0], node.userData.base.y + pos[1], node.userData.base.z + pos[2]);
    node.scale.set(scl[0] || 1e-4, scl[1] || 1e-4, scl[2] || 1e-4);
  }
}

window.GRIMOIRE_PREVIEW = { THREE, buildModel, pose, molang, M };
