import { Entity, Player, Vector3 } from "@minecraft/server";
import { DN04 as C } from "../config/dn04";
import { defineSpell } from "../core/registry";
import { addWard, damage, effect, heal, shove } from "../lib/combat";
import { burst, particle, ring, sound } from "../lib/fx";
import { Actor, secs } from "../lib/scene";
import { allies, groundBelow, hostiles, isAlive } from "../lib/targeting";
import { add, bezier, distXZ, easeOut, flat, lerp, mul, norm, right, smooth, sub, up, yawOf } from "../lib/vec";

// Animation states (tools/assets/dn_lullaby.py TAP_STATES / RIB_STATES / WAVE_STATES)
const T = { hidden: 0, unfurl: 1, lullaby: 2, dissonance: 3, dual: 4, scream: 5, unravel: 6 };
const R = { hidden: 0, travel: 1, wrap: 2, orbit: 3, recoil: 4, unwind: 5 };
const W = { hidden: 0, scream: 1, faint: 2, fade: 3 };
// Animation lengths in ticks (UNFURL, DISSONANCE, SCREAM, UNRAVEL, WRAP, RECOIL, UNWIND, FADE in dn_lullaby.py)
const L = { unfurl: 30, dissonance: 32, scream: 18, unravel: 36, wrap: 16, recoil: 12, unwind: 20, fade: 7 };

interface Wrap { p: Player; rib: Actor; from: Vector3; t0: number; wrapped: boolean; busyUntil: number }
interface Dizzy { e: Entity; until: number; yaw: number; dir: number; t0: number }

/**
 * DN04 - Lullaby and Scream.
 * A hanging musical tapestry unfurls from the Grimoire above the caster and plays an original
 * lullaby.  Dream ribbons spool out and cocoon every nearby ally (periodic healing + real damage
 * resistance).  Dissonance tears an indigo nightmare layer through the weave; from then on the
 * tapestry shrieks once per phrase and a waveform ring expands from it, damaging, slowing,
 * weakening and spinning every enemy the front reaches.  Ribbons flinch as the scream passes
 * their ally, and the ally is soothed instead of hurt.  Finally both halves wind back into the book.
 */
