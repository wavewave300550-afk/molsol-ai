import { Entity, Vector3 } from "@minecraft/server";
import { DW01 as C } from "../config/dw01";
import { defineSpell } from "../core/registry";
import { damage, knockback } from "../lib/combat";
import { burst, particle, ring, sound } from "../lib/fx";
import { Actor, secs } from "../lib/scene";
import { focus, groundBelow, hostiles, isAlive } from "../lib/targeting";
import { LIGHT, blocksFor } from "../lib/tempblocks";
import { add, mul, polar, up, yawOf, sub } from "../lib/vec";

// Seraphim animation states (tools/assets/dw_seraph.py STATES)
const S = { hidden: 0, arrive: 1, veiled: 2, unfurl: 3, open: 4, chant1: 5, chant2: 6, chant3: 7, verdict: 8, depart: 9 };

/**
 * DW01 - Seraphic Litany: The Sixfold Sanctus.
 * A six-winged Seraphim is written into the sky, unveils itself wing pair by wing pair and
 * chants three times.  Each chant drops inscription seals on the nearest enemies; a seal becomes
 * a column of judgment.  Enemies struck by all three receive the verdict.
 */
export default defineSpell("dw01", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, 12);
  const hover = up(add(center, mul(aim.forward, C.hoverBack)), C.hoverHeight);
  const faceCaster = yawOf(sub(caster.location, hover));
  const lights = blocksFor(scene);
  const hits = new Map<string, { e: Entity; n: number; last: number; mark?: Actor }>();

  // -- manifestation: inscription circles on the ground and behind the Seraphim
  const ground = scene.spawn("dw_circle", center, { size: C.radius / 2.6, state: 1 });
  const sky = scene.spawn("dw_circle", up(hover, 13), { size: 3.2, state: 1 });
  sound(dim, "dw_circle", center, 1.0);
  scene.at(8, () => { ground.state(2); sky.state(2); });
  const seraph = scene.spawn("seraph", hover, { yaw: faceCaster, state: S.arrive });
  sound(dim, "dw_seraph_arrive", hover, 1.2);
  scene.every(4, () => particle(dim, "dw_mote", up(hover, 4)), 0, secs(8));
  scene.at(8, () => burst(dim, "dw_glyph_rise", up(center, 0.5), C.radius * 0.5, 6));
  lights.place(up(center, 2), LIGHT);

  const tUnfurl = secs(1.5);
  scene.at(tUnfurl, () => { seraph.state(S.unfurl); sound(dim, "dw_unfurl", hover, 1.0); burst(dim, "dw_feather", up(hover, 5), 5, 8); });

  // -- three chants, each a different gesture, vowel and column colour
  const chantAt = [tUnfurl + secs(1.3), tUnfurl + secs(2.7), tUnfurl + secs(4.1)];
  const gestureLead = [18, 19, 19]; // ticks into each chant animation where the gesture peaks
  chantAt.forEach((t0, i) => {
    scene.at(t0, () => {
      seraph.state(S.chant1 + i).skin(1); // feathers light up with inscriptions
      sound(dim, `dw_chant${i + 1}`, hover, 1.3);
      ring(dim, "dw_glyph_rise", up(hover, 4), 5, 8, i * 20);
    });
    scene.at(t0 + gestureLead[i] - C.warnTicks + 8, () => judge(i));
  });

  function pickTargets(): { loc: Vector3; e?: Entity }[] {
    const found = hostiles(dim, center, C.radius, caster, C.maxTargets);
    if (found.length) return found.map((e) => ({ loc: groundBelow(dim, e.location), e }));
    // no enemies: the litany still falls in a ring so the spell reads clearly
    return [0, 1, 2].map((k) => ({ loc: polar(center, 4, k * 120 + 30) }));
  }

  function judge(i: number): void {
    for (const t of pickTargets()) {
      const size = (C.columnRadius / 1.3) * (1 + i * 0.12);
      const warn = scene.spawn("telegraph", t.loc, { kind: 0, size: C.columnRadius * (1 + i * 0.1), state: 1 });
      let at = t.loc;
      // the seal tracks its enemy until just before it lands
      scene.every(1, () => {
        if (t.e && isAlive(t.e)) { at = groundBelow(dim, t.e.location); warn.move(at); }
      }, scene.tick, scene.tick + C.warnTicks - 4);
      scene.after(C.warnTicks - 6, () => {
        const col = scene.spawn("dw_column", at, { kind: i === 1 ? 1 : 0, size, state: 1 });
        sound(dim, "dw_column", at, 1.0, 0.95 + i * 0.08);
        scene.after(10, () => col.state(2));
        scene.after(22, () => col.state(3));
        scene.after(36, () => scene.despawn(col));
      });
      scene.after(C.warnTicks, () => {
        warn.state(3);
        scene.after(8, () => scene.despawn(warn));
        strike(at, i);
      });
    }
  }

  function strike(at: Vector3, i: number): void {
    particle(dim, "dw_ring", up(at, 0.2));
    particle(dim, "dw_pillar_burst", up(at, 0.3));
    particle(dim, "dw_spark", up(at, 1.0));
    particle(dim, "fx_flash", up(at, 1.5));
    for (const e of hostiles(dim, at, C.columnRadius * (1 + i * 0.1), caster)) {
      let h = hits.get(e.id);
      if (!h) { h = { e, n: 0, last: -1 }; hits.set(e.id, h); }
      if (h.last >= i) continue; // overlapping columns: one judgment per enemy per chant
      if (!damage(e, C.chantDamage[i], caster)) continue;
      h.last = i;
      h.n++;
      if (isAlive(e)) {
        if (!h.mark || !h.mark.valid) {
          h.mark = scene.spawn("dw_mark", up(e.location, 2.4), { state: 1 });
          scene.follow(h.mark, e, 2.4);
          sound(dim, "dw_mark", e.location, 0.7, 1 + i * 0.12);
        }
        h.mark.skin(Math.min(2, h.n - 1));
      }
    }
  }

  // -- verdict: everything judged three times receives the finishing blow
  const tVerdict = chantAt[2] + secs(1.75);
  scene.at(tVerdict, () => {
    seraph.state(S.verdict);
    const judged = [...hits.values()].filter((h) => h.n >= 3 && isAlive(h.e));
    sound(dim, "dw_verdict", judged.length ? judged[0].e.location : center, 1.4);
    scene.after(9, () => {
      const spots = judged.length ? judged.map((h) => groundBelow(dim, h.e.location)) : [center];
      const sentenced = new Set<string>();
      for (const at of spots) {
        const col = scene.spawn("dw_column", at, { kind: 2, size: 2.2, state: 1 });
        scene.after(10, () => col.state(2));
        scene.after(24, () => col.state(3));
        scene.after(38, () => scene.despawn(col));
        scene.after(6, () => {
          particle(dim, "dw_ring", up(at, 0.2));
          particle(dim, "fx_shock", up(at, 0.3));
          burst(dim, "dw_spark", up(at, 1.2), 1.5, 3);
          ring(dim, "dw_glyph_fall", up(at, 6), 2.5, 6);
          for (const e of hostiles(dim, at, C.verdictRadius, caster)) {
            const h = hits.get(e.id);
            if (h && h.n >= 3 && !sentenced.has(e.id)) { sentenced.add(e.id); damage(e, C.verdictBonus, caster); }
            knockback(e, at, C.verdictKnockback, 0.5);
          }
        });
      }
      for (const h of hits.values()) if (h.mark?.valid) { h.mark.state(3); const m = h.mark; scene.after(8, () => scene.despawn(m)); }
    });
  });

  // -- departure: the wings veil again and the Seraphim is unwritten
  const tDepart = tVerdict + secs(1.5);
  scene.at(tDepart, () => {
    seraph.state(S.depart).skin(0);
    ground.state(3); sky.state(3);
    sound(dim, "dw_depart", hover, 1.0);
    ring(dim, "dw_feather", up(hover, 5), 4, 8);
  });
  scene.at(tDepart + secs(1.2), () => burst(dim, "dw_glyph_rise", up(hover, 8), 3, 8));
  scene.endAt(tDepart + secs(1.7));
});
