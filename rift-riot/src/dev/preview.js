// Dev-only turntable for checking a racer model: /preview.html?m=boonsong&yaw=0.6&speed=0.8&skill=active
import * as THREE from 'three';
import { MODEL_BUILDERS } from '../render/models/index.js';

const q = new URLSearchParams(location.search);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(1);
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color('#3a3560');
scene.add(new THREE.HemisphereLight('#fff4e6', '#6a5a9a', 1.5));
const sun = new THREE.DirectionalLight('#ffffff', 1.9);
sun.position.set(4, 9, 6);
scene.add(sun);
const ground = new THREE.Mesh(new THREE.CircleGeometry(6, 40), new THREE.MeshBasicMaterial({ color: '#4b4680' }));
ground.rotation.x = -Math.PI / 2;
scene.add(ground);
const cam = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.1, 200);
const m = MODEL_BUILDERS[q.get('m') || 'boonsong']();
scene.add(m.root);
const yaw = Number(q.get('yaw') ?? 0.7);
const dist = Number(q.get('d') ?? 11);
const h = Number(q.get('h') ?? 4);
cam.position.set(Math.sin(yaw) * dist, h, Math.cos(yaw) * dist);
cam.lookAt(0, Number(q.get('ly') ?? 1.6), 0);
const st = { t: 0, dt: 1 / 60, speed: 0, speedN: Number(q.get('speed') ?? 0.8), dist: 0, steer: Number(q.get('steer') ?? 0), yawRate: 0, drift: 0, slip: 0,
  airborne: q.get('air') === '1', air: Number(q.get('airh') ?? 0), vy: 0, skillPhase: q.get('skill') || 'idle', skillFrac: Number(q.get('frac') ?? 0.5), skillT: 0, boost: 0, slick: 0, pushed: 0, mood: q.get('mood') || '', lookBack: 0 };
const frames = Number(q.get('frames') ?? 90);
for (let i = 0; i < frames; i++) {
  st.t += st.dt; st.speed = st.speedN * 34; st.dist += st.speed * st.dt; st.skillT += st.dt;
  m.update(st);
}
renderer.render(scene, cam);
window.__ready = true;
if (q.get('live')) { const loop = () => { st.t += st.dt; st.dist += st.speed * st.dt; st.skillT += st.dt; m.update(st); renderer.render(scene, cam); requestAnimationFrame(loop); }; loop(); }
