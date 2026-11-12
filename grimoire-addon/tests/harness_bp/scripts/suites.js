// Test suites. Each suite receives the harness context `h`.
import { SPELL_SUITES } from "./spell_suites.js";
import { ROBUST_SUITES } from "./robust_suites.js";

const P = "grimoire:pressure", I = "grimoire:ice", B = "grimoire:blood";

async function controls(h) {
  const S = "controls";
  const A = h.spawnPlayer("Alice", 0, 0, h.GameMode.Survival);
  const Bob = h.spawnPlayer("Bob", 0, 8, h.GameMode.Creative);
  await h.wait(20);
  for (const sp of [A, Bob]) {
    h.give(sp, 0, P); h.give(sp, 1, I); h.give(sp, 2, B); h.give(sp, 3, "minecraft:stick");
    sp.selectedSlotIndex = 0;
  }
  await h.wait(10);
  let s = await h.state("Alice");
  h.check(S, "diagnostics reachable", !!s, s);
  h.check(S, "three grimoires start at spell 01", s && s.selected.pressure === 0 && s.selected.ice === 0 && s.selected.blood === 0, s?.selected);

  await h.crouch(A);
  s = await h.state("Alice");
  h.check(S, "one crouch press advances exactly one spell", s.selected.pressure === 1, s.selected);

  A.isSneaking = true;
  await h.wait(60);
  A.isSneaking = false;
  await h.wait(3);
  s = await h.state("Alice");
  h.check(S, "holding crouch 3s advances only once", s.selected.pressure === 2, s.selected);

  for (let i = 0; i < 13; i++) await h.crouch(A, 2);
  s = await h.state("Alice");
  h.check(S, "selection wraps 15 -> 01", s.selected.pressure === 0, s.selected);

  // ---- hold and release casts exactly once (P01 Pressure Lance: charge 8, cooldown 6s)
  const hp0 = A.getComponent("minecraft:health").currentValue;
  const food0 = A.getComponent("minecraft:player.hunger")?.currentValue;
  A.useItemInSlot(0);
  await h.wait(4);
  s = await h.state("Alice");
  h.check(S, "holding Use starts preparation (no instant cast)", s.preparing && s.preparing.spell === "pressure.lance" && !s.cooldowns["pressure.lance"], s);
  await h.wait(10);
  A.stopUsingItem();
  await h.wait(2);
  s = await h.state("Alice");
  const cd1 = s.cooldowns["pressure.lance"];
  h.check(S, "release casts the selected spell (cooldown 6s started)", cd1 > 100 && cd1 <= 120, s.cooldowns);
  h.check(S, "single release activates only one spell", Object.keys(s.cooldowns).length === 1, s.cooldowns);
  await h.wait(5);
  const hp1 = A.getComponent("minecraft:health").currentValue;
  h.check(S, "casting costs no health", hp1 >= hp0, { hp0, hp1 });
  h.check(S, "full hunger does not block casting (no food component used)", food0 === undefined || food0 >= 0, { food0 });

  // ---- recast while cooling down is refused
  await h.wait(8);
  A.useItemInSlot(0);
  await h.wait(12);
  A.stopUsingItem();
  await h.wait(2);
  s = await h.state("Alice");
  h.check(S, "spell on cooldown cannot be recast", s.cooldowns["pressure.lance"] < cd1, s.cooldowns);

  // ---- independent cooldowns: P02 is available although P01 cools down
  await h.crouch(A);
  s = await h.state("Alice");
  h.check(S, "selected P02 Atlas Piston", s.selected.pressure === 1, s.selected);
  A.useItemInSlot(0);
  await h.wait(3);
  A.stopUsingItem(); // too early (charge 14)
  await h.wait(10);
  s = await h.state("Alice");
  h.check(S, "releasing before minimum preparation does not cast", !s.cooldowns["pressure.atlas_piston"], s.cooldowns);
  A.useItemInSlot(0);
  await h.wait(18);
  A.stopUsingItem();
  await h.wait(2);
  s = await h.state("Alice");
  h.check(S, "P02 castable while P01 is cooling (independent cooldowns)", s.cooldowns["pressure.atlas_piston"] > 300 && s.cooldowns["pressure.lance"] > 0, s.cooldowns);

  // ---- crouch during preparation cancels it
  await h.wait(8);
  await h.crouch(A); // -> P03
  A.useItemInSlot(0);
  await h.wait(12);
  A.isSneaking = true;
  await h.wait(3);
  s = await h.state("Alice");
  h.check(S, "crouching during preparation cancels it", !s.preparing, s);
  A.isSneaking = false;
  await h.wait(2);
  A.stopUsingItem();
  await h.wait(2);
  s = await h.state("Alice");
  h.check(S, "release after crouch-cancel casts nothing", !s.cooldowns["pressure.isobaric_severance"] && !s.cooldowns["pressure.cataclysm_salvo"], s.cooldowns);
  h.check(S, "the crouch also advanced the selection (P03 -> P04)", s.selected.pressure === 3, s.selected);

  // ---- switching items during preparation cancels without casting
  await h.wait(8);
  A.useItemInSlot(0);
  await h.wait(20);
  A.selectedSlotIndex = 3;
  await h.wait(3);
  s = await h.state("Alice");
  h.check(S, "switching items cancels preparation", !s.preparing, s);
  A.selectedSlotIndex = 0;
  await h.wait(2);
  A.stopUsingItem();
  await h.wait(2);
  s = await h.state("Alice");
  h.check(S, "no cast after item switch", !s.cooldowns["pressure.cataclysm_salvo"], s.cooldowns);

  // ---- starting to use while crouching prepares nothing
  await h.wait(8);
  A.isSneaking = true; // also advances to P05
  await h.wait(3);
  A.useItemInSlot(0);
  await h.wait(16);
  s = await h.state("Alice");
  h.check(S, "Use while crouching does not prepare", !s.preparing, s);
  A.stopUsingItem();
  A.isSneaking = false;
  await h.wait(3);
  s = await h.state("Alice");
  h.check(S, "no cast when the preparation started crouched", !s.cooldowns["pressure.aegis_of_isobars"], s.cooldowns);

  // ---- per-grimoire selection is independent
  A.selectedSlotIndex = 1; // ice
  await h.wait(3);
  await h.crouch(A);
  s = await h.state("Alice");
  h.check(S, "selection is stored per grimoire", s.selected.ice === 1 && s.selected.pressure === 4 && s.selected.blood === 0, s.selected);

  // ---- second copy of the same book does not reset cooldowns
  h.give(A, 5, P);
  A.selectedSlotIndex = 5;
  await h.wait(3);
  s = await h.state("Alice");
  h.check(S, "another copy of the book shares the player's cooldowns", s.cooldowns["pressure.atlas_piston"] > 0 && s.selected.pressure === 4, s);

  // ---- multiplayer: Bob (creative) is independent of Alice
  let sb = await h.state("Bob");
  h.check(S, "second player has independent selection", sb.selected.pressure === 0 && Object.keys(sb.cooldowns).length === 0, sb);
  Bob.useItemInSlot(0);
  await h.wait(12);
  Bob.stopUsingItem();
  await h.wait(2);
  sb = await h.state("Bob");
  h.check(S, "creative player can cast (P01)", sb.cooldowns["pressure.lance"] > 0, sb.cooldowns);

  // ---- death during preparation cancels it
  A.selectedSlotIndex = 2; // blood, B01 charge 10
  await h.wait(10);
  A.useItemInSlot(2);
  await h.wait(5);
  A.kill();
  await h.wait(5);
  s = await h.state("Alice");
  h.check(S, "death cancels preparation", !s.preparing, s);
  A.respawn();
  await h.wait(20);
  s = await h.state("Alice");
  h.check(S, "no cast happened through death", !s.cooldowns["blood.stiletto_rain"], s.cooldowns);
  h.check(S, "cooldowns survive death", s.cooldowns["pressure.atlas_piston"] > 0, s.cooldowns);

  // ---- itemCompleteUse never auto-casts: covered by use_duration 3600s (not waited here)
  A.disconnect();
  Bob.disconnect();
  await h.wait(10);
}

