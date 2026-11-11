// Per-spell in-engine tests. Each spell is cast through the real controls (crouch to select,
// hold Use for the preparation time, release) by a simulated player inside BDS.
import { EntityDamageCause } from "@minecraft/server";
import { CHARGES } from "./charges.js";

// kind: damage | ward | move | detect | buff | struct | summon | mark
export const SPELLS = {
  pressure: [
    { code: "P01", id: "pressure.lance", kind: "damage", targets: 3, dist: 9, line: true, wait: 50 },
    { code: "P02", id: "pressure.atlas_piston", kind: "damage", targets: 3, dist: 9, wait: 110 },
    { code: "P03", id: "pressure.isobaric_severance", kind: "damage", targets: 3, dist: 7, wait: 90 },
    { code: "P04", id: "pressure.cataclysm_salvo", kind: "damage", targets: 3, dist: 10, wait: 150 },
    { code: "P05", id: "pressure.aegis_of_isobars", kind: "ward", targets: 1, dist: 3, wait: 40, after: 260 },
    { code: "P06", id: "pressure.counterpressure_mantle", kind: "ward", targets: 1, dist: 2.5, wait: 30, after: 300 },
    { code: "P07", id: "pressure.titans_vise", kind: "damage", targets: 3, dist: 8, wait: 150, bind: true },
    { code: "P08", id: "pressure.atmospheric_labyrinth", kind: "struct", targets: 2, dist: 12, wait: 120, after: 260, block: "grimoire:pressure_barrier" },
    { code: "P09", id: "pressure.resonance_cage", kind: "damage", targets: 2, dist: 8, wait: 150 },
    { code: "P10", id: "pressure.pressure_step", kind: "move", targets: 0, wait: 20 },
    { code: "P11", id: "pressure.skyline_rail", kind: "move", targets: 0, wait: 60, lookUp: true },
    { code: "P12", id: "pressure.barometric_omniscience", kind: "detect", targets: 3, dist: 14, wait: 80, after: 240, marker: "grimoire:fx_p_marker" },
    { code: "P13", id: "pressure.equilibrium_theft", kind: "buff", targets: 2, dist: 4, wait: 60 },
    { code: "P14", id: "pressure.isobaric_citadel", kind: "struct", targets: 2, dist: 14, wait: 200, after: 480, block: "grimoire:pressure_barrier", damage: true },
    { code: "P15", id: "pressure.thousand_atmospheres", kind: "damage", targets: 4, dist: 12, wait: 300 },
  ],
  ice: [],
  blood: [],
};

const ITEMS = { pressure: "grimoire:pressure", ice: "grimoire:ice", blood: "grimoire:blood" };
const CHARGE = { ...CHARGES };

function hp(e) {
  try { return e.isValid ? e.getComponent("minecraft:health").currentValue : 0; } catch { return 0; }
}

function countType(h, type) {
  return h.dim().getEntities({ type }).length;
}

function blocksAround(h, center, r, id) {
  let n = 0;
  for (let x = -r; x <= r; x++) for (let z = -r; z <= r; z++) for (let y = 0; y < 6; y++) {
    try {
      const b = h.dim().getBlock({ x: Math.floor(center.x) + x, y: -60 + y, z: Math.floor(center.z) + z });
      if (b && b.typeId === id) n++;
    } catch {}
  }
  return n;
}

async function castSpell(h, sp, school, index, charge) {
  await h.selectSpell(sp, school, index);
  await h.wait(10);
  sp.useItemInSlot(0);
  await h.wait(charge + 4);
  sp.stopUsingItem();
  await h.wait(2);
}

