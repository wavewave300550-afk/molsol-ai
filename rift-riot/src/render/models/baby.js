// 002 — BABY HAVOC in the Turbo Stroller.
// A round devil-horned baby who never leaves the pram and drives it with a giant remote.
import * as THREE from 'three';
import { Part, addEye, glow, toonDouble, C } from '../toon.js';

export function buildBaby() {
  const root = new THREE.Group();
  const RED = '#e23b3b';
  const RED_D = '#a82525';
  const YEL = '#ffd23f';
  const SKIN = '#ffd3b8';

  // ── stroller chassis ──
  const body = new Part();
  body.sph(1.0, RED, { p: [0, 1.25, 0.1], s: [0.98, 0.62, 1.45] }); // tub
  body.box(1.5, 0.5, 2.2, '#3a2a3a', { p: [0, 1.52, 0.1] }); // dark interior (covers the tub top)
  body.torus(0.88, 0.09, YEL, { p: [0, 1.5, 0.1], r: [Math.PI / 2, 0, 0], s: [1.05, 1.52, 1] }, 20);
  body.box(0.26, 0.3, 0.1, YEL, { p: [0, 1.25, 1.52] }); // number plate
  // X-frame legs to the axles
  for (const x of [0.78, -0.78]) {
    body.tube([x, 1.0, 0.9], [x, 0.38, -1.05], 0.06, 0.06, C.chrome);
    body.tube([x, 1.0, -0.8], [x, 0.38, 1.15], 0.06, 0.06, C.chrome);
  }
  // push handle sweeping up behind
  body.tube([0.7, 1.4, -1.1], [0.7, 2.45, -2.25], 0.06, 0.06, C.chrome);
  body.tube([-0.7, 1.4, -1.1], [-0.7, 2.45, -2.25], 0.06, 0.06, C.chrome);
  body.cyl(0.09, 0.09, 1.5, '#2b2b33', { p: [0, 2.45, -2.25], r: [0, 0, Math.PI / 2] });
  // ── oversized turbo engine strapped on the back ──
  body.cyl(0.62, 0.62, 1.15, C.steel, { p: [0, 1.55, -1.75], r: [Math.PI / 2, 0, 0] }, 16);
  body.cyl(0.68, 0.68, 0.14, C.steelDark, { p: [0, 1.55, -1.25], r: [Math.PI / 2, 0, 0] }, 16);
  body.cyl(0.68, 0.68, 0.14, C.steelDark, { p: [0, 1.55, -2.25], r: [Math.PI / 2, 0, 0] }, 16);
  body.cyl(0.36, 0.5, 0.55, '#ff9a3c', { p: [0, 2.3, -1.55] }, 14); // intake scoop
  body.cyl(0.4, 0.36, 0.12, C.steelDark, { p: [0, 2.6, -1.55] }, 14);
  body.box(0.26, 0.5, 0.26, C.steelDark, { p: [0, 2.0, -1.55] });
  body.sph(0.2, YEL, { p: [0.5, 2.0, -1.4] }); // pressure gauge
  for (const x of [1, -1]) {
    body.tube([x * 0.55, 1.45, -1.9], [x * 1.0, 1.35, -2.75], 0.17, 0.2, C.chrome, 10);
    body.cyl(0.24, 0.2, 0.2, C.steelDark, { p: [x * 1.02, 1.345, -2.8], r: [Math.PI / 2 + 0.1, 0, x * 0.5] }, 10);
  }
  root.add(body.build());

  // exhaust flames (unlit, flicker)
  const flames = [];
  for (const x of [1, -1]) {
    const f = new Part();
    f.cone(0.2, 0.9, '#ffb02e', { p: [0, 0, -0.42], r: [-Math.PI / 2, 0, 0] });
    f.cone(0.11, 0.6, '#fff3a6', { p: [0, 0, -0.3], r: [-Math.PI / 2, 0, 0] });
    const m = f.build(glow());
    m.position.set(x * 1.07, 1.33, -2.9);
    m.rotation.y = x * 0.5;
    root.add(m);
    flames.push(m);
  }

  // tiny wheels that spin absurdly fast
  const axles = [];
  for (const z of [1.15, -1.05]) {
    const w = new Part();
    w.cyl(0.05, 0.05, 1.7, C.steelDark, { r: [0, 0, Math.PI / 2] });
    for (const x of [0.92, -0.92]) {
      w.cyl(0.36, 0.36, 0.2, '#2b2b33', { p: [x, 0, 0], r: [0, 0, Math.PI / 2] }, 14);
      w.cyl(0.2, 0.2, 0.22, YEL, { p: [x, 0, 0], r: [0, 0, Math.PI / 2] }, 8);
      w.box(0.23, 0.1, 0.5, '#ffffff', { p: [x, 0, 0] });
    }
    const m = w.build();
    m.position.set(0, 0.37, z);
    root.add(m);
    axles.push(m);
  }

  // canopy hood: low enough that the horns still show from the chase camera
  const cp = new Part();
  cp.add(new THREE.SphereGeometry(1.05, 14, 6, Math.PI, Math.PI, 0, Math.PI / 2), RED, { s: [0.95, 1, 1] });
  for (let i = 0; i < 4; i++) {
    cp.torus(1.06, 0.045, RED_D, { r: [-(0.02 + i * 0.5), 0, 0], s: [0.95, 1, 1] }, 14, 5, Math.PI);
  }
  cp.torus(1.06, 0.07, YEL, { r: [0, 0, 0], s: [0.95, 1, 1] }, 14, 5, Math.PI);
  const canopy = cp.build(toonDouble());
  canopy.position.set(0, 1.5, -0.35);
  root.add(canopy);

  // ── the baby ──
  const baby = new THREE.Group();
  baby.position.set(0, 1.6, 0.25);
  root.add(baby);
  const bp = new Part();
  bp.sph(0.62, SKIN, { p: [0, 0.42, 0], s: [1.05, 0.95, 0.95] }); // tummy
  bp.sph(0.6, '#ffffff', { p: [0, 0.14, 0.02], s: [1.1, 0.7, 1.0] }); // nappy
  bp.sph(0.07, YEL, { p: [0, 0.3, 0.6] }); // safety pin
  // stubby legs poking forward
  bp.cap(0.2, 0.3, SKIN, { p: [0.36, 0.12, 0.62], r: [1.35, 0, -0.25] });
  bp.cap(0.2, 0.3, SKIN, { p: [-0.36, 0.12, 0.62], r: [1.35, 0, 0.25] });
  bp.sph(0.22, SKIN, { p: [0.44, 0.17, 0.95], s: [0.9, 1.1, 1.2] });
  bp.sph(0.22, SKIN, { p: [-0.44, 0.17, 0.95], s: [0.9, 1.1, 1.2] });
  baby.add(bp.build());

  const head = new THREE.Group();
  head.position.set(0, 1.38, 0.05);
  baby.add(head);
  const hp = new Part();
  hp.sph(0.68, SKIN, { s: [1.08, 1, 1] });
  hp.sph(0.26, SKIN, { p: [0.46, -0.2, 0.3] }); // cheeks
  hp.sph(0.26, SKIN, { p: [-0.46, -0.2, 0.3] });
  hp.sph(0.12, '#ff9a8a', { p: [0.5, -0.2, 0.48], s: [1, 0.7, 0.5] });
  hp.sph(0.12, '#ff9a8a', { p: [-0.5, -0.2, 0.48], s: [1, 0.7, 0.5] });
  hp.sph(0.09, '#f4b89c', { p: [0, -0.08, 0.68] }); // nose
  hp.sph(0.13, SKIN, { p: [0.72, 0, 0], s: [0.5, 1, 0.8] });
  hp.sph(0.13, SKIN, { p: [-0.72, 0, 0], s: [0.5, 1, 0.8] });
  // little devil horns + one curl of hair
  hp.cone(0.14, 0.42, '#c21f2c', { p: [0.4, 0.62, 0.05], r: [0.1, 0, -0.5] });
  hp.cone(0.14, 0.42, '#c21f2c', { p: [-0.4, 0.62, 0.05], r: [0.1, 0, 0.5] });
  hp.torus(0.1, 0.035, '#5a3a22', { p: [0, 0.72, 0.1], r: [0, 0.4, 0] }, 10, 5);
  head.add(hp.build());

  // eyes (open) / eyes (screwed shut) / brows / mouths are separate so the face can act
  const eyesP = new Part();
  addEye(eyesP, 0.26, 0.1, 0.56, 0.17, { iris: '#3a2a1a', pupil: 0.55 });
  addEye(eyesP, -0.26, 0.1, 0.56, 0.17, { iris: '#3a2a1a', pupil: 0.55 });
  const eyes = eyesP.build();
  const shutP = new Part();
  shutP.box(0.3, 0.06, 0.06, '#3a2418', { p: [0.27, 0.1, 0.63], r: [0, 0, 0.35] });
  shutP.box(0.3, 0.06, 0.06, '#3a2418', { p: [-0.27, 0.1, 0.63], r: [0, 0, -0.35] });
  const eyesShut = shutP.build();
  const browP = new Part();
  browP.box(0.34, 0.08, 0.08, '#5a3a22', { p: [0.27, 0.34, 0.6], r: [0, 0, -0.45] });
  browP.box(0.34, 0.08, 0.08, '#5a3a22', { p: [-0.27, 0.34, 0.6], r: [0, 0, 0.45] });
  const brows = browP.build();
  const smirkP = new Part();
  smirkP.torus(0.2, 0.04, '#7a2a2a', { p: [0.04, -0.26, 0.6], r: [0.2, 0, Math.PI + 0.25] }, 10, 5, Math.PI * 0.8);
  smirkP.box(0.1, 0.12, 0.05, '#ffffff', { p: [0.02, -0.4, 0.63] }); // the one milk tooth
  const smirk = smirkP.build();
  const wailP = new Part();
  wailP.sph(0.3, '#5a1420', { p: [0, -0.3, 0.52], s: [1.1, 1.15, 0.6] });
  wailP.sph(0.17, '#ff6f7d', { p: [0, -0.42, 0.6], s: [1.1, 0.6, 0.5] });
  wailP.box(0.11, 0.13, 0.05, '#ffffff', { p: [0.02, -0.12, 0.68] });
  const wail = wailP.build();
  wail.visible = false;
  eyesShut.visible = false;
  head.add(eyes, eyesShut, brows, smirk, wail);

  // arms + the big remote (one group so it can drop to the lap)
  const arms = new THREE.Group();
  arms.position.set(0, 0.75, 0.3);
  baby.add(arms);
  const ap = new Part();
  ap.cap(0.17, 0.32, SKIN, { p: [0.55, -0.02, 0.2], r: [1.0, 0, -0.7] });
  ap.sph(0.19, SKIN, { p: [0.36, -0.06, 0.46] });
  ap.box(0.95, 0.16, 0.56, '#2d2d38', { p: [0, -0.02, 0.56], r: [-0.5, 0, 0] });
  ap.cyl(0.14, 0.14, 0.08, '#ff3b3b', { p: [-0.22, 0.12, 0.52], r: [-0.5, 0, 0] });
  ap.cyl(0.08, 0.08, 0.07, '#ffd23f', { p: [0.08, 0.14, 0.44], r: [-0.5, 0, 0] });
  ap.cyl(0.08, 0.08, 0.07, '#4cd964', { p: [0.3, 0.14, 0.44], r: [-0.5, 0, 0] });
  ap.cyl(0.08, 0.08, 0.07, '#4aa8ff', { p: [0.08, 0.03, 0.66], r: [-0.5, 0, 0] });
  ap.cyl(0.08, 0.08, 0.07, '#ffffff', { p: [0.3, 0.03, 0.66], r: [-0.5, 0, 0] });
  ap.cyl(0.02, 0.02, 0.7, C.chrome, { p: [-0.4, 0.38, 0.32], r: [-0.3, 0, 0] });
  ap.sph(0.07, '#ff3b3b', { p: [-0.4, 0.72, 0.21] });
  arms.add(ap.build());
  // jabbing arm
  const jp = new Part();
  jp.cap(0.17, 0.32, SKIN, { p: [0, -0.2, 0.12], r: [0.9, 0, 0] });
  jp.sph(0.19, SKIN, { p: [0, -0.34, 0.34] });
  jp.cap(0.07, 0.1, SKIN, { p: [0, -0.46, 0.42], r: [0.3, 0, 0] });
  const jab = jp.build();
  jab.position.set(-0.62, 0.3, 0.02);
  jab.rotation.z = -0.5;
  arms.add(jab);

  let tantrum = 0;
  function update(st) {
    const t = st.t;
    for (const ax of axles) ax.rotation.x = (st.dist / 0.36) * 1.0;
    // canopy snaps in the wind
    canopy.rotation.x = -0.08 - st.speedN * 0.14 + Math.sin(t * 21) * 0.045 * st.speedN;
    canopy.scale.set(1 + Math.sin(t * 26) * 0.02 * st.speedN, 0.92 + Math.sin(t * 17 + 1) * 0.06 * st.speedN, 1.05 + Math.sin(t * 19) * 0.05 * st.speedN);
    // turbo flames grow with speed, roar on boost
    const fl = 0.35 + st.speedN * 0.8 + st.boost * 1.2;
    flames.forEach((f, i) => {
      f.scale.set(1, 1, fl * (0.85 + Math.sin(t * 43 + i * 2) * 0.2));
      f.visible = st.speedN > 0.05;
    });
    // engine shake
    root.position.y = Math.sin(t * 38) * 0.012 * (0.3 + st.speedN);

    const wailing = st.skillPhase === 'windup' || st.skillPhase === 'recover';
    tantrum += ((wailing ? 1 : 0) - tantrum) * Math.min(1, st.dt * 18);
    const angry = st.mood === 'angry' && !wailing;
    eyes.visible = !wailing;
    eyesShut.visible = wailing;
    smirk.visible = !wailing;
    wail.visible = wailing;
    wail.scale.setScalar(0.85 + tantrum * 0.35 + Math.sin(t * 40) * 0.05);
    brows.rotation.z = 0;
    brows.position.y = angry ? -0.07 : wailing ? 0.06 : 0;
    // head: smug bob, look back at whoever is chasing, thrown back to scream
    head.rotation.x = -tantrum * 0.55 + Math.sin(t * 3) * 0.04;
    head.rotation.y = st.lookBack * 2.3 * (1 - tantrum) - st.steer * 0.3;
    head.rotation.z = Math.sin(t * 2.2) * 0.06 + (wailing ? Math.sin(t * 45) * 0.07 : 0);
    head.scale.setScalar(1 + tantrum * 0.12);
    // remote goes down onto the lap while he screams
    arms.rotation.x = tantrum * 0.75;
    arms.position.y = 0.75 - tantrum * 0.25;
    jab.position.y = 0.3 + (wailing ? 0.25 + Math.sin(t * 34) * 0.12 : Math.max(0, Math.sin(t * 11)) * 0.13);
    // squash & stretch on the body
    const sq = 1 + tantrum * 0.1 * Math.sin(t * 30) + (angry ? Math.abs(Math.sin(t * 16)) * 0.08 : 0);
    baby.scale.set(1 / Math.sqrt(sq), sq, 1 / Math.sqrt(sq));
  }

  return { root, update, height: 3.2, cam: { h: 0, d: 0 } };
}