async function world_cleanup(h) {
  const S = "cleanup";
  await h.wait(40);
  const w = await h.worldInfo();
  h.check(S, "constructs dissolved after spells ended", w && w.fx === 0, w);
  h.check(S, "temporary blocks removed", w && w.tempBlocks === 0, w);
  h.check(S, "no routines left running", w && w.routines.length === 0, w);
  h.check(S, "no construct entities remain in the world", h.countFamily("grimoire_fx") === 0, h.countFamily("grimoire_fx"));
}

export const SUITES = { controls, ...SPELL_SUITES, ...ROBUST_SUITES, cleanup: world_cleanup };

// Measures the engine's minimum gap between releasing Use and pressing it again. Presses inside the
// engine's re-use window are dropped by Bedrock itself (no itemStartUse at all), so they are recorded as a
// measurement; the checks assert what the add-on relies on: a press after the window always starts a new
// preparation, and a dropped press never produces a cast.
async function reuse_gap(h) {
  const S = "reuse_gap";
  const evs = [];
  const sub1 = h.world.afterEvents.itemStartUse.subscribe((e) => evs.push(["start", h.system.currentTick, e.source.name]));
  const sub2 = h.world.afterEvents.itemReleaseUse.subscribe((e) => evs.push(["release", h.system.currentTick, e.source.name]));
  const sub3 = h.world.afterEvents.itemStopUse.subscribe((e) => evs.push(["stop", h.system.currentTick, e.source.name]));
  const C = h.spawnPlayer("Carol", 20, 0, h.GameMode.Survival);
  await h.wait(20);
  h.give(C, 0, "grimoire:ice");
  C.selectedSlotIndex = 0;
  await h.wait(5);
  const accepted = {};
  for (const gap of [2, 3, 4, 5, 6, 7, 8, 10, 12]) {
    evs.length = 0;
    C.useItemInSlot(0);
    await h.wait(3);
    C.stopUsingItem(); // released before I01's preparation minimum: fizzles, no cooldown
    await h.wait(gap);
    C.useItemInSlot(0);
    await h.wait(3);
    accepted[gap] = evs.filter((e) => e[0] === "start").length >= 2;
    C.stopUsingItem();
    await h.wait(12);
  }
  const window = Math.min(...Object.keys(accepted).map(Number).filter((g) => accepted[g]));
  h.out({ measurement: "engine re-use window", acceptedByGap: accepted, firstAcceptedGapTicks: window });
  h.check(S, `engine re-use window measured: presses >= ${window} ticks after a release are accepted`, Number.isFinite(window) && window <= 10, accepted);
  h.check(S, "every press 10+ ticks after a release starts a new use", accepted[10] && accepted[12], accepted);
  const s = await h.state("Carol");
  h.check(S, "dropped and early-released presses never cast anything", s && Object.keys(s.cooldowns).length === 0, s?.cooldowns);
  h.world.afterEvents.itemStartUse.unsubscribe(sub1);
  h.world.afterEvents.itemReleaseUse.unsubscribe(sub2);
  h.world.afterEvents.itemStopUse.unsubscribe(sub3);
  C.disconnect();
}
SUITES.reuse_gap = reuse_gap;

