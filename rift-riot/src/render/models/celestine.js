// 003 — CELESTINE, the Rolling Ballerina, inside her Crystal Dance Ball.
// The shell is a display layer that rolls with travel; she stays upright inside it
// and tiptoes (bourrée) faster the faster she goes. Pirouette = she spins, not the camera.
import * as THREE from 'three';
import { Part, Limb2, addEye } from '../toon.js';

const R = 1.9;

export function buildCelestine() {
  const root = new THREE.Group();
  const PINK = '#f7a8c8';
  const TUTU = '#ffd6e8';
  const SKIN = '#ffe2d0';
  const HAIR = '#6b3f2a';
  const SHOE = '#ff8fb3';
  const TIGHTS = '#fff1f5';

  // ── the dancer ──
  const dancer = new THREE.Group();
  dancer.position.set(0, 0.16, 0);
  root.add(dancer);
  const body = new THREE.Group(); // hips-up, leans with turns
  body.position.set(0, 1.42, 0);
  dancer.add(body);

  const bp = new Part();
  bp.sph(0.27, PINK, { p: [0, 0, 0], s: [1.05, 0.9, 0.9] }); // hips
  bp.cyl(0.2, 0.24, 0.5, PINK, { p: [0, 0.32, 0] }, 12); // slim waist
  bp.sph(0.26, PINK, { p: [0, 0.62, 0.02], s: [1.1, 0.85, 0.85] }); // chest
  bp.sph(0.13, SKIN, { p: [0.3, 0.72, 0] }); // shoulders
  bp.sph(0.13, SKIN, { p: [-0.3, 0.72, 0] });
  bp.cyl(0.075, 0.09, 0.32, SKIN, { p: [0, 0.93, 0] }, 8); // long neck
  bp.box(0.4, 0.05, 0.3, '#ffffff', { p: [0, 0.78, 0.06] }); // neckline trim
  body.add(bp.build());

  // tutu: stiff layered plate that bounces
  const tp = new Part();
  tp.cyl(0.3, 1.02, 0.14, TUTU, { p: [0, 0.0, 0] }, 20);
  tp.cyl(0.3, 0.92, 0.12, '#fff0f6', { p: [0, 0.07, 0] }, 20);
  tp.cyl(0.28, 0.8, 0.1, PINK, { p: [0, 0.13, 0] }, 20);
  tp.torus(1.0, 0.04, '#ffffff', { p: [0, -0.06, 0], r: [Math.PI / 2, 0, 0] }, 24, 5);
  const tutu = tp.build();
  tutu.position.set(0, 0.06, 0);
  body.add(tutu);

  const head = new THREE.Group();
  head.position.set(0, 1.3, 0.02);
  body.add(head);
  const hp = new Part();
  hp.sph(0.3, SKIN, { s: [0.95, 1.08, 0.98] });
  hp.sph(0.31, HAIR, { p: [0, 0.06, -0.05], s: [1.0, 1.0, 1.0] }); // hair cap
  hp.sph(0.3, SKIN, { p: [0, -0.03, 0.06], s: [0.93, 1.0, 0.95] }); // face in front of the hair
  hp.sph(0.17, HAIR, { p: [0, 0.34, -0.14] }); // neat bun
  hp.torus(0.13, 0.03, '#ffd23f', { p: [0, 0.25, -0.08], r: [Math.PI / 2 - 0.4, 0, 0] }, 12, 5);
  hp.sph(0.045, '#f4b8a0', { p: [0, -0.06, 0.34] });
  addEye(hp, 0.11, 0.0, 0.26, 0.065, { iris: '#3d5a8a' });
  addEye(hp, -0.11, 0.0, 0.26, 0.065, { iris: '#3d5a8a' });
  hp.box(0.16, 0.025, 0.03, '#3a2418', { p: [0.115, 0.075, 0.3], r: [0, 0, -0.12] }); // lashes
  hp.box(0.16, 0.025, 0.03, '#3a2418', { p: [-0.115, 0.075, 0.3], r: [0, 0, 0.12] });
  hp.sph(0.06, '#ffb0bd', { p: [0.19, -0.1, 0.24], s: [1, 0.6, 0.5] });
  hp.sph(0.06, '#ffb0bd', { p: [-0.19, -0.1, 0.24], s: [1, 0.6, 0.5] });
  hp.torus(0.06, 0.016, '#c2455c', { p: [0, -0.15, 0.3], r: [0.1, 0, Math.PI] }, 8, 4, Math.PI);
  head.add(hp.build());

  // limbs (in dancer space so targets are easy to express)
  const hand = (pb, len) => pb.sph(0.075, SKIN, { p: [0, -len - 0.04, 0], s: [0.8, 1.3, 0.8] });
  const shoe = (pb, len) => {
    pb.sph(0.1, SHOE, { p: [0, -len - 0.08, 0.02], s: [0.8, 1.7, 0.85] }); // en pointe
    pb.torus(0.075, 0.018, SHOE, { p: [0, -len + 0.12, 0], r: [Math.PI / 2, 0, 0] }, 8, 4);
  };
  const armL = new Limb2(dancer, 0.52, 0.5, 0.065, 0.055, SKIN, SKIN, hand);
  const armR = new Limb2(dancer, 0.52, 0.5, 0.065, 0.055, SKIN, SKIN, hand);
  const legL = new Limb2(dancer, 0.66, 0.66, 0.1, 0.075, TIGHTS, TIGHTS, shoe);
  const legR = new Limb2(dancer, 0.66, 0.66, 0.1, 0.075, TIGHTS, TIGHTS, shoe);

  // ── crystal ball (transparent, drawn after the dancer so she never disappears) ──
  const shell = new THREE.Group();
  shell.position.set(0, R, 0);
  root.add(shell);
  const sphereGeo = new THREE.SphereGeometry(R, 28, 18);
  const backMat = new THREE.MeshBasicMaterial({ color: '#bfeaff', transparent: true, opacity: 0.1, side: THREE.BackSide, depthWrite: false });
  const frontMat = new THREE.MeshPhongMaterial({
    color: '#dff6ff',
    transparent: true,
    opacity: 0.17,
    shininess: 120,
    specular: new THREE.Color('#ffffff'),
    depthWrite: false,
  });
  const back = new THREE.Mesh(sphereGeo, backMat);
  const front = new THREE.Mesh(sphereGeo, frontMat);
  back.renderOrder = 5;
  front.renderOrder = 7;
  shell.add(back, front);
  // seams + stars painted on the shell make the rolling readable
  const sp = new Part();
  sp.torus(R, 0.028, '#ffffff', { r: [Math.PI / 2, 0, 0] }, 40, 4);
  sp.torus(R, 0.028, '#ffc6e0', { r: [0, 0, 0] }, 40, 4);
  sp.torus(R, 0.028, '#a8ecff', { r: [0, Math.PI / 2, 0] }, 40, 4);
  for (let i = 0; i < 14; i++) {
    const a = i * 2.399;
    const y = 1 - (i + 0.5) / 7;
    const rr = Math.sqrt(1 - y * y);
    sp.add(new THREE.OctahedronGeometry(0.09), i % 2 ? '#ffffff' : '#ffe58a', { p: [Math.cos(a) * rr * R, y * R, Math.sin(a) * rr * R], s: [1, 1.6, 1] });
  }
  const seams = sp.build(new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.75, depthWrite: false }));
  seams.renderOrder = 6;
  shell.add(seams);

  const qRoll = new THREE.Quaternion();
  const axisX = new THREE.Vector3(1, 0, 0);
  const axisZ = new THREE.Vector3(0, 0, 1);
  let lastDist = 0;
  let phase = 0;
  let spin = 0;
  let pir = 0; // 0..1 blend into the pirouette pose

  function update(st) {
    const t = st.t;
    // shell rolls with distance travelled (and a touch sideways when sliding)
    const ds = st.dist - lastDist;
    lastDist = st.dist;
    if (Math.abs(ds) < 5) {
      qRoll.setFromAxisAngle(axisX, ds / R);
      shell.quaternion.premultiply(qRoll);
      qRoll.setFromAxisAngle(axisZ, st.slip * st.drift * ds * 0.3);
      shell.quaternion.premultiply(qRoll);
    }
    const active = st.skillPhase === 'active';
    pir += ((active ? 1 : 0) - pir) * Math.min(1, st.dt * 9);
    frontMat.opacity = 0.17 + pir * 0.06;

    // tiptoe steps: quicker with speed, tiny and precise
    const rate = 5 + st.speedN * 22;
    phase += rate * st.dt;
    const stepLift = 0.1 + st.speedN * 0.1;
    const lean = st.steer * 0.22;
    body.rotation.z = lean * (1 - pir);
    body.rotation.x = 0.06 * st.speedN * (1 - pir);
    body.position.x = -st.steer * 0.12 * (1 - pir);
    body.position.y = 1.42 + Math.abs(Math.sin(phase)) * 0.035 + pir * 0.1;
    head.rotation.z = -lean * 0.6;
    head.rotation.x = -0.08 - pir * 0.12;
    tutu.rotation.x = Math.sin(phase * 2) * 0.05;
    tutu.scale.set(1 + pir * 0.18, 1 - pir * 0.3 + Math.sin(phase * 2) * 0.06, 1 + pir * 0.18);

    // pirouette: she turns, the root (and therefore the camera) does not
    if (pir > 0.02) spin += st.dt * (4 + pir * 19);
    else spin *= 0.8;
    dancer.rotation.y = pir > 0.02 ? spin : 0;

    const hipY = body.position.y;
    const bx = body.position.x;
    // legs
    const lz = Math.cos(phase) * 0.16;
    const liftL = Math.max(0, Math.sin(phase)) * stepLift;
    const liftR = Math.max(0, -Math.sin(phase)) * stepLift;
    // supporting leg en pointe, working leg drawn up to passé during the pirouette
    const passe = pir;
    legL.solve(bx + 0.13, hipY, 0, 0.1 * (1 - pir), 0.02 + liftL * (1 - pir), lz * (1 - pir), 0.2, 0, 1);
    legR.solve(bx - 0.13, hipY, 0, -0.1 + passe * -0.12, 0.02 + liftR * (1 - pir) + passe * 0.72, -lz * (1 - pir) + passe * 0.22, -0.6 - passe, 0, 1);

    // arms: second position while travelling, port de bras into the turn, fifth overhead when spinning
    const sway = Math.sin(phase * 0.5) * 0.06;
    const shY = hipY + 0.72;
    const upL = Math.max(0, st.steer) * 0.5;
    const upR = Math.max(0, -st.steer) * 0.5;
    const ax = 0.92 * (1 - pir) + 0.16 * pir;
    const ayL = (shY - 0.08 + upL + sway) * (1 - pir) + (shY + 0.98) * pir;
    const ayR = (shY - 0.08 + upR - sway) * (1 - pir) + (shY + 0.98) * pir;
    const az = 0.22 * (1 - pir) + 0.1 * pir;
    armL.solve(bx + 0.3, shY, 0, bx + ax, ayL, az, 0.3, -0.5 + pir, -1);
    armR.solve(bx - 0.3, shY, 0, bx - ax, ayR, az, -0.3, -0.5 + pir, -1);
    void t;
  }

  return { root, update, height: 3.8, cam: { h: 0.4, d: 0.8 }, ballRadius: R };
}