export default defineSpell("dn04", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  let facing = norm(flat(aim.forward));
  const hoverTarget = (): Vector3 => up(add(caster.location, mul(facing, C.hoverForward)), C.hoverHeight);
  const bookAt = (): Vector3 => up(add(caster.location, mul(facing, 0.6)), 1.1);

  // ---- phrase grid (every musical / gameplay event lands on a phrase or bar downbeat)
  const P = C.phraseTicks;
  const tLull = L.unfurl;
  const phrases = Math.max(C.lullabyPhrases + C.dissonancePhrases + 1, Math.floor((secs(C.activeSeconds) - tLull) / P));
  const tDis = tLull + C.lullabyPhrases * P;
  const tDual = tDis + C.dissonancePhrases * P;
  const tUnravel = tLull + phrases * P;
  const tEnd = tUnravel + L.unravel + 4;

  // ---- the tapestry rises out of the book and unfolds
  const book0 = bookAt();
  let hover = book0;
  const tap = scene.spawn("dn_lull_tapestry", book0, { yaw: yawOf(mul(facing, -1)), state: T.unfurl, skin: 0 });
  sound(dim, "dn_lull_open", book0, 1.0);
  burst(dim, "dn_lull_mote", up(book0, 0.4), 0.6, 4);
  scene.at(14, () => burst(dim, "dn_lull_note", up(hover, 2.2), 1.5, 3));

  scene.every(1, () => {
    const t = scene.tick;
    const view = caster.getViewDirection();
    const want = norm(flat(view));
    if (Math.hypot(want.x, want.z) > 0.1) facing = norm(lerp(facing, want, 0.05));
    if (t < tLull) {
      const f = smooth(t / tLull);
      const goal = hoverTarget();
      hover = bezier(book0, up(lerp(book0, goal, 0.5), 1.6), goal, f);
    } else if (t < tUnravel + 10) {
      hover = lerp(hover, hoverTarget(), C.followLerp);
    } else {
      hover = lerp(hover, bookAt(), 0.14); // both halves wind back into the book
    }
    tap.move(hover, yawOf(mul(facing, -1)));
    if (tele?.valid) tele.move(groundBelow(dim, hover));
    updateRibbons(t);
    updateDizzy(t);
  }, 0, tEnd);

  // ---- music: one clip per phrase, chosen by phase
  for (let k = 0; k < phrases; k++) {
    const t0 = tLull + k * P;
    const kind = k < C.lullabyPhrases ? "lull" : k < C.lullabyPhrases + C.dissonancePhrases ? "dis" : "dual";
    scene.at(t0, () => sound(dim, `dn_lull_${kind}${(k % 2) + 1}`, hover, 1.0));
    if (kind === "dual") {
      scene.at(t0, () => {
        tap.state(T.scream);
        sound(dim, "dn_lull_scream", hover, 1.2);
        burst(dim, "dn_lull_thread", up(hover, 2.2), 1.2, 3);
      });
      scene.at(t0 + C.screamLead, () => launchWave(false));
      scene.at(t0 + L.scream, () => tap.state(T.dual));
    }
  }
  scene.at(tLull, () => tap.state(T.lullaby));
  scene.every(10, () => particle(dim, "dn_lull_note", up(hover, 2.4)), tLull, tDual);

  // ---- dissonance creeps in: the stave tears, the nightmare weave grows through, eyes open
  let tele: Actor | undefined;
  scene.at(tDis, () => {
    tap.state(T.dissonance);
    sound(dim, "dn_lull_tear", hover, 1.1);
    tele = scene.spawn("telegraph", groundBelow(dim, hover), { kind: 1, size: C.waveRadius, state: 4 });
  });
  scene.at(tDis + 6, () => tap.skin(1));
  scene.at(tDis + P / 2, () => { sound(dim, "dn_lull_faint", hover, 0.9); launchWave(true); });
  scene.at(tDis + L.dissonance, () => { tap.state(T.dual); tele?.state(2); });
  scene.every(8, () => particle(dim, "dn_lull_thread", up(hover, 1.0)), tDis, tUnravel);

  // ---- dream half: ribbons wrap allies (real resistance + periodic heals)
  const wraps = new Map<string, Wrap>();
  const lastWardFx = new Map<string, number>();
  addWard({
    scene,
    factor: C.wardFactor,
    protects: (e) => { const w = wraps.get(e.id); return !!w && w.wrapped; },
    onAbsorb: (_amount, _attacker, victim) => {
      const last = lastWardFx.get(victim.id) ?? -99;
      if (scene.tick - last < 8 || !victim.isValid) return;
      lastWardFx.set(victim.id, scene.tick);
      particle(dim, "dn_lull_ward", up(victim.location, 1.0));
      sound(dim, "dn_lull_ward", victim.location, 0.8);
      const w = wraps.get(victim.id);
      if (w && scene.tick >= w.busyUntil) recoil(w);
    },
  });

  function checkAllies(): void {
    const near = allies(dim, caster.location, C.allyRadius, caster);
    if (!near.some((p) => p.id === caster.id) && isAlive(caster)) near.unshift(caster);
    for (const p of near) {
      if (wraps.has(p.id) || wraps.size >= C.maxAllies) continue;
      const from = up(hover, 1.6);
      const rib = scene.spawn("dn_lull_ribbon", from, { state: R.travel });
      if (!rib.valid) continue;
      wraps.set(p.id, { p, rib, from, t0: scene.tick, wrapped: false, busyUntil: 0 });
      sound(dim, "dn_lull_ribbon", from, 0.9, 0.95 + wraps.size * 0.05);
    }
    for (const w of [...wraps.values()]) {
      if (!isAlive(w.p) || w.p.dimension.id !== dim.id || distXZ(w.p.location, caster.location) > C.ribbonLoseRadius) release(w);
    }
  }
  scene.every(C.allyCheckEvery, checkAllies, 12, tUnravel);

  function updateRibbons(t: number): void {
    for (const w of wraps.values()) {
      if (!w.rib.valid) continue;
      if (!w.p.isValid) continue;
      const target = w.p.location;
      if (!w.wrapped) {
        const f = (t - w.t0) / C.ribbonTravelTicks;
        const pos = bezier(w.from, up(lerp(w.from, target, 0.5), 2.5), target, easeOut(Math.min(1, f)));
        w.rib.move(pos, yawOf(sub(target, w.from)));
        if (f >= 1) {
          w.wrapped = true;
          w.busyUntil = t + L.wrap;
          w.rib.state(R.wrap);
          sound(dim, "dn_lull_calm", target, 0.7, 1.1);
          ring(dim, "dn_lull_mote", up(target, 0.8), 0.8, 4);
          const rib = w.rib;
          scene.after(L.wrap, () => { if (wraps.get(w.p.id) === w) rib.state(R.orbit); });
        }
      } else {
        w.rib.move(target);
      }
    }
  }

  function recoil(w: Wrap): void {
    w.busyUntil = scene.tick + L.recoil;
    w.rib.state(R.recoil);
    const rib = w.rib;
    scene.after(L.recoil, () => { if (wraps.get(w.p.id) === w) rib.state(R.orbit); });
  }

  function release(w: Wrap): void {
    wraps.delete(w.p.id);
    const rib = w.rib;
    rib.state(R.unwind);
    scene.after(L.unwind, () => scene.despawn(rib));
  }

  scene.every(C.healEvery, (e) => {
    const pitch = [1.0, 1.12, 1.26][Math.floor(e / C.healEvery) % 3];
    for (const w of wraps.values()) {
      if (!w.wrapped || !isAlive(w.p)) continue;
      heal(w.p, C.healAmount);
      particle(dim, "dn_lull_heal", up(w.p.location, 0.2));
      sound(dim, "dn_lull_heal", w.p.location, 0.8, pitch);
    }
  }, tLull + C.healOffset, tUnravel);
  scene.every(16, () => {
    for (const w of wraps.values()) if (w.wrapped && w.p.isValid) particle(dim, "dn_lull_mote", up(w.p.location, 1.2));
  }, tLull, tUnravel);

  // ---- nightmare half: radius-synchronised scream waves
  const dizzy = new Map<string, Dizzy>();

  function launchWave(faint: boolean): void {
    const center = groundBelow(dim, hover);
    const maxR = C.waveRadius * (faint ? C.faintRadius : 1);
    const dmg = C.waveDamage * (faint ? C.faintDamage : 1);
    const wv = scene.spawn("dn_lull_wave", center, { size: C.waveStartRadius, state: faint ? W.faint : W.scream });
    if (!faint) particle(dim, "dn_lull_scream_ring", up(center, 0.15));
    const hit = new Set<string>();
    const soothed = new Set<string>();
    const t0 = scene.tick;
    scene.span(t0, t0 + C.waveTicks, (p, el) => {
      const r = C.waveStartRadius + (maxR - C.waveStartRadius) * easeOut(p);
      wv.size(r);
      if (el % 3 === 0) ring(dim, "dn_lull_front", up(center, 1.2), r, faint ? 4 : 7, el * 17);
      for (const e of hostiles(dim, center, r + 1.5, caster, C.maxTargets)) {
        if (hit.has(e.id) || distXZ(e.location, center) > r) continue;
        hit.add(e.id);
        strike(e, center, dmg, faint);
      }
      // where the front passes an ally the nightmare is soothed: the ribbons flinch, the ally is untouched
      for (const w of wraps.values()) {
        if (!w.wrapped || soothed.has(w.p.id) || !w.p.isValid || distXZ(w.p.location, center) > r) continue;
        soothed.add(w.p.id);
        recoil(w);
        particle(dim, "dn_lull_calm", up(w.p.location, 1.2));
        if (!faint) sound(dim, "dn_lull_calm", w.p.location, 0.6);
      }
    });
    scene.at(t0 + C.waveTicks, () => wv.state(W.fade));
    scene.at(t0 + C.waveTicks + L.fade, () => scene.despawn(wv));
  }

  function strike(e: Entity, center: Vector3, dmg: number, faint: boolean): void {
    damage(e, dmg, caster);
    particle(dim, "dn_lull_eye", up(e.location, 1.6));
    sound(dim, "dn_lull_hit", e.location, faint ? 0.6 : 0.9);
    if (!isAlive(e)) return;
    effect(e, "slowness", C.slowTicks, faint ? 0 : C.slowAmp);
    effect(e, "weakness", C.weaknessTicks, C.weaknessAmp);
    // disorientation: stagger sideways and spin the enemy's facing so it loses its target
    const out = norm(flat(sub(e.location, center)));
    const dir = (e.id.charCodeAt(e.id.length - 1) ?? 0) % 2 === 0 ? 1 : -1;
    shove(e, add(mul(right(out), dir), mul(out, 0.5)), C.disorientShove * (faint ? 0.6 : 1), 0.12);
    dizzy.set(e.id, { e, until: scene.tick + C.disorientTicks, yaw: yawOf(out), dir, t0: scene.tick });
  }

  function updateDizzy(t: number): void {
    for (const [id, d] of dizzy) {
      if (t > d.until || !isAlive(d.e)) { dizzy.delete(id); continue; }
      try { d.e.setRotation({ x: 0, y: d.yaw + d.dir * C.disorientSpin * (t - d.t0) }); } catch { /* immovable */ }
    }
  }

  // ---- unravel: both halves wind back into the book
  scene.at(tUnravel, () => {
    tap.state(T.unravel);
    sound(dim, "dn_lull_unravel", hover, 1.0);
    particle(dim, "dn_lull_unravel", up(hover, 2.2));
    if (tele?.valid) { tele.state(3); const tl = tele; scene.after(8, () => scene.despawn(tl)); }
    for (const w of [...wraps.values()]) release(w);
  });
  scene.at(tUnravel + 14, () => tap.skin(0));
  scene.at(tUnravel + L.unravel - 6, () => burst(dim, "dn_lull_mote", bookAt(), 0.5, 4));
  scene.endAt(tEnd);
});