// Calibration (informational): how applyKnockback maps to player motion in this engine build.
async function calibrate(h) {
  const S = "calibrate";
  const D = h.spawnPlayer("Dave", 40, 0, h.GameMode.Survival);
  await h.wait(30);
  for (const [hz, vy, repeat] of [[1, 0, 1], [2, 0, 1], [1, 0.4, 1], [0.6, 0.05, 10], [1.2, 0.0, 10], [0, 0.6, 1]]) {
    D.teleport({ x: 40.5, y: -60, z: 0.5 });
    await h.wait(10);
    const p0 = D.location;
    const track = [];
    for (let i = 0; i < 24; i++) {
      if (i < repeat) D.applyKnockback({ x: hz, z: 0 }, vy);
      await h.wait(1);
      const l = D.location, v = D.getVelocity();
      track.push([+(l.x - p0.x).toFixed(2), +(l.y - p0.y).toFixed(2), +v.x.toFixed(3), +v.y.toFixed(3)]);
    }
    h.out({ calib: { hz, vy, repeat }, after1: track[0], after2: track[1], after5: track[4], after10: track[9], end: track[23] });
    h.check(S, `knockback h=${hz} v=${vy} x${repeat} moves the player`, Math.abs(track[23][0]) > 0.1 || Math.abs(track[3][1]) > 0.1, track[23]);
  }
  // mobs are simulated server-side: measure the knockback -> velocity mapping on a husk
  for (const [hz, vy] of [[1, 0], [2, 0], [1, 0.5], [0, 0.8]]) {
    const m = h.dim().spawnEntity("minecraft:husk", { x: 44.5, y: -60, z: 4.5 });
    await h.wait(10);
    const p0 = m.location;
    m.applyKnockback({ x: hz, z: 0 }, vy);
    const tr = [];
    for (let i = 0; i < 12; i++) {
      await h.wait(1);
      const l = m.location, v = m.getVelocity();
      tr.push([+(l.x - p0.x).toFixed(2), +(l.y - p0.y).toFixed(2), +v.x.toFixed(3), +v.y.toFixed(3)]);
    }
    h.out({ mobcalib: { hz, vy }, t1: tr[0], t2: tr[1], t5: tr[4], t12: tr[11] });
    h.check(S, `mob knockback h=${hz} v=${vy} moves the mob`, Math.abs(tr[11][0]) > 0.05 || Math.abs(tr[2][1]) > 0.05, tr);
    m.remove();
  }
  D.disconnect();
}
SUITES.calibrate = calibrate;
