// 005 — LOVE NEVER SINKS: a couple holding one romantic pose on the back of a
// manatee that is lying on a low four-wheeled trolley. They never drive, never
// react. The trolley does the work (and blows the heart bubbles).
import * as THREE from 'three';
import { Part, addEye, glow, C } from '../toon.js';

export function buildLovers() {
  const root = new THREE.Group();
  const GREY = '#8e99a6';
  const GREY_L = '#b9c2cb';
  const GREY_D = '#737e8b';

  // ── trolley ──
  const tr = new Part();
  tr.box(2.5, 0.22, 4.7, C.wood, { p: [0, 0.62, -0.1] });
  tr.box(2.6, 0.14, 0.2, C.woodDark, { p: [0, 0.62, 2.3] });
  tr.box(2.6, 0.14, 0.2, C.woodDark, { p: [0, 0.62, -2.5] });
  tr.box(0.16, 0.16, 4.7, '#d94f7a', { p: [1.26, 0.64, -0.1] });
  tr.box(0.16, 0.16, 4.7, '#d94f7a', { p: [-1.26, 0.64, -0.1] });
  for (const x of [1.0, -1.0]) {
    for (const z of [1.7, -1.9]) {
      tr.box(0.16, 0.3, 0.16, C.steelDark, { p: [x, 0.42, z] }); // caster forks
    }
    // brass bubble horns at the back corners
    tr.cyl(0.07, 0.07, 0.5, '#d9a441', { p: [x, 0.95, -2.3] }, 8);
    tr.cyl(0.24, 0.09, 0.34, '#e8b84f', { p: [x, 1.25, -2.42], r: [-0.9, 0, 0] }, 10);
  }
  // heart emblem on the tail board
  tr.sph(0.2, '#ff5d8f', { p: [0.13, 0.98, -2.56], s: [1, 1, 0.4] });
  tr.sph(0.2, '#ff5d8f', { p: [-0.13, 0.98, -2.56], s: [1, 1, 0.4] });
  tr.cone(0.3, 0.36, '#ff5d8f', { p: [0, 0.75, -2.56], r: [Math.PI, 0, 0], s: [1, 1, 0.4] }, 4);
  root.add(tr.build());

  const wheels = [];
  for (const x of [1.0, -1.0]) {
    for (const z of [1.7, -1.9]) {
      const w = new Part();
      w.cyl(0.3, 0.3, 0.2, '#2b2b33', { r: [0, 0, Math.PI / 2] }, 12);
      w.cyl(0.14, 0.14, 0.22, C.chrome, { r: [0, 0, Math.PI / 2] }, 6);
      w.box(0.21, 0.08, 0.42, '#ffffff', {});
      const m = w.build();
      m.position.set(x, 0.3, z);
      root.add(m);
      wheels.push(m);
    }
  }

  // ── manatee (lies along z, head forward) ──
  const man = new THREE.Group();
  man.position.set(0, 0.73, 0);
  root.add(man);
  const mp = new Part();
  mp.sph(1.0, GREY, { p: [0, 0.82, 0], s: [1.2, 0.84, 2.0] }, 18, 12); // great round body
  mp.sph(1.0, GREY_L, { p: [0, 0.6, 0.1], s: [1.05, 0.62, 1.8] }, 16, 10); // pale belly
  mp.sph(0.82, GREY, { p: [0, 0.78, 1.75], s: [1.05, 0.88, 1.0] }); // head
  mp.sph(0.6, GREY_L, { p: [0, 0.6, 2.3], s: [1.15, 0.72, 0.8] }); // broad, squashed muzzle
  mp.sph(0.07, '#3b4450', { p: [0.2, 0.86, 2.68] }); // nostrils
  mp.sph(0.07, '#3b4450', { p: [-0.2, 0.86, 2.68] });
  for (const x of [1, -1]) {
    for (let i = 0; i < 3; i++) mp.sph(0.04, '#59636f', { p: [x * (0.3 + i * 0.13), 0.52 + (i % 2) * 0.1, 2.66 - i * 0.05] }); // whisker dots
    // paddle flippers resting on the board
    mp.sph(0.5, GREY_D, { p: [x * 1.2, 0.34, 0.95], s: [0.5, 0.2, 1.0], r: [0, x * 0.5, x * -0.35] });
    // sleepy eyes on the sides of the head
    mp.sph(0.1, '#20252c', { p: [x * 0.62, 1.02, 2.05] });
    mp.sph(0.13, GREY, { p: [x * 0.62, 1.09, 2.05], s: [1.1, 0.6, 1.1] }); // heavy lid
  }
  mp.sph(0.05, GREY_D, { p: [0, 1.45, 1.4], s: [6, 0.5, 1] }); // neck wrinkle
  mp.sph(0.05, GREY_D, { p: [0, 1.52, 1.1], s: [7, 0.5, 1] });
  mp.sph(0.62, GREY, { p: [0, 0.74, -1.9], s: [0.85, 0.62, 1.1] }); // tail stock
  man.add(mp.build());
  // jiggly cheeks
  const ck = new Part();
  ck.sph(0.34, GREY_L, { p: [0.42, 0, 0] });
  ck.sph(0.34, GREY_L, { p: [-0.42, 0, 0] });
  const cheeks = ck.build();
  cheeks.position.set(0, 0.55, 2.38);
  man.add(cheeks);
  // round paddle tail — a flat disc, never a fluke
  const tl = new Part();
  tl.sph(0.95, GREY_D, { p: [0, 0, -0.75], s: [1.0, 0.17, 0.95] }, 16, 8);
  tl.sph(0.3, GREY, { p: [0, 0, -0.1], s: [1.4, 0.45, 1] });
  const tail = tl.build();
  tail.position.set(0, 0.66, -2.35);
  man.add(tail);

  // ── the couple: one fixed pose, forever ──
  const couple = new THREE.Group();
  couple.position.set(0, 1.62, 0.1);
  man.add(couple);
  const SK_W = '#ffdcc6';
  const SK_M = '#f0c09a';
  const cp = new Part();
  // her: long lilac dress, arms flung wide, chin up
  cp.cyl(0.2, 0.55, 1.0, '#c9a5ff', { p: [0, 0.5, 0.3] }, 12); // skirt
  cp.cyl(0.19, 0.21, 0.45, '#b98cff', { p: [0, 1.15, 0.3] }, 10); // bodice
  cp.box(0.46, 0.06, 0.3, '#fff3fb', { p: [0, 1.38, 0.3] });
  cp.cyl(0.06, 0.07, 0.16, SK_W, { p: [0, 1.48, 0.3] }, 8);
  cp.tube([0.2, 1.36, 0.3], [1.02, 1.5, 0.34], 0.07, 0.055, SK_W);
  cp.tube([-0.2, 1.36, 0.3], [-1.02, 1.5, 0.34], 0.07, 0.055, SK_W);
  cp.sph(0.08, SK_W, { p: [1.08, 1.51, 0.34], s: [1.3, 0.7, 1] });
  cp.sph(0.08, SK_W, { p: [-1.08, 1.51, 0.34], s: [1.3, 0.7, 1] });
  cp.sph(0.24, SK_W, { p: [0, 1.75, 0.32], s: [0.95, 1.05, 1] });
  cp.sph(0.25, '#b5482c', { p: [0, 1.8, 0.24], s: [1.0, 1.0, 1.0] }); // auburn hair
  cp.sph(0.235, SK_W, { p: [0, 1.73, 0.37], s: [0.9, 0.98, 0.95] });
  cp.box(0.1, 0.02, 0.03, '#5a2a1a', { p: [0.09, 1.77, 0.57], r: [0, 0, 0.2] }); // eyes closed in bliss
  cp.box(0.1, 0.02, 0.03, '#5a2a1a', { p: [-0.09, 1.77, 0.57], r: [0, 0, -0.2] });
  cp.torus(0.05, 0.014, '#c2455c', { p: [0, 1.66, 0.57], r: [0, 0, Math.PI] }, 8, 4, Math.PI);
  cp.sph(0.05, '#ffb0bd', { p: [0.15, 1.69, 0.5], s: [1, 0.6, 0.5] });
  cp.sph(0.05, '#ffb0bd', { p: [-0.15, 1.69, 0.5], s: [1, 0.6, 0.5] });
  // him: behind her, hands at her waist, cheek by her shoulder
  cp.cap(0.13, 0.75, '#5b4636', { p: [0.14, 0.5, -0.12] }); // trousers
  cp.cap(0.13, 0.75, '#5b4636', { p: [-0.14, 0.5, -0.12] });
  cp.box(0.24, 0.12, 0.4, '#2c2420', { p: [0.14, 0.06, -0.06] });
  cp.box(0.24, 0.12, 0.4, '#2c2420', { p: [-0.14, 0.06, -0.06] });
  cp.sph(0.3, '#fbf7ee', { p: [0, 1.22, -0.12], s: [1.1, 1.25, 0.8] }); // white shirt
  cp.box(0.07, 0.6, 0.05, '#7a4b2c', { p: [0.15, 1.25, 0.1] }); // braces
  cp.box(0.07, 0.6, 0.05, '#7a4b2c', { p: [-0.15, 1.25, 0.1] });
  cp.tube([0.34, 1.42, -0.1], [0.42, 1.1, 0.16], 0.085, 0.075, '#fbf7ee');
  cp.tube([0.42, 1.1, 0.16], [0.22, 1.02, 0.36], 0.07, 0.06, SK_M);
  cp.tube([-0.34, 1.42, -0.1], [-0.42, 1.1, 0.16], 0.085, 0.075, '#fbf7ee');
  cp.tube([-0.42, 1.1, 0.16], [-0.22, 1.02, 0.36], 0.07, 0.06, SK_M);
  cp.sph(0.075, SK_M, { p: [0.21, 1.02, 0.38] });
  cp.sph(0.075, SK_M, { p: [-0.21, 1.02, 0.38] });
  cp.cyl(0.07, 0.08, 0.14, SK_M, { p: [0.1, 1.62, -0.08] }, 8);
  cp.sph(0.25, SK_M, { p: [0.16, 1.9, -0.04], s: [0.95, 1.05, 1] });
  cp.sph(0.26, '#3a2a20', { p: [0.16, 1.97, -0.1], s: [1.0, 0.85, 1.0] }); // dark hair
  cp.sph(0.24, SK_M, { p: [0.16, 1.87, 0.02], s: [0.9, 0.98, 0.95] });
  cp.box(0.09, 0.02, 0.03, '#2a1a12', { p: [0.24, 1.92, 0.22], r: [0, 0, 0.2] });
  cp.box(0.09, 0.02, 0.03, '#2a1a12', { p: [0.08, 1.92, 0.22], r: [0, 0, -0.2] });
  cp.torus(0.045, 0.013, '#9a4a3a', { p: [0.16, 1.8, 0.23], r: [0, 0, Math.PI] }, 8, 4, Math.PI);
  couple.add(cp.build());
  // the only things allowed to move: hair and a scarf in the wind
  const hairP = new Part();
  hairP.sph(0.2, '#b5482c', { p: [0, 0, -0.2], s: [1.0, 0.7, 1.6] });
  hairP.sph(0.15, '#c7583a', { p: [0.06, -0.06, -0.48], s: [0.9, 0.6, 1.5] });
  hairP.sph(0.1, '#b5482c', { p: [-0.04, -0.1, -0.7], s: [0.8, 0.6, 1.4] });
  const hair = hairP.build();
  hair.position.set(-0.1, 1.78, 0.2);
  couple.add(hair);
  const scarfP = new Part();
  scarfP.box(0.16, 0.03, 0.6, '#ff5d8f', { p: [0, 0, -0.3] });
  scarfP.box(0.14, 0.03, 0.5, '#ff7fa8', { p: [0.02, 0.03, -0.8], r: [0.15, 0.1, 0] });
  const scarf = scarfP.build();
  scarf.position.set(-0.2, 1.44, 0.26);
  couple.add(scarf);
  const tuftP = new Part();
  tuftP.sph(0.12, '#3a2a20', { p: [0, 0, -0.1], s: [1, 0.6, 1.5] });
  const tuft = tuftP.build();
  tuft.position.set(0.16, 2.14, 0.02);
  couple.add(tuft);

  // little glow lamps on the horns while the skill runs
  const gl = new Part();
  gl.sph(0.13, '#ffd0e2', { p: [1.0, 1.36, -2.52] });
  gl.sph(0.13, '#ffd0e2', { p: [-1.0, 1.36, -2.52] });
  const hornGlow = gl.build(glow());
  root.add(hornGlow);

  function update(st) {
    const t = st.t;
    for (const w of wheels) w.rotation.x = st.dist / 0.3;
    // the manatee: slow breathing, wobbling cheeks, lazy tail
    const breathe = Math.sin(t * 1.6) * 0.02;
    man.scale.set(1 + breathe, 1 - breathe, 1);
    const jig = 0.06 + Math.min(1, st.speedN) * 0.12 + st.pushed * 0.25;
    cheeks.scale.set(1 + Math.sin(t * 19) * jig, 1 + Math.sin(t * 23 + 1) * jig, 1 + Math.sin(t * 17) * jig * 0.5);
    cheeks.position.x = Math.sin(t * 11) * 0.03 - st.steer * 0.05;
    tail.rotation.x = Math.sin(t * 2.2) * 0.16 + (st.skillPhase === 'active' ? Math.sin(t * 9) * 0.12 : 0);
    man.rotation.z = -st.steer * 0.05;
    // the couple: no acting, only wind
    const wind = 0.3 + st.speedN;
    hair.rotation.y = Math.sin(t * 7) * 0.2 * wind;
    hair.rotation.x = Math.sin(t * 9 + 1) * 0.12 * wind - 0.1;
    scarf.rotation.y = Math.sin(t * 10) * 0.3 * wind;
    scarf.rotation.x = Math.sin(t * 12.5) * 0.2 * wind;
    tuft.rotation.x = Math.sin(t * 14) * 0.25 * wind;
    const on = st.skillPhase === 'active';
    hornGlow.visible = on;
    if (on) hornGlow.scale.setScalar(1 + Math.sin(t * 20) * 0.04);
  }

  return { root, update, height: 4.5, cam: { h: 1.0, d: 1.6 } };
}