async function runSpell(h, school, i, spec, arenaX, arenaZ) {
  const S = `${school}:${spec.code}`;
  const name = `T${spec.code}`;
  const caster = h.spawnPlayer(name, arenaX, arenaZ, h.GameMode.Survival);
  await h.wait(20);
  h.give(caster, 0, ITEMS[school]);
  caster.selectedSlotIndex = 0;
  await h.resetCd(name);
  const targets = [];
  const ahead = { x: arenaX + 0.5 + (spec.dist ?? 8), y: -60, z: arenaZ + 0.5 };
  for (let k = 0; k < (spec.targets ?? 0); k++) {
    const off = spec.line ? { x: k * 2.2, z: 0 } : { x: Math.cos((k / spec.targets) * 6.283) * 1.8, z: Math.sin((k / spec.targets) * 6.283) * 1.8 };
    const e = h.dim().spawnEntity("minecraft:husk", { x: ahead.x + off.x, y: -60, z: ahead.z + off.z });
    e.addTag("harness_target");
    try { e.addEffect("slowness", 20 * 60, { amplifier: 3, showParticles: false }); } catch {}
    targets.push(e);
  }
  await h.wait(5);
  caster.lookAtLocation({ x: ahead.x, y: spec.lookUp ? -50 : -58.8, z: ahead.z });
  await h.wait(3);
  const hp0 = targets.map(hp);
  const casterHp0 = hp(caster);
  const charge = CHARGE[spec.id] ?? 20;
  const pos0 = { ...caster.location };
  // record every hurt event on the caster: a casting cost would show up as self/no-source damage
  const hurts = [];
  const hurtSub = h.world.afterEvents.entityHurt.subscribe((ev) => {
    if (ev.hurtEntity.id !== caster.id) return;
    hurts.push({ cause: ev.damageSource.cause, src: ev.damageSource.damagingEntity?.typeId ?? null, dmg: ev.damage });
  });
  await castSpell(h, caster, school, i, charge);
  const st = await h.state(name);
  const cd = st?.cooldowns?.[spec.id];
  h.check(S, `${spec.code} activates via crouch-select + hold/release (cooldown started)`, cd !== undefined && cd !== 0, { cd, preparing: st?.preparing, selected: st?.selected });
  // during the spell: poll the construct count
  const midWait = Math.min(spec.wait ?? 40, 30);
  let maxFx = 0;
  let w1 = null;
  for (let t = 0; t < midWait; t += 3) {
    const w = await h.worldInfo();
    if (w && w.fx >= maxFx) { maxFx = w.fx; w1 = w; }
    await h.wait(3);
  }
  h.check(S, `${spec.code} spawns its constructs`, maxFx > 0, { maxFx, w1 });
  if (spec.kind === "ward") {
    const attacker = targets[0] ?? h.dim().spawnEntity("minecraft:husk", { x: arenaX + 2.5, y: -60, z: arenaZ + 0.5 });
    const before = hp(caster);
    caster.applyDamage(6, { cause: EntityDamageCause.entityAttack, damagingEntity: attacker });
    await h.wait(6);
    const after = hp(caster);
    h.check(S, `${spec.code} absorbs/reduces a real attack on the caster`, after > before - 6, { before, after });
    if (spec.code === "P06" || spec.code === "B06") {
      h.check(S, `${spec.code} counterattack hits the attacker`, hp(attacker) < 20 || !attacker.isValid, { attackerHp: hp(attacker) });
    }
  }
  if (spec.kind === "struct") {
    await h.wait(40);
    const n = blocksAround(h, ahead, 14, spec.block) + blocksAround(h, caster.location, 14, spec.block);
    h.check(S, `${spec.code} raises temporary barrier blocks`, n > 10, { blocks: n });
  }
  if (spec.kind === "detect") {
    await h.wait(30);
    const m = countType(h, spec.marker);
    h.check(S, `${spec.code} marks detected living entities`, m >= Math.min(3, spec.targets), { markers: m });
  }
  if (spec.kind === "buff") {
    await h.wait(spec.wait ?? 60);
    const s2 = await h.state(name);
    h.check(S, `${spec.code} grants a single-use empowerment`, s2?.empowered === true, s2);
    await h.resetCd(name);
    // the next eligible spell consumes it (P01)
    await castSpell(h, caster, school, 0, 12);
    await h.wait(5);
    const s3 = await h.state(name);
    h.check(S, `${spec.code} empowerment is consumed by the next eligible spell (no stacking)`, s3?.empowered === false, s3);
  }
  if (spec.kind === "move") {
    const moved = Math.hypot(caster.location.x - pos0.x, caster.location.z - pos0.z);
    h.out({ note: `${spec.code} simulated players have no client physics; knockback-driven motion is not observable in BDS`, moved });
  }
  await h.wait(Math.max(0, (spec.wait ?? 40) - midWait));
  if (spec.kind === "damage" || spec.damage) {
    const dealt = targets.map((t, k) => hp0[k] - hp(t));
    h.check(S, `${spec.code} damages enemies`, dealt.some((d) => d > 0), { dealt });
  }
  h.world.afterEvents.entityHurt.unsubscribe(hurtSub);
  const selfCost = hurts.filter((x) => !(x.src && x.src !== "minecraft:player") && !(spec.kind === "ward" && x.src));
  h.check(S, `${spec.code} costs the caster no health (no self-inflicted damage)`, selfCost.length === 0, { hurts });
  await h.wait(spec.after ?? 40);
  const w2 = await h.worldInfo();
  h.check(S, `${spec.code} cleans up constructs/blocks after it ends`, w2 && w2.fx === 0 && w2.tempBlocks === 0, w2);
  caster.disconnect();
  for (const t of targets) { try { t.remove(); } catch {} }
  h.cleanupTargets();
  await h.wait(10);
}

function suiteFor(school) {
  return async (h) => {
    const list = SPELLS[school];
    for (let i = 0; i < list.length; i++) {
      const spec = list[i];
      if (h.only && h.only.length && !h.only.includes(spec.code)) continue;
      const arenaX = 112 + ((i % 3) - 1) * 40;
      const arenaZ = (Math.floor(i / 3) - 2) * 24;
      try {
        await runSpell(h, school, i, spec, arenaX, arenaZ);
      } catch (err) {
        h.check(`${school}:${spec.code}`, `${spec.code} test crashed`, false, `${err} ${err?.stack ?? ""}`);
      }
    }
  };
}

export function setCharges(map) { Object.assign(CHARGE, map); }

export const SPELL_SUITES = {
  pressure: suiteFor("pressure"),
  ice: suiteFor("ice"),
  blood: suiteFor("blood"),
};
