// 004 — GRANNY CRACKLEBONE. No vehicle: she bends over backwards into a bridge
// and scuttles on hands and feet, feet first, with her polite upside-down face
// smiling back at whoever is behind her. Creepy by rhythm, never by gore.
import * as THREE from 'three';
import { Part, Limb2, addEye, toonDouble } from '../toon.js';

export function buildGranny() {
  const root = new THREE.Group();
  const DRESS = '#5b2d8c';
  const DRESS_D = '#47216f';
  const BLOOM = '#cdb7ea';
  const SKIN = '#f3d2ba';
  const HAIR = '#e9e9f2';
  const SHOE = '#6b4226';

  const rig = new THREE.Group(); // whole body: flips in the air, squashes on landing
  root.add(rig);
  const pivot = new THREE.Group(); // rotation centre for the slingshot flip
  pivot.position.set(0, 1.3, 0);
  rig.add(pivot);
  const bodyG = new THREE.Group();
  bodyG.position.set(0, -1.3, 0);
  pivot.add(bodyG);

  // ── arched torso, belly to the sky. Hips lead (+z), shoulders trail (-z) ──
  const tp = new Part();
  tp.sph(0.5, DRESS, { p: [0, 1.5, 0.55], s: [1.05, 0.8, 0.95] }); // hips
  tp.sph(0.5, DRESS, { p: [0, 1.72, 0.1], s: [1.0, 0.78, 1.0] }); // belly (top of the arch)
  tp.sph(0.48, DRESS, { p: [0, 1.6, -0.38], s: [1.02, 0.8, 0.95] }); // chest
  tp.sph(0.36, DRESS_D, { p: [0, 1.33, -0.74], s: [1.3, 0.75, 0.8] }); // shoulders
  tp.sph(0.07, '#e9d9ff', { p: [0, 2.0, -0.32] }); // buttons up the front
  tp.sph(0.07, '#e9d9ff', { p: [0, 2.11, 0.0] });
  tp.sph(0.07, '#e9d9ff', { p: [0, 2.07, 0.3] });
  tp.torus(0.22, 0.07, '#ffffff', { p: [0, 1.22, -0.86], r: [-0.9 + Math.PI / 2, 0, 0] }, 12, 5); // lace collar
  tp.cyl(0.13, 0.15, 0.3, SKIN, { p: [0, 1.12, -0.95], r: [-0.9, 0, 0] }, 8); // neck dropping back
  const torso = tp.build();
  bodyG.add(torso);

  // long skirt: hangs straight down from the hips like a curtain, with a lace hem
  const sk = new Part();
  sk.add(new THREE.CylinderGeometry(0.56, 0.86, 1.0, 14, 1, true, Math.PI * 0.5, Math.PI), DRESS, { p: [0, -0.5, 0] });
  sk.add(new THREE.CylinderGeometry(0.86, 0.9, 0.12, 14, 1, true, Math.PI * 0.5, Math.PI), '#ffffff', { p: [0, -1.04, 0] });
  sk.add(new THREE.CylinderGeometry(0.52, 0.8, 0.95, 14, 1, true, Math.PI * 1.5, Math.PI), DRESS_D, { p: [0, -0.48, 0.08] });
  const skirt = sk.build(toonDouble());
  skirt.position.set(0, 1.5, 0.5);
  bodyG.add(skirt);

  // ── head: hangs upside down between the arms, facing backwards ──
  const headG = new THREE.Group();
  headG.position.set(0, 0.86, -1.18);
  bodyG.add(headG);
  const head = new THREE.Group();
  head.rotation.set(Math.PI, 0, 0); // crown to the floor; face now looks toward -z (the chase camera)
  headG.add(head);
  const hp = new Part();
  hp.sph(0.4, SKIN, { s: [1, 1.05, 1] });
  hp.sph(0.41, HAIR, { p: [0, 0.1, -0.08], s: [1.02, 0.95, 0.98] });
  hp.sph(0.4, SKIN, { p: [0, -0.04, 0.07], s: [0.92, 0.98, 0.95] });
  hp.sph(0.24, HAIR, { p: [0, 0.52, -0.06], s: [1, 1.25, 1] }); // tall bun (points at the road)
  hp.sph(0.15, HAIR, { p: [0, 0.8, -0.06] });
  hp.cyl(0.02, 0.02, 0.5, '#c9a227', { p: [0.1, 0.62, -0.06], r: [0, 0, 0.9] }, 5); // hairpin
  hp.sph(0.07, '#eab69a', { p: [0, -0.06, 0.45] }); // nose
  hp.sph(0.1, SKIN, { p: [0.4, 0, 0.02], s: [0.5, 1, 0.8] });
  hp.sph(0.1, SKIN, { p: [-0.4, 0, 0.02], s: [0.5, 1, 0.8] });
  addEye(hp, 0.16, 0.06, 0.36, 0.075, { iris: '#2c2233', pupil: 0.6 });
  addEye(hp, -0.16, 0.06, 0.36, 0.075, { iris: '#2c2233', pupil: 0.6 });
  // round gold spectacles
  hp.torus(0.13, 0.02, '#d9b23c', { p: [0.16, 0.06, 0.42] }, 14, 5);
  hp.torus(0.13, 0.02, '#d9b23c', { p: [-0.16, 0.06, 0.42] }, 14, 5);
  hp.box(0.08, 0.02, 0.02, '#d9b23c', { p: [0, 0.07, 0.43] });
  hp.box(0.14, 0.03, 0.03, HAIR, { p: [0.16, 0.24, 0.39], r: [0, 0, 0.12] }); // kindly raised brows
  hp.box(0.14, 0.03, 0.03, HAIR, { p: [-0.16, 0.24, 0.39], r: [0, 0, -0.12] });
  hp.sph(0.08, '#f4a9a9', { p: [0.26, -0.12, 0.3], s: [1, 0.6, 0.5] });
  hp.sph(0.08, '#f4a9a9', { p: [-0.26, -0.12, 0.3], s: [1, 0.6, 0.5] });
  hp.torus(0.11, 0.02, '#a8475a', { p: [0, -0.16, 0.38], r: [0.1, 0, Math.PI] }, 10, 4, Math.PI); // serene smile
  head.add(hp.build());
  // pearls: gravity pulls them toward her chin while she is upside down
  const pp = new Part();
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * Math.PI * 2;
    pp.sph(0.055, '#fffdf5', { p: [Math.cos(a) * 0.27, 0, Math.sin(a) * 0.24] });
  }
  const pearls = pp.build();
  pearls.position.set(0, 0.28, 0.1);
  pearls.rotation.x = 0.5;
  headG.add(pearls);

  // ── limbs ──
  const shoe = (pb, len) => {
    pb.box(0.24, 0.18, 0.5, SHOE, { p: [0, -len - 0.06, 0.1] });
    pb.box(0.2, 0.14, 0.14, '#4a2c18', { p: [0, -len - 0.12, -0.12] });
    pb.torus(0.14, 0.05, '#ffffff', { p: [0, -len + 0.14, 0], r: [Math.PI / 2, 0, 0] }, 8, 4); // frilly bloomer cuff
  };
  const hand = (pb, len) => {
    pb.sph(0.13, SKIN, { p: [0, -len - 0.05, 0.02], s: [1.1, 0.6, 1.4] });
    pb.torus(0.11, 0.035, '#ffffff', { p: [0, -len + 0.08, 0], r: [Math.PI / 2, 0, 0] }, 8, 4); // cuff
  };
  const legL = new Limb2(bodyG, 0.9, 0.9, 0.2, 0.15, BLOOM, BLOOM, shoe);
  const legR = new Limb2(bodyG, 0.9, 0.9, 0.2, 0.15, BLOOM, BLOOM, shoe);
  const armL = new Limb2(bodyG, 0.78, 0.78, 0.13, 0.11, DRESS_D, DRESS, hand);
  const armR = new Limb2(bodyG, 0.78, 0.78, 0.13, 0.11, DRESS_D, DRESS, hand);

  let phase = 0;
  let crouch = 0;
  let flight = 0;
  let land = 0;
  let wasAir = false;
  let flip = 0;

  function update(st) {
    const t = st.t;
    const windup = st.skillPhase === 'windup';
    const air = st.skillPhase === 'air' || (st.airborne && st.air > 0.4);
    crouch += ((windup ? 1 : 0) - crouch) * Math.min(1, st.dt * 22);
    flight += ((air ? 1 : 0) - flight) * Math.min(1, st.dt * 12);
    if (wasAir && !air) land = 1;
    wasAir = air;
    land = Math.max(0, land - st.dt * 4);

    // scuttle: unnaturally quick, diagonal pairs
    const rate = 4 + st.speedN * 30;
    phase += rate * st.dt * (1 - flight);
    const stride = 0.12 + Math.min(1, st.speedN) * 0.42;
    const lift = 0.08 + Math.min(1, st.speedN) * 0.26;
    const bob = Math.sin(phase * 2) * 0.045 * (1 - flight);
    const sway = Math.sin(phase) * 0.05 * (1 - flight);

    // spring: coil down, then stretch long in the air and tumble once backwards
    const sy = 1 - crouch * 0.38 + flight * 0.16 - land * 0.22;
    const sz = 1 + crouch * 0.12 - flight * 0.06 + land * 0.12;
    rig.scale.set(1 + crouch * 0.1 + land * 0.1, sy, sz);
    if (st.skillPhase === 'air') flip = Math.min(1, flip + st.dt / 1.15);
    else flip = 0;
    const e = flip * flip * (3 - 2 * flip);
    pivot.rotation.x = -e * Math.PI * 2;
    bodyG.rotation.z = sway + st.steer * 0.16;
    bodyG.position.y = -1.3 + bob;
    torso.scale.y = 1 + crouch * 0.1;

    // head stays eerily level while everything else scrabbles
    headG.rotation.z = -bodyG.rotation.z + Math.sin(t * 0.9) * 0.09;
    headG.rotation.y = st.lookBack * 0.5 + Math.sin(t * 0.6) * 0.08;
    headG.position.y = 0.86 - bob;
    pearls.rotation.z = Math.sin(phase) * 0.12;
    pearls.position.y = 0.28 + Math.abs(Math.sin(phase * 2)) * 0.03;
    skirt.rotation.x = -0.12 - st.speedN * 0.22 + Math.sin(phase * 2) * 0.05;
    skirt.scale.set(1 + Math.sin(phase * 2 + 1) * 0.03, 1 - flight * 0.25, 1);

    // limb targets
    const tuck = flight;
    const gy = -bob; // feet/hands stay planted while the body bobs
    const foot = (side, off) => {
      const ph = phase + off;
      const z = 1.35 + Math.cos(ph) * stride;
      const y = 0.16 + Math.max(0, Math.sin(ph)) * lift;
      return [side * 0.48, (y + gy) * (1 - tuck) + 0.75 * tuck, z * (1 - tuck) + 1.0 * tuck];
    };
    const palm = (side, off) => {
      const ph = phase + off;
      const z = -1.25 + Math.cos(ph) * stride * 0.85;
      const y = 0.1 + Math.max(0, Math.sin(ph)) * lift * 0.9;
      return [side * 0.62, (y + gy) * (1 - tuck) + 0.7 * tuck, z * (1 - tuck) - 1.05 * tuck];
    };
    const fl = foot(1, 0);
    const fr = foot(-1, Math.PI);
    const pl = palm(1, Math.PI);
    const pr = palm(-1, 0);
    legL.solve(0.34, 1.45, 0.62, fl[0], fl[1], fl[2], 0.5, 1, 0.9);
    legR.solve(-0.34, 1.45, 0.62, fr[0], fr[1], fr[2], -0.5, 1, 0.9);
    armL.solve(0.46, 1.3, -0.76, pl[0], pl[1], pl[2], 1, 0.6, -0.9);
    armR.solve(-0.46, 1.3, -0.76, pr[0], pr[1], pr[2], -1, 0.6, -0.9);
  }

  return { root, update, height: 2.4, cam: { h: -0.5, d: -0.8 } };
}
