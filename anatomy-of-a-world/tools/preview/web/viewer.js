// Preview renderer: voxel bodies + Bedrock entity geometry (with textures and
// animation poses) in one three.js scene. Driven by tools/preview/render.mjs.
import * as THREE from "/three/build/three.module.js";

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, 1, 0.5, 4000);

const hemi = new THREE.HemisphereLight(0xdfeeff, 0x6a5a48, 1.25);
scene.add(hemi);
const sun = new THREE.DirectionalLight(0xfff4e0, 1.6);
sun.position.set(-120, 220, -90);
scene.add(sun);
const fill = new THREE.DirectionalLight(0xb8d0ff, 0.45);
fill.position.set(140, 60, 120);
scene.add(fill);

window.__ready = false;

function setSize(w, h) {
  renderer.setSize(w, h, false);
  renderer.domElement.style.width = w + "px";
  renderer.domElement.style.height = h + "px";
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}

function skyGradient(top, bottom) {
  const c = document.createElement("canvas");
  c.width = 2;
  c.height = 256;
  const g = c.getContext("2d");
  const grad = g.createLinearGradient(0, 0, 0, 256);
  grad.addColorStop(0, top);
  grad.addColorStop(1, bottom);
  g.fillStyle = grad;
  g.fillRect(0, 0, 2, 256);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

// ------------------------------------------------------------------ voxels
const shadeGeo = (() => {
  // unit cube with Minecraft-like per-face shading baked as vertex colours
  const geo = new THREE.BoxGeometry(1, 1, 1);
  const n = geo.attributes.normal;
  const col = new Float32Array(n.count * 3);
  for (let i = 0; i < n.count; i++) {
    const nx = n.getX(i);
    const ny = n.getY(i);
    const nz = n.getZ(i);
    const s = ny > 0.5 ? 1.0 : ny < -0.5 ? 0.5 : Math.abs(nx) > 0.5 ? 0.62 : 0.8;
    col[i * 3] = col[i * 3 + 1] = col[i * 3 + 2] = s;
    void nz;
  }
  geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
  return geo;
})();

function addVoxels(buf, meta, opts = {}) {
  const dv = new DataView(buf);
  const n = buf.byteLength / 7;
  const groups = new Map();
  for (let i = 0; i < n; i++) {
    const o = i * 7;
    const b = dv.getUint8(o + 6);
    const p = meta.palette[b];
    if (!p || !p.color) continue;
    const key = p.emissive ? "e" : p.water ? "w" : "s";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(dv.getInt16(o, true), dv.getInt16(o + 2, true), dv.getInt16(o + 4, true), b);
  }
  const m4 = new THREE.Matrix4();
  const color = new THREE.Color();
  for (const [key, arr] of groups) {
    const count = arr.length / 4;
    const mat =
      key === "e"
        ? new THREE.MeshBasicMaterial({ vertexColors: false })
        : key === "w"
          ? new THREE.MeshLambertMaterial({ transparent: true, opacity: 0.72, vertexColors: true })
          : new THREE.MeshLambertMaterial({ vertexColors: true });
    const mesh = new THREE.InstancedMesh(shadeGeo, mat, count);
    for (let i = 0; i < count; i++) {
      const x = arr[i * 4];
      const y = arr[i * 4 + 1];
      const z = arr[i * 4 + 2];
      const p = meta.palette[arr[i * 4 + 3]];
      const small = p.small;
      if (small) {
        m4.makeScale(0.55, 0.55, 0.55);
        m4.setPosition(x + 0.5, y + 0.3, z + 0.5);
      } else {
        m4.makeTranslation(x + 0.5, y + 0.5, z + 0.5);
      }
      mesh.setMatrixAt(i, m4);
      // deterministic per-block jitter for texture-like variation
      const j = ((Math.imul(x * 73856093 ^ y * 19349663 ^ z * 83492791, 2654435761) >>> 0) % 1000) / 1000;
      const k = 0.9 + j * 0.16;
      color.setRGB(((p.color[0] / 255) * k) ** 2.2, ((p.color[1] / 255) * k) ** 2.2, ((p.color[2] / 255) * k) ** 2.2);
      mesh.setColorAt(i, color);
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    if (opts.group) opts.group.add(mesh);
    else scene.add(mesh);
  }
}

// ------------------------------------------------------------------ Bedrock geometry
// Bedrock geometry units are 1/16 block. Model space: +X is the model's left?  We follow
// Blockbench's Bedrock conventions: a cube's origin is its minimum corner, bones rotate
// around their pivot with Euler [rx, ry, rz] applied in Z->Y->X order with X and Y negated
// relative to three.js' right-handed frame.  The whole model is flipped on X when rendered
// (Bedrock mirrors X), which Blockbench reproduces with a scale(-1,1,1) on the root.
const DEG = Math.PI / 180;

function bedrockEuler(r) {
  // Blockbench shows Bedrock models in an X-mirrored space with rotation (-rx, -ry, rz), order ZYX.
  // We keep geometry in Bedrock space and mirror at the root, so the equivalent rotation is
  // M * R_bb * M = Rz(-rz) * Ry(ry) * Rx(-rx).
  return new THREE.Euler(-r[0] * DEG, r[1] * DEG, -r[2] * DEG, "ZYX");
}

function faceUV(texW, texH, u, v, w, h) {
  // returns [u0,v0,u1,v1] in 0..1 with v flipped for three.js
  return [u / texW, 1 - v / texH, (u + w) / texW, 1 - (v + h) / texH];
}

function buildCubeGeometry(cube, texW, texH) {
  const [ox, oy, oz] = cube.origin;
  const [sx, sy, sz] = cube.size;
  const inf = cube.inflate ?? 0;
  const x0 = ox - inf, y0 = oy - inf, z0 = oz - inf;
  const x1 = ox + sx + inf, y1 = oy + sy + inf, z1 = oz + sz + inf;
  // face definitions in Bedrock model space (before X mirror)
  const faces = {
    north: { n: [0, 0, -1], v: [[x1, y1, z0], [x0, y1, z0], [x1, y0, z0], [x0, y0, z0]] },
    south: { n: [0, 0, 1], v: [[x0, y1, z1], [x1, y1, z1], [x0, y0, z1], [x1, y0, z1]] },
    east: { n: [1, 0, 0], v: [[x1, y1, z1], [x1, y1, z0], [x1, y0, z1], [x1, y0, z0]] },
    west: { n: [-1, 0, 0], v: [[x0, y1, z0], [x0, y1, z1], [x0, y0, z0], [x0, y0, z1]] },
    up: { n: [0, 1, 0], v: [[x0, y1, z0], [x1, y1, z0], [x0, y1, z1], [x1, y1, z1]] },
    down: { n: [0, -1, 0], v: [[x0, y0, z1], [x1, y0, z1], [x0, y0, z0], [x1, y0, z0]] },
  };
  let uvs = {};
  if (Array.isArray(cube.uv)) {
    // box UV
    const [u, v] = cube.uv;
    const fsx = Math.floor(sx), fsy = Math.floor(sy), fsz = Math.floor(sz);
    uvs = {
      east: [u, v + fsz, fsz, fsy],
      north: [u + fsz, v + fsz, fsx, fsy],
      west: [u + fsz + fsx, v + fsz, fsz, fsy],
      south: [u + fsz + fsx + fsz, v + fsz, fsx, fsy],
      up: [u + fsz, v, fsx, fsz],
      down: [u + fsz + fsx, v, fsx, fsz],
    };
    if (cube.mirror) {
      const t = uvs.east;
      uvs.east = uvs.west;
      uvs.west = t;
    }
  } else if (cube.uv) {
    for (const [f, d] of Object.entries(cube.uv)) uvs[f] = [d.uv[0], d.uv[1], d.uv_size[0], d.uv_size[1]];
  }
  const pos = [];
  const nor = [];
  const uv = [];
  const idx = [];
  for (const [name, f] of Object.entries(faces)) {
    const r = uvs[name];
    if (!r) continue;
    let [u0, v0, u1, v1] = faceUV(texW, texH, r[0], r[1], r[2], r[3]);
    if (name === "up" || name === "down") {
      // Bedrock up/down faces: up texture's top edge is north; down is flipped on V
      if (name === "down") [v0, v1] = [v1, v0];
    }
    if (cube.mirror && !Array.isArray(cube.uv)) [u0, u1] = [u1, u0];
    const base = pos.length / 3;
    const corners = [
      [u0, v0],
      [u1, v0],
      [u0, v1],
      [u1, v1],
    ];
    for (let i = 0; i < 4; i++) {
      pos.push(...f.v[i]);
      nor.push(...f.n);
      uv.push(...corners[i]);
    }
    idx.push(base, base + 2, base + 1, base + 2, base + 3, base + 1);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute("normal", new THREE.Float32BufferAttribute(nor, 3));
  geo.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
  geo.setIndex(idx);
  return geo;
}

/**
 * Build a three.js object from Bedrock geometry JSON.
 * pose: { boneName: { rotation:[x,y,z], position:[x,y,z], scale:n|[x,y,z] } } in Bedrock animation units.
 */
function buildBedrockModel(geoJson, textureUrl, opts = {}) {
  const geom = geoJson["minecraft:geometry"][0];
  const desc = geom.description;
  const texW = desc.texture_width;
  const texH = desc.texture_height;
  const tex = new THREE.TextureLoader().load(textureUrl, () => (window.__texLoaded = (window.__texLoaded ?? 0) + 1));
  tex.magFilter = THREE.NearestFilter;
  tex.minFilter = THREE.NearestFilter;
  tex.colorSpace = THREE.SRGBColorSpace;
  const mat = new THREE.MeshLambertMaterial({ map: tex, transparent: true, alphaTest: 0.05, side: THREE.DoubleSide });
  const emissiveMat = opts.emissiveAlpha
    ? new THREE.ShaderMaterial({
        uniforms: { map: { value: tex } },
        vertexShader: "varying vec2 vUv; varying vec3 vN; void main(){ vUv=uv; vN=normalMatrix*normal; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);} ",
        fragmentShader:
          "uniform sampler2D map; varying vec2 vUv; varying vec3 vN; void main(){ vec4 c=texture2D(map,vUv); float lit=0.55+0.45*max(dot(normalize(vN),normalize(vec3(-0.4,0.8,-0.3))),0.0); vec3 base=pow(c.rgb,vec3(2.2)); vec3 col= mix(base*lit*1.25, base*1.6, 1.0-c.a); gl_FragColor=vec4(pow(col,vec3(1.0/2.2)),1.0);} ",
      })
    : null;
  const root = new THREE.Group();
  const flip = new THREE.Group();
  flip.scale.set(-1, 1, 1); // Bedrock renders model X mirrored
  root.add(flip);
  const bones = {};
  const pose = opts.pose ?? {};
  for (const b of geom.bones) {
    const g = new THREE.Group();
    g.name = b.name;
    bones[b.name] = { group: g, def: b };
  }
  for (const b of geom.bones) {
    const { group, def } = bones[b.name];
    const pivot = def.pivot ?? [0, 0, 0];
    const parent = def.parent ? bones[def.parent] : null;
    const parentPivot = parent ? parent.def.pivot ?? [0, 0, 0] : [0, 0, 0];
    // group positioned at its pivot (relative to the parent's pivot)
    group.position.set(pivot[0] - parentPivot[0], pivot[1] - parentPivot[1], pivot[2] - parentPivot[2]);
    const rot = [...(def.rotation ?? [0, 0, 0])];
    const p = pose[b.name];
    if (p?.rotation) for (let i = 0; i < 3; i++) rot[i] += p.rotation[i];
    group.setRotationFromEuler(bedrockEuler(rot));
    if (p?.position) {
      group.position.x += p.position[0];
      group.position.y += p.position[1];
      group.position.z += p.position[2];
    }
    if (p?.scale !== undefined) {
      const s = Array.isArray(p.scale) ? p.scale : [p.scale, p.scale, p.scale];
      group.scale.set(s[0], s[1], s[2]);
    }
    for (const cube of def.cubes ?? []) {
      const cg = buildCubeGeometry(cube, texW, texH);
      const cpivot = cube.pivot ?? pivot;
      const holder = new THREE.Group();
      holder.position.set(cpivot[0] - pivot[0], cpivot[1] - pivot[1], cpivot[2] - pivot[2]);
      if (cube.rotation) holder.setRotationFromEuler(bedrockEuler(cube.rotation));
      const mesh = new THREE.Mesh(cg, emissiveMat ?? mat);
      mesh.position.set(-cpivot[0], -cpivot[1], -cpivot[2]);
      holder.add(mesh);
      group.add(holder);
    }
    (parent ? parent.group : flip).add(group);
  }
  const s = opts.scale ?? 1;
  root.scale.set(s / 16, s / 16, s / 16);
  if (opts.position) root.position.set(...opts.position);
  if (opts.yaw !== undefined) root.rotation.y = -opts.yaw * DEG + Math.PI; // Bedrock yaw 0 faces +Z; models face -Z (north)
  return root;
}

// ------------------------------------------------------------------ public API (called by Playwright)
window.preview = {
  async setup({ width = 1280, height = 800, sky = ["#7fb2ff", "#e9f2ff"], fog = null }) {
    setSize(width, height);
    scene.background = skyGradient(sky[0], sky[1]);
    if (fog) scene.fog = new THREE.Fog(fog.color, fog.near, fog.far);
  },
  async voxels(url, metaUrl, clip) {
    let buf = await (await fetch(url)).arrayBuffer();
    const meta = await (await fetch(metaUrl)).json();
    if (clip) {
      // keep voxels on the near side of a plane: axis/value, e.g. {axis:2, max:0}
      const dv = new DataView(buf);
      const keep = [];
      for (let o = 0; o < buf.byteLength; o += 7) {
        const v = dv.getInt16(o + clip.axis * 2, true);
        if (clip.max !== undefined && v > clip.max) continue;
        if (clip.min !== undefined && v < clip.min) continue;
        keep.push(o);
      }
      const nb = new Uint8Array(keep.length * 7);
      const src = new Uint8Array(buf);
      keep.forEach((o, i) => nb.set(src.subarray(o, o + 7), i * 7));
      buf = nb.buffer;
    }
    addVoxels(buf, meta);
    return { n: buf.byteLength / 7 };
  },
  clouds(y, size = 600, opacity = 0.85) {
    const c = document.createElement("canvas");
    c.width = c.height = 256;
    const g = c.getContext("2d");
    g.fillStyle = "rgba(0,0,0,0)";
    g.fillRect(0, 0, 256, 256);
    for (let i = 0; i < 900; i++) {
      const x = Math.random() * 256;
      const y2 = Math.random() * 256;
      const r = 6 + Math.random() * 18;
      const grd = g.createRadialGradient(x, y2, 0, x, y2, r);
      grd.addColorStop(0, "rgba(255,255,255,0.55)");
      grd.addColorStop(1, "rgba(255,255,255,0)");
      g.fillStyle = grd;
      g.fillRect(x - r, y2 - r, r * 2, r * 2);
    }
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(4, 4);
    const m = new THREE.Mesh(new THREE.PlaneGeometry(size, size), new THREE.MeshBasicMaterial({ map: t, transparent: true, opacity, depthWrite: false }));
    m.rotation.x = -Math.PI / 2;
    m.position.y = y;
    scene.add(m);
    const m2 = m.clone();
    m2.position.y = y - 3;
    scene.add(m2);
  },
  model(geoJson, textureUrl, opts) {
    const obj = buildBedrockModel(geoJson, textureUrl, opts);
    scene.add(obj);
    return true;
  },
  marker(pos, color = 0xff00ff, r = 0.6) {
    const m = new THREE.Mesh(new THREE.SphereGeometry(r, 12, 8), new THREE.MeshBasicMaterial({ color }));
    m.position.set(pos[0], pos[1], pos[2]);
    scene.add(m);
  },
  clear() {
    for (const c of [...scene.children]) if (!(c instanceof THREE.Light)) scene.remove(c);
  },
  render({ eye, target, fov = 45 }) {
    camera.fov = fov;
    camera.position.set(...eye);
    camera.lookAt(...target);
    camera.updateProjectionMatrix();
    renderer.render(scene, camera);
    return true;
  },
};
window.__ready = true;
