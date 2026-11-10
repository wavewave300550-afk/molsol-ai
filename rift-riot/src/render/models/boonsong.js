// 001 — Uncle Boonsong on a hand-pumped railway handcar.
// He stands at the rear handle and really pumps the walking beam; pump rate follows speed.
import * as THREE from 'three';
import { Part, Limb2, addEye, C } from '../toon.js';

export function buildBoonsong() {
  const root = new THREE.Group();
  const DENIM = '#3f6fb5';
  const DENIM_D = '#2f5690';
  const SHIRT = '#f3e6c8';
  const SKIN = C.skinTan;
  const CAP = '#7d6b4c';

  // ── deck + frame ──
  const deck = new Part();
  for (let i = 0; i < 5; i++) {
    deck.box(0.5, 0.2, 4.0, i % 2 ? C.wood : C.woodLight, { p: [-1.04 + i * 0.52, 0.86, 0] });
  }
  deck.box(2.75, 0.22, 0.26, C.woodDark, { p: [0, 0.74, 1.9] });
  deck.box(2.75, 0.22, 0.26, C.woodDark, { p: [0, 0.74, -1.9] });
  deck.box(0.2, 0.26, 4.0, C.steelDark, { p: [1.0, 0.66, 0] });
  deck.box(0.2, 0.26, 4.0, C.steelDark, { p: [-1.0, 0.66, 0] });
  // A-frame carrying the beam pivot
  deck.tube([0.55, 0.95, 0.5], [0.16, 2.45, 0], 0.11, 0.08, C.steel);
  deck.tube([0.55, 0.95, -0.5], [0.16, 2.45, 0], 0.11, 0.08, C.steel);
  deck.tube([-0.55, 0.95, 0.5], [-0.16, 2.45, 0], 0.11, 0.08, C.steel);
  deck.tube([-0.55, 0.95, -0.5], [-0.16, 2.45, 0], 0.11, 0.08, C.steel);
  deck.cyl(0.14, 0.14, 0.6, C.steelDark, { p: [0, 2.45, 0], r: [0, 0, Math.PI / 2] });
  // crank housing + bell + buffer
  deck.box(0.7, 0.4, 0.9, '#a33b2c', { p: [0, 1.15, 0] });
  deck.cyl(0.07, 0.07, 0.8, C.steel, { p: [0.95, 1.35, 1.75] });
  deck.sph(0.2, '#e6b93f', { p: [0.95, 1.85, 1.75], s: [1, 0.85, 1] });
  deck.box(0.5, 0.3, 0.2, '#a33b2c', { p: [0, 0.7, 2.08] });
  root.add(deck.build());

  // lantern (unlit, brightens while laying rail)
  const lanternPart = new Part();
  lanternPart.sph(0.2, '#ffe9a3', {});
  const lantern = lanternPart.build(new THREE.MeshBasicMaterial({ vertexColors: true }));
  lantern.position.set(-0.95, 1.5, 1.8);
  const lp = new Part();
  lp.cyl(0.06, 0.06, 0.5, C.steel, { p: [-0.95, 1.2, 1.8] });
  lp.cone(0.26, 0.2, C.steelDark, { p: [-0.95, 1.75, 1.8] });
  root.add(lantern, lp.build());

  // ── wheel sets (rotate about X) ──
  const axles = [];
  for (const z of [1.3, -1.3]) {
    const w = new Part();
    w.cyl(0.07, 0.07, 2.5, C.steelDark, { r: [0, 0, Math.PI / 2] });
    for (const x of [1.12, -1.12]) {
      w.cyl(0.52, 0.52, 0.2, C.steel, { p: [x, 0, 0], r: [0, 0, Math.PI / 2] }, 16);
      w.cyl(0.62, 0.62, 0.06, C.steelDark, { p: [x - Math.sign(x) * 0.13, 0, 0], r: [0, 0, Math.PI / 2] }, 16);
      w.cyl(0.16, 0.16, 0.26, '#a33b2c', { p: [x, 0, 0], r: [0, 0, Math.PI / 2] });
      for (let k = 0; k < 4; k++) {
        const a = (k / 4) * Math.PI * 2;
        w.box(0.05, 0.1, 0.42, C.steelDark, { p: [x + Math.sign(x) * 0.105, Math.cos(a) * 0.26, Math.sin(a) * 0.26], r: [a, 0, 0] });
      }
    }
    const m = w.build();
    m.position.set(0, 0.52, z);
    root.add(m);
    axles.push(m);
  }

  // ── walking beam (pivots about X at the top of the A-frame) ──
  const beamP = new Part();
  beamP.box(0.16, 0.16, 3.3, C.steel, {});
  beamP.box(0.22, 0.3, 0.5, C.steelDark, {});
  for (const z of [1.6, -1.6]) {
    beamP.cyl(0.07, 0.07, 1.5, C.woodLight, { p: [0, 0, z], r: [0, 0, Math.PI / 2] });
    beamP.sph(0.1, C.woodDark, { p: [0.75, 0, z] });
    beamP.sph(0.1, C.woodDark, { p: [-0.75, 0, z] });
  }
  const beam = beamP.build();
  beam.position.set(0, 2.45, 0);
  root.add(beam);

  // ── the uncle ──
  const man = new THREE.Group();
  man.position.set(0, 0.96, -1.05);
  root.add(man);
  const legs = new Part();
  legs.cap(0.2, 0.75, DENIM, { p: [0.26, 0.6, 0] });
  legs.cap(0.2, 0.75, DENIM, { p: [-0.26, 0.6, 0] });
  legs.box(0.36, 0.2, 0.62, '#4a3524', { p: [0.26, 0.1, 0.1] });
  legs.box(0.36, 0.2, 0.62, '#4a3524', { p: [-0.26, 0.1, 0.1] });
  man.add(legs.build());

  const torso = new THREE.Group(); // bends at the hips while pumping
  torso.position.set(0, 1.15, 0);
  man.add(torso);
  const tp = new Part();
  tp.sph(0.5, DENIM, { p: [0, 0.18, 0.02], s: [1, 0.9, 0.82] }); // hips / dungarees
  tp.sph(0.5, SHIRT, { p: [0, 0.68, 0], s: [0.98, 0.95, 0.8] }); // shirt
  tp.box(0.56, 0.5, 0.1, DENIM, { p: [0, 0.62, 0.36] }); // bib
  tp.box(0.1, 0.62, 0.08, DENIM_D, { p: [0.24, 0.84, 0.3], r: [0.25, 0, 0.12] });
  tp.box(0.1, 0.62, 0.08, DENIM_D, { p: [-0.24, 0.84, 0.3], r: [0.25, 0, -0.12] });
  tp.sph(0.05, '#e6b93f', { p: [0.24, 0.84, 0.42] });
  tp.sph(0.05, '#e6b93f', { p: [-0.24, 0.84, 0.42] });
  tp.box(0.1, 0.5, 0.06, DENIM_D, { p: [0.24, 0.8, -0.34] });
  tp.box(0.1, 0.5, 0.06, DENIM_D, { p: [-0.24, 0.8, -0.34] });
  tp.cyl(0.14, 0.16, 0.2, SKIN, { p: [0, 1.13, 0] });
  torso.add(tp.build());

  const head = new THREE.Group();
  head.position.set(0, 1.52, 0.02);
  torso.add(head);
  const hp = new Part();
  hp.sph(0.42, SKIN, { s: [1, 1.05, 0.98] });
  hp.sph(0.13, '#d99a70', { p: [0, -0.04, 0.41], s: [1, 0.9, 1] }); // nose
  hp.sph(0.1, SKIN, { p: [0.42, 0, 0], s: [0.5, 1, 0.8] });
  hp.sph(0.1, SKIN, { p: [-0.42, 0, 0], s: [0.5, 1, 0.8] });
  // calm, half-closed eyes under bushy white brows
  addEye(hp, 0.16, 0.09, 0.34, 0.085);
  addEye(hp, -0.16, 0.09, 0.34, 0.085);
  hp.sph(0.1, SKIN, { p: [0.16, 0.15, 0.35], s: [1.15, 0.55, 0.8] });
  hp.sph(0.1, SKIN, { p: [-0.16, 0.15, 0.35], s: [1.15, 0.55, 0.8] });
  hp.sph(0.09, '#f7f7f2', { p: [0.17, 0.24, 0.36], s: [1.5, 0.5, 0.7], r: [0, 0, -0.15] });
  hp.sph(0.09, '#f7f7f2', { p: [-0.17, 0.24, 0.36], s: [1.5, 0.5, 0.7], r: [0, 0, 0.15] });
  hp.sph(0.2, '#f1efe8', { p: [0, 0.02, -0.2], s: [2.0, 1.2, 1.2] }); // white hair at the back
  // old cloth flat cap
  hp.sph(0.46, CAP, { p: [0, 0.27, -0.02], s: [1.02, 0.42, 1.08] });
  hp.sph(0.3, '#6a5a3e', { p: [0, 0.2, 0.36], s: [1.1, 0.22, 0.9] });
  hp.sph(0.05, '#6a5a3e', { p: [0, 0.47, 0] });
  head.add(hp.build());
  // moustache is its own mesh so it can bristle
  const mp = new Part();
  mp.sph(0.16, '#fbfbf6', { p: [0.15, 0, 0], s: [1.25, 0.62, 0.7], r: [0, 0, -0.35] });
  mp.sph(0.16, '#fbfbf6', { p: [-0.15, 0, 0], s: [1.25, 0.62, 0.7], r: [0, 0, 0.35] });
  mp.sph(0.07, '#fbfbf6', { p: [0.34, -0.1, -0.02] });
  mp.sph(0.07, '#fbfbf6', { p: [-0.34, -0.1, -0.02] });
  const stache = mp.build();
  stache.position.set(0, -0.17, 0.4);
  head.add(stache);

  // arms: rolled shirt sleeve + bare forearm, hands gripping the rear handle
  const hand = (pb, len) => pb.sph(0.13, SKIN, { p: [0, -len - 0.04, 0] });
  const armL = new Limb2(root, 0.62, 0.62, 0.13, 0.1, SHIRT, SKIN, hand);
  const armR = new Limb2(root, 0.62, 0.62, 0.13, 0.1, SHIRT, SKIN, hand);

  const lanternMat = lantern.material;
  let phase = 0;
  const v = new THREE.Vector3();

  function update(st) {
    // pump rate follows speed; a lazy idle rock when stopped
    const rate = 1.2 + st.speedN * 9.5 + (st.skillPhase === 'active' ? 3 : 0);
    phase += rate * st.dt;
    const amp = 0.14 + Math.min(1, st.speedN) * 0.27;
    const a = Math.sin(phase) * amp;
    beam.rotation.x = a;
    for (const ax of axles) ax.rotation.x = st.dist / 0.52;

    // rear handle position in root space (beam local z = -1.6)
    const hy = 2.45 + Math.sin(a) * 1.6;
    const hz = -Math.cos(a) * 1.6;
    // torso follows the handle up and down
    const bend = 0.34 - (hy - 2.45) * 0.42;
    torso.rotation.x = bend;
    man.position.y = 0.96 - Math.max(0, -(hy - 2.45)) * 0.12;
    head.rotation.x = -bend * 0.8 + Math.sin(phase * 0.5) * 0.02; // keeps a level, unbothered gaze
    head.rotation.y = -st.steer * 0.25;
    stache.rotation.z = Math.sin(st.t * 9) * 0.03 * (0.3 + st.speedN);
    stache.scale.y = 1 + Math.sin(st.t * 13) * 0.04 * st.speedN;

    // shoulders (torso space → root space)
    for (const side of [1, -1]) {
      v.set(side * 0.5, 0.9, 0.05).applyEuler(torso.rotation);
      const sx = man.position.x + torso.position.x + v.x;
      const sy = man.position.y + torso.position.y + v.y;
      const sz = man.position.z + torso.position.z + v.z;
      (side > 0 ? armL : armR).solve(sx, sy, sz, side * 0.52, hy + 0.02, hz - 0.02, side * 0.9, -0.6, -0.8);
    }
    const on = st.skillPhase === 'active' ? 1 : 0;
    lanternMat.color.setRGB(1 + on * 0.6, 1 + on * 0.5, 0.8 + Math.sin(st.t * 30) * 0.2 * on);
    lantern.scale.setScalar(1 + on * (0.25 + Math.sin(st.t * 24) * 0.08));
  }

  return { root, update, height: 3.6, cam: { h: 0.2, d: 0.4 } };
}
