// Headless preview renderer: node tools/preview/render.mjs <jobs.json>
// Each job: { out, geo, textures:{default, extra...}, anims:[{file,name}], frames:[{t, ctx}], camera:{yaw,pitch,dist,target,fov}, size }
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
import fs from "node:fs";
import path from "node:path";

const jobs = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const bundle = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../../.build/preview_bundle.js");

const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const page = await browser.newPage({ viewport: { width: 640, height: 640 }, deviceScaleFactor: 1 });
await page.setContent('<html><body style="margin:0;background:#000"><canvas id="c" width="640" height="640"></canvas></body></html>');
await page.addScriptTag({ path: bundle });

const dataUrl = (p) => "data:image/png;base64," + fs.readFileSync(p).toString("base64");

for (const job of jobs) {
  const geo = JSON.parse(fs.readFileSync(job.geo, "utf8"))["minecraft:geometry"].find((g) => g.description.identifier === job.geoId) ??
    JSON.parse(fs.readFileSync(job.geo, "utf8"))["minecraft:geometry"][0];
  const anims = [];
  for (const a of job.anims || []) {
    const all = JSON.parse(fs.readFileSync(a.file, "utf8")).animations;
    if (all[a.name]) anims.push(all[a.name]);
  }
  const textures = {};
  for (const [k, v] of Object.entries(job.textures)) textures[k] = dataUrl(v);
  const outFrames = await page.evaluate(async ({ geo, textures, anims, job }) => {
    const { THREE, buildModel, pose, M } = window.GRIMOIRE_PREVIEW;
    const size = job.size || 512;
    const canvas = document.getElementById("c");
    canvas.width = size; canvas.height = size;
    if (!window.__R) window.__R = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true, alpha: false });
    const renderer = window.__R;
    renderer.setSize(size, size, false);
    renderer.autoClear = true;
    renderer.setClearColor(new THREE.Color(job.bg || "#14121a"));
    const loader = new THREE.TextureLoader();
    const load = (u) => new Promise((res) => loader.load(u, (t) => { t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; res(t); }));
    const tex = {};
    for (const [k, u] of Object.entries(textures)) tex[k] = await load(u);
    const vs = `varying vec2 vUv; varying vec3 vN; void main(){ vUv=uv; vN=normalize(normalMatrix*normal); gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);} `;
    const mk = (kind, map, uvOff) => {
      const uniforms = { map: { value: map }, off: { value: new THREE.Vector2(0, uvOff || 0) } };
      const fsDefault = `uniform sampler2D map; uniform vec2 off; varying vec2 vUv; varying vec3 vN;
        void main(){ vec4 c=texture2D(map,vUv+off); float l=0.45+0.55*abs(dot(normalize(vN),normalize(vec3(0.4,0.8,0.5))));
        float glow=1.0-c.a; gl_FragColor=vec4(c.rgb*mix(l,1.25,glow),1.0); }`;
      const fsTrans = `uniform sampler2D map; uniform vec2 off; varying vec2 vUv; varying vec3 vN;
        void main(){ vec4 c=texture2D(map,vUv+off); float l=0.55+0.45*abs(dot(normalize(vN),normalize(vec3(0.4,0.8,0.5))));
        if(c.a<0.02) discard; gl_FragColor=vec4(c.rgb*l,c.a); }`;
      const fsAdd = `uniform sampler2D map; uniform vec2 off; varying vec2 vUv;
        void main(){ vec4 c=texture2D(map,vUv+off); gl_FragColor=vec4(c.rgb*c.a,1.0); }`;
      const m = new THREE.ShaderMaterial({ uniforms, vertexShader: vs, fragmentShader: kind === "glow" ? fsAdd : kind === "trans" ? fsTrans : fsDefault, side: THREE.DoubleSide });
      if (kind === "glow") { m.transparent = true; m.blending = THREE.AdditiveBlending; m.depthWrite = false; }
      if (kind === "trans") { m.transparent = true; m.depthWrite = false; }
      return m;
    };
    const frames = [];
    for (const fr of job.frames) {
      const ctx = { q: { life_time: fr.t, anim_time: fr.t, is_using_item: 0, is_sneaking: 0, body_y_rotation: 0, ...(fr.q || {}) },
        v: { size: 1, yaw: 0, pitch: 0, len: 1, ...(fr.v || {}) }, c: { is_first_person: 0, item_slot: "main_hand", ...(fr.c || {}) }, M,
        P: (n) => (fr.props || {})[n] ?? 0 };
      const scene = new THREE.Scene();
      const matFor = (name) => {
        const n = name.toLowerCase();
        if (n.startsWith("flow_")) return job.flow ? mk("glow", tex.flow, (fr.t * 0.35) % 1) : new THREE.MeshBasicMaterial({ visible: false });
        if (n.startsWith("g_")) return mk("glow", tex[fr.texKey || "default"]);
        if (n.startsWith("t_")) return mk("trans", tex[fr.texKey || "default"]);
        return mk("default", tex[fr.texKey || "default"]);
      };
      const model = buildModel(geo, tex, matFor);
      pose(model, (fr.anims || anims.map((_, i) => i)).map((i) => anims[i]), fr.t, ctx);
      scene.add(model.object);
      const cam = { yaw: 30, pitch: 18, dist: 40, target: [0, 0, 0], fov: 35, ...(job.camera || {}), ...(fr.camera || {}) };
      const camera = new THREE.PerspectiveCamera(cam.fov, 1, 0.1, 5000);
      const y = cam.yaw * Math.PI / 180, p = cam.pitch * Math.PI / 180;
      // camera on the model's front (-Z raw == +Z after mirror? front faces -Z raw; mirrored model keeps Z)
      camera.position.set(cam.target[0] + Math.sin(y) * Math.cos(p) * cam.dist, cam.target[1] + Math.sin(p) * cam.dist, cam.target[2] - Math.cos(y) * Math.cos(p) * cam.dist);
      camera.lookAt(cam.target[0], cam.target[1], cam.target[2]);
      renderer.render(scene, camera);
      frames.push(canvas.toDataURL("image/png"));
      renderer.renderLists.dispose();
    }
    return frames;
  }, { geo, textures, anims, job });
  fs.mkdirSync(path.dirname(job.out), { recursive: true });
  outFrames.forEach((d, i) => {
    const file = job.frames.length > 1 ? job.out.replace(/\.png$/, `_${i}.png`) : job.out;
    fs.writeFileSync(file, Buffer.from(d.split(",")[1], "base64"));
  });
  console.log("rendered", job.out, outFrames.length);
}
await browser.close();
