// 006 — UNCLE GATOR in the Flying Porta-Potty.
// The whole booth hovers (no wheels). The open doorway faces the chase camera so
// you always see him sitting there, fully dressed, cuddling a fat little alligator.
import * as THREE from 'three';
import { Part, addEye, glow, toonDouble } from '../toon.js';

export function buildGator() {
  const root = new THREE.Group();
  const BLUE = '#2f8fd8';
  const BLUE_D = '#2374b5';
  const ROOF = '#e9f5ff';
  const SKIN = '#6b4430';
  const SHIRT = '#ff8a2a';
  const GREEN = '#58b84a';
  const GREEN_L = '#cfe9a3';

  const bob = new THREE.Group(); // hover bob + bank
  root.add(bob);
  const spin = new THREE.Group(); // hurricane spin (visual only — the camera ignores it)
  bob.add(spin);

  const W = 1.2; // half width
  const H = 3.1;
  // ── booth: floor, three walls, roof. The -z side is open ──
  const bp = new Part();
  bp.box(W * 2 + 0.1, 0.2, W * 2 + 0.1, BLUE_D, { p: [0, 0.1, 0] });
  bp.box(W * 2, H, 0.12, BLUE, { p: [0, H / 2 + 0.2, W] }); // front wall (direction of travel)
  bp.box(0.12, H, W * 2, BLUE, { p: [W, H / 2 + 0.2, 0] });
  bp.box(0.12, H, W * 2, BLUE, { p: [-W, H / 2 + 0.2, 0] });
  for (const x of [W, -W]) {
    for (const z of [W, -W]) bp.box(0.2, H + 0.1, 0.2, BLUE_D, { p: [x, H / 2 + 0.2, z] }); // corner posts
    // side vents
    for (let i = 0; i < 3; i++) bp.box(0.06, 0.07, 0.9, '#1b5a8f', { p: [x * 1.05, 2.75 - i * 0.16, 0.1] });
  }
  bp.box(W * 2 + 0.3, 0.14, W * 2 + 0.3, BLUE_D, { p: [0, H + 0.25, 0] });
  bp.sph(1.0, ROOF, { p: [0, H + 0.28, 0], s: [W * 1.12, 0.36, W * 1.12] }, 12, 6); // domed roof
  bp.cyl(0.11, 0.11, 0.9, '#d0d6dc', { p: [0.8, H + 0.6, 0.8] }, 8); // vent stack
  bp.cyl(0.17, 0.11, 0.12, '#aab2ba', { p: [0.8, H + 1.08, 0.8] }, 8);
  bp.box(W * 2, 0.2, 0.14, BLUE_D, { p: [0, H + 0.1, -W] }); // lintel over the doorway
  // toilet against the front wall
  bp.cyl(0.52, 0.42, 0.75, '#fafcff', { p: [0, 0.58, 0.45] }, 14);
  bp.torus(0.47, 0.09, '#ffffff', { p: [0, 0.98, 0.45], r: [Math.PI / 2, 0, 0] }, 16, 6);
  bp.box(1.0, 1.0, 0.36, '#fafcff', { p: [0, 1.5, 0.95] });
  bp.box(1.08, 0.1, 0.44, '#e6edf5', { p: [0, 2.03, 0.95] });
  bp.cyl(0.05, 0.05, 0.3, '#c9d2da', { p: [0.42, 1.8, 0.74], r: [Math.PI / 2, 0, 0] }, 6); // flush handle
  // loo roll on the wall
  bp.cyl(0.17, 0.17, 0.3, '#ffffff', { p: [-W + 0.22, 1.5, -0.3], r: [Math.PI / 2, 0, 0] }, 10);
  spin.add(bp.build());

  // hover glow underneath (unlit)
  const hv = new Part();
  hv.cyl(1.25, 0.9, 0.12, '#8ff3ff', { p: [0, 0, 0] }, 18);
  hv.cyl(0.7, 0.4, 0.2, '#ffffff', { p: [0, -0.1, 0] }, 14);
  const hover = hv.build(new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.8 }));
  hover.position.y = -0.05;
  spin.add(hover);

  // ── door: hinged on one side of the doorway, always open, swings with inertia ──
  const doorPivot = new THREE.Group();
  doorPivot.position.set(W, 0.2, -W);
  spin.add(doorPivot);
  const dp = new Part();
  dp.box(W * 2 - 0.1, H - 0.1, 0.1, BLUE, { p: [-W + 0.05, H / 2, 0] });
  dp.box(W * 2 - 0.5, 0.1, 0.13, BLUE_D, { p: [-W, H - 0.5, 0] });
  dp.box(W * 2 - 0.5, 0.1, 0.13, BLUE_D, { p: [-W, 0.5, 0] });
  // crescent-moon cut-out (classic outhouse) painted on both faces
  for (const z of [0.06, -0.06]) {
    dp.cyl(0.3, 0.3, 0.02, '#ffe58a', { p: [-W, H - 1.1, z], r: [Math.PI / 2, 0, 0] }, 14);
    dp.cyl(0.25, 0.25, 0.03, BLUE, { p: [-W + 0.14, H - 1.04, z], r: [Math.PI / 2, 0, 0] }, 14);
  }
  dp.box(0.34, 0.16, 0.14, '#4cd964', { p: [-W * 2 + 0.45, 1.6, 0] }); // "vacant" latch
  dp.sph(0.09, '#d0d6dc', { p: [-W * 2 + 0.3, 1.35, -0.1] });
  const door = dp.build(toonDouble());
  doorPivot.add(door);

  // ── Uncle Gator, seated, facing out of the doorway (-z) ──
  const uncle = new THREE.Group();
  uncle.position.set(0, 0.92, 0.4);
  uncle.scale.setScalar(0.84);
  uncle.rotation.y = Math.PI; // builds facing +z, turned to face the camera side
  spin.add(uncle);
  const up = new Part();
  up.sph(0.62, SHIRT, { p: [0, 0.52, 0.12], s: [1.08, 1.0, 1.0] }); // big round belly in a Hawaiian shirt
  up.sph(0.5, SHIRT, { p: [0, 1.02, 0], s: [1.15, 0.8, 0.85] }); // chest & shoulders
  const flowers = ['#fff6d6', '#ffe14f', '#ff5d8f', '#fff6d6', '#7fe0c5'];
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * Math.PI * 2 + 0.3;
    const y = 0.25 + ((i * 7) % 10) * 0.085;
    const rr = y < 0.85 ? 0.63 : 0.5;
    up.sph(0.085, flowers[i % 5], { p: [Math.sin(a) * rr * 1.05, y + 0.05, 0.1 + Math.cos(a) * rr * 0.92], s: [1, 1, 0.5], r: [0, a, 0] });
  }
  up.box(0.1, 0.5, 0.06, '#fff6d6', { p: [0, 0.95, 0.5], r: [0.25, 0, 0] }); // open collar strip
  // khaki shorts + legs + flip-flops
  up.cap(0.24, 0.5, '#d9c79a', { p: [0.32, 0.1, 0.5], r: [Math.PI / 2 - 0.1, 0, -0.12] });
  up.cap(0.24, 0.5, '#d9c79a', { p: [-0.32, 0.1, 0.5], r: [Math.PI / 2 - 0.1, 0, 0.12] });
  up.cap(0.15, 0.55, SKIN, { p: [0.4, -0.38, 0.95], r: [0.15, 0, 0] });
  up.cap(0.15, 0.55, SKIN, { p: [-0.4, -0.38, 0.95], r: [0.15, 0, 0] });
  up.box(0.3, 0.08, 0.6, '#35c26b', { p: [0.4, -0.78, 1.08] });
  up.box(0.3, 0.08, 0.6, '#35c26b', { p: [-0.4, -0.78, 1.08] });
  up.sph(0.16, SKIN, { p: [0.4, -0.7, 1.12], s: [1, 0.6, 1.6] });
  up.sph(0.16, SKIN, { p: [-0.4, -0.7, 1.12], s: [1, 0.6, 1.6] });
  // arms cradling the gator
  up.tube([0.6, 1.1, 0.05], [0.82, 0.62, 0.4], 0.17, 0.14, SHIRT);
  up.tube([0.82, 0.62, 0.4], [0.42, 0.55, 0.8], 0.13, 0.11, SKIN);
  up.tube([-0.6, 1.1, 0.05], [-0.82, 0.62, 0.4], 0.17, 0.14, SHIRT);
  up.tube([-0.82, 0.62, 0.4], [-0.42, 0.5, 0.8], 0.13, 0.11, SKIN);
  up.sph(0.15, SKIN, { p: [0.38, 0.55, 0.84] });
  up.sph(0.15, SKIN, { p: [-0.38, 0.5, 0.84] });
  up.cyl(0.17, 0.2, 0.18, SKIN, { p: [0, 1.38, 0.02] }, 8);
  uncle.add(up.build());

  const head = new THREE.Group();
  head.position.set(0, 1.78, 0.06);
  uncle.add(head);
  const hp = new Part();
  hp.sph(0.44, SKIN, { s: [1, 1.02, 1] });
  hp.sph(0.4, '#d9d9d9', { p: [0, -0.2, 0.08], s: [1.04, 0.75, 1.0] }); // grizzled beard
  hp.sph(0.3, SKIN, { p: [0, -0.02, 0.2], s: [1.05, 0.8, 0.9] }); // face over the beard
  hp.sph(0.13, '#5a3826', { p: [0, -0.02, 0.5], s: [1.2, 0.9, 1] }); // broad nose
  hp.sph(0.1, SKIN, { p: [0.44, 0.02, 0], s: [0.5, 1, 0.8] });
  hp.sph(0.1, SKIN, { p: [-0.44, 0.02, 0], s: [0.5, 1, 0.8] });
  hp.sph(0.16, '#d9d9d9', { p: [0.13, -0.14, 0.44], s: [1.2, 0.5, 0.6], r: [0, 0, -0.2] }); // moustache
  hp.sph(0.16, '#d9d9d9', { p: [-0.13, -0.14, 0.44], s: [1.2, 0.5, 0.6], r: [0, 0, 0.2] });
  hp.torus(0.13, 0.03, '#fff6ee', { p: [0, -0.2, 0.43], r: [0.1, 0, Math.PI] }, 8, 4, Math.PI); // easy grin
  // sunglasses
  hp.box(0.3, 0.19, 0.08, '#15151c', { p: [0.19, 0.1, 0.4] });
  hp.box(0.3, 0.19, 0.08, '#15151c', { p: [-0.19, 0.1, 0.4] });
  hp.box(0.14, 0.05, 0.06, '#15151c', { p: [0, 0.13, 0.42] });
  hp.box(0.04, 0.05, 0.5, '#15151c', { p: [0.36, 0.13, 0.18] });
  hp.box(0.04, 0.05, 0.5, '#15151c', { p: [-0.36, 0.13, 0.18] });
  // straw hat
  hp.cyl(0.85, 0.85, 0.05, '#e8cf7a', { p: [0, 0.3, 0] }, 18);
  hp.cyl(0.4, 0.46, 0.34, '#f0d98a', { p: [0, 0.48, 0] }, 14);
  hp.cyl(0.47, 0.47, 0.1, '#d94f3a', { p: [0, 0.37, 0] }, 14); // hat band
  head.add(hp.build());

  // ── the alligator: small, fat, real model, on his lap ──
  const gatorG = new THREE.Group();
  gatorG.position.set(-0.12, 0.62, 0.72);
  uncle.add(gatorG);
  const gp = new Part();
  gp.sph(0.34, GREEN, { p: [0, 0.04, 0], s: [1.75, 1.15, 1.2] }); // tubby body lying across the lap
  gp.sph(0.3, GREEN_L, { p: [0, -0.1, 0.1], s: [1.6, 0.95, 1.15] });
  gp.sph(0.26, GREEN, { p: [0.72, 0.1, 0.06], s: [1.1, 0.9, 1.0] }); // head
  gp.sph(0.2, GREEN, { p: [1.0, 0.04, 0.08], s: [1.5, 0.6, 0.95] }); // snout
  gp.sph(0.2, GREEN_L, { p: [0.98, -0.04, 0.08], s: [1.4, 0.4, 0.85] }); // lower jaw
  gp.sph(0.035, '#2a3a22', { p: [1.26, 0.1, 0.16] });
  gp.sph(0.035, '#2a3a22', { p: [1.26, 0.1, 0.0] });
  for (let i = 0; i < 4; i++) gp.cone(0.03, 0.07, '#ffffff', { p: [0.86 + i * 0.1, -0.02, 0.24], r: [Math.PI, 0, 0] }, 4); // tiny teeth
  for (let i = 0; i < 5; i++) gp.cone(0.07, 0.12, '#3f9a36', { p: [-0.4 + i * 0.2, 0.28, 0] }, 4); // back ridge
  for (const sx of [0.4, -0.35]) {
    gp.cap(0.08, 0.14, GREEN, { p: [sx, -0.2, 0.3], r: [0.6, 0, 0] }); // dangling legs
  }
  gatorG.add(gp.build());
  const ge = new Part();
  addEye(ge, 0.72, 0.32, 0.2, 0.1, { iris: '#1a1a1a', white: '#fff7b8', dir: [0.3, 0, 1] });
  addEye(ge, 0.72, 0.32, -0.08, 0.1, { iris: '#1a1a1a', white: '#fff7b8', dir: [0.3, 0, 1] });
  gatorG.add(ge.build(glow()));
  const gt = new Part();
  gt.cone(0.24, 0.95, GREEN, { p: [-0.42, 0, 0], r: [0, 0, Math.PI / 2], s: [1, 1, 0.8] }, 8);
  for (let i = 0; i < 3; i++) gt.cone(0.06, 0.1, '#3f9a36', { p: [-0.15 - i * 0.2, 0.2 - i * 0.04, 0] }, 4);
  const gtail = gt.build();
  gtail.position.set(-0.55, 0.02, 0);
  gatorG.add(gtail);

  let doorA = 1.9;
  let doorV = 0;
  let spinA = 0;
  let spinV = 0;
  let bank = 0;
  let slide = 0;
  let flick = 0;
  let wasActive = false;

  function update(st) {
    const t = st.t;
    const active = st.skillPhase === 'active';
    if (active && !wasActive) flick = 1;
    wasActive = active;
    flick = Math.max(0, flick - st.dt * 2.2);

    // hover: bobs, banks hard into corners and slides its tail out like an air-drift
    bob.position.y = 0.55 + Math.sin(t * 2.6) * 0.09 + Math.sin(t * 7.3) * 0.02;
    bank += (st.steer * 0.3 + st.drift * 0.12 - bank) * Math.min(1, st.dt * 5);
    slide += (st.steer * 0.22 + st.drift * st.slip * 0.6 - slide) * Math.min(1, st.dt * 4);
    bob.rotation.z = bank;
    bob.rotation.y = slide;
    bob.rotation.x = -0.04 - st.speedN * 0.05 + Math.sin(t * 1.9) * 0.02;
    hover.scale.setScalar(1 + Math.sin(t * 14) * 0.05);
    hover.material.opacity = 0.55 + Math.sin(t * 9) * 0.15 + st.boost * 0.2;

    // hurricane spin (eases in and back to a clean forward-facing stop)
    const target = active ? 11 : 0;
    spinV += (target - spinV) * Math.min(1, st.dt * (active ? 5 : 3));
    if (active || spinV > 0.6) spinA += spinV * st.dt;
    else {
      const rest = Math.round(spinA / (Math.PI * 2)) * Math.PI * 2;
      spinA += (rest - spinA) * Math.min(1, st.dt * 8);
    }
    spin.rotation.y = spinA;

    // door: a damped pendulum driven by turning; never swings shut over the occupant
    const drive = st.yawRate * 2.4 + spinV * 0.35;
    doorV += (-(doorA - 1.9) * 26 - doorV * 3.2 + drive * 14) * st.dt;
    doorA += doorV * st.dt;
    if (doorA < 1.25) {
      doorA = 1.25;
      doorV = Math.abs(doorV) * 0.4;
    }
    if (doorA > 2.9) {
      doorA = 2.9;
      doorV = -Math.abs(doorV) * 0.4;
    }
    doorPivot.rotation.y = -doorA;

    // uncle: perfectly relaxed; the gator's tail does the work
    head.rotation.z = Math.sin(t * 1.3) * 0.06;
    head.rotation.y = Math.sin(t * 0.7) * 0.18 - st.lookBack * 0.3;
    uncle.position.y = 0.92 + Math.sin(t * 2.6 + 0.5) * 0.02;
    gtail.rotation.y = Math.sin(t * (active ? 22 : 3)) * (active ? 0.7 : 0.25) + flick * 1.2;
    gatorG.rotation.z = Math.sin(t * 2) * 0.04;
    gatorG.scale.setScalar(0.84 * (1 + flick * 0.12));
  }

  return { root, update, height: 4.3, cam: { h: -0.5, d: 1.2 } };
}
