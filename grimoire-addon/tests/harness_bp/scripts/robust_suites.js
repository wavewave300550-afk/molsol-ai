// Robustness suites: dimension change, PvP / team rules, two simultaneous casters with summons,
// owner disconnect mid-spell, and temporary blocks never replacing existing blocks.
import { world, system } from "@minecraft/server";

const P = "grimoire:pressure", I = "grimoire:ice";

const config = (rule, value) => system.sendScriptEvent("grimoire:config", `${rule} ${value}`);

async function holdRelease(h, sp, ticks) {
  sp.useItemInSlot(sp.selectedSlotIndex);
  await h.wait(ticks);
  sp.stopUsingItem();
  await h.wait(2);
}

function hurtLog(target) {
  const log = [];
  const sub = world.afterEvents.entityHurt.subscribe((ev) => {
    if (ev.hurtEntity.id === target.id) log.push({ cause: ev.damageSource.cause, by: ev.damageSource.damagingEntity?.name ?? ev.damageSource.damagingEntity?.typeId ?? null, dmg: ev.damage });
  });
  return { log, stop: () => world.afterEvents.entityHurt.unsubscribe(sub) };
}

function hunger(sp) {
  try { return sp.getComponent("minecraft:player.hunger").currentValue; } catch { return undefined; }
}

function slotItem(sp, slot) {
  const it = sp.getComponent("minecraft:inventory").container.getItem(slot);
  return it ? { id: it.typeId, amount: it.amount } : null;
}

// ------------------------------------------------------------------------------------ dimension
async function dimension(h) {
  const S = "robust:dimension";
  const sp = h.spawnPlayer("Dana", 16, 30);
  await h.wait(20);
  h.give(sp, 0, P);
  sp.selectedSlotIndex = 0;
  await h.resetCd("Dana");
  await h.selectSpell(sp, "pressure", 4); // P05 Aegis of Isobars (12 s ward)
  await h.wait(10);
  await holdRelease(h, sp, 16);
  await h.wait(10);
  let w = await h.worldInfo();
  h.check(S, "an active cast is running before the dimension change", w?.routines.includes("P05:Dana") && w.fx > 0, w);
  await h.crouch(sp); // -> P06
  sp.useItemInSlot(0);
  await h.wait(6);
  let s = await h.state("Dana");
  h.check(S, "preparation running before the dimension change", s?.preparing?.spell === "pressure.counterpressure_mantle", s);
  const nether = world.getDimension("nether");
  try { sp.teleport({ x: 0.5, y: 129, z: 0.5 }, { dimension: nether }); } catch (e) { h.out({ note: `teleport threw ${e}` }); }
  await h.wait(12);
  h.check(S, "simulated player is now in the Nether", sp.dimension.id === "minecraft:nether", sp.dimension.id);
  s = await h.state("Dana");
  h.check(S, "dimension change cancels the preparation", s && !s.preparing, s);
  w = await h.worldInfo();
  h.check(S, "dimension change ends the caster's active spells", w && !w.routines.some((r) => r.endsWith(":Dana")), w);
  for (let i = 0; i < 8 && w && w.fx > 0; i++) { await h.wait(5); w = await h.worldInfo(); } // dissolve animations
  h.check(S, "their constructs dissolve within 2 seconds", w && w.fx === 0, w);
  sp.stopUsingItem();
  await h.wait(4);
  s = await h.state("Dana");
  h.check(S, "releasing Use after the dimension change casts nothing", s && !s.cooldowns["pressure.counterpressure_mantle"], s?.cooldowns);
  h.check(S, "the cooldown of the spell that was already cast is kept", s && s.cooldowns["pressure.aegis_of_isobars"] > 0, s?.cooldowns);
  try { sp.teleport({ x: 16.5, y: -60, z: 30.5 }, { dimension: h.dim() }); } catch {}
  await h.wait(10);
  sp.disconnect();
  await h.wait(10);
}

// ------------------------------------------------------------------------------------------ pvp
async function pvp(h) {
  const S = "robust:pvp";
  const A = h.spawnPlayer("Pvpa", 16, -30);
  const T = h.spawnPlayer("Pvpt", 16, -23);
  await h.wait(20);
  h.give(A, 0, P);
  A.selectedSlotIndex = 0;
  const shoot = async () => {
    try { T.teleport({ x: 16.5, y: -60, z: -22.5 }); } catch {}
    await h.resetCd("Pvpa");
    await h.wait(4);
    A.lookAtEntity(T);
    await h.wait(3);
    const hurts = hurtLog(T);
    await holdRelease(h, A, 12); // P01 Pressure Lance, charge 8
    await h.wait(20);
    hurts.stop();
    return hurts.log.filter((x) => x.by === "Pvpa");
  };
  try {
    config("pvp", "false");
    await h.wait(3);
    const food0 = hunger(A);
    let hits = await shoot();
    let s = await h.state("Pvpa");
    h.check(S, "PvP off: the lance was cast", s?.cooldowns["pressure.lance"] > 0, s?.cooldowns);
    h.check(S, "PvP off (default): spells never damage other players", hits.length === 0, hits);
    config("pvp", "true");
    await h.wait(3);
    hits = await shoot();
    h.check(S, "PvP on: the same spell damages the other player", hits.length > 0 && hits.every((x) => x.cause === "magic"), hits);
    A.addTag("grimoire_team:red");
    T.addTag("grimoire_team:red");
    hits = await shoot();
    h.check(S, "PvP on, same grimoire_team tag, friendlyFire off: teammates are not damaged", hits.length === 0, hits);
    h.check(S, "casting consumed no food (Survival, full hunger bar)", hunger(A) === food0, { before: food0, after: hunger(A) });
    const it = slotItem(A, 0);
    h.check(S, "the grimoire is not consumed by casting", it && it.id === P && it.amount === 1, it);
  } finally {
    config("pvp", "false");
    await h.wait(3);
  }
  A.disconnect();
  T.disconnect();
  await h.wait(10);
}

// ---------------------------------------------------------------------------------- multiplayer
function knights(h) {
  return h.dim().getEntities({ families: ["frost_knight"] });
}

function near(e, sp, r) {
  const a = e.location, b = sp.location;
  return Math.hypot(a.x - b.x, a.z - b.z) <= r;
}

function tamedTo(e) {
  try { return e.getComponent("minecraft:tameable")?.tamedToPlayerId ?? null; } catch { return null; }
}

async function multiplayer(h) {
  const S = "robust:multiplayer";
  const F = h.spawnPlayer("Finn", 196, 0);
  const G = h.spawnPlayer("Gwen", 220, 0);
  await h.wait(20);
  for (const sp of [F, G]) {
    h.give(sp, 0, I);
    sp.selectedSlotIndex = 0;
  }
  await h.resetCd("Finn");
  await h.resetCd("Gwen");
  await Promise.all([h.selectSpell(F, "ice", 11), h.selectSpell(G, "ice", 11)]); // I12 Imperial Frost Legion
  await h.wait(10);
  F.useItemInSlot(0);
  G.useItemInSlot(0);
  await h.wait(30);
  F.stopUsingItem();
  G.stopUsingItem();
  await h.wait(40);
  const sf = await h.state("Finn"), sg = await h.state("Gwen");
  h.check(S, "two players cast the same spell in the same tick; both activate", sf?.cooldowns["ice.frost_legion"] > 0 && sg?.cooldowns["ice.frost_legion"] > 0, { finn: sf?.cooldowns, gwen: sg?.cooldowns });
  const all = knights(h);
  const kf = all.filter((k) => near(k, F, 8)), kg = all.filter((k) => near(k, G, 8));
  h.check(S, "each caster summons their own three knights", kf.length === 3 && kg.length === 3, { finn: kf.length, gwen: kg.length, total: all.length });
  const ownF = kf.filter((k) => tamedTo(k) === F.id).length, ownG = kg.filter((k) => tamedTo(k) === G.id).length;
  h.check(S, "summoned knights are tamed to their own caster", ownF === 3 && ownG === 3, { ownF, ownG });
  F.disconnect();
  await h.wait(40);
  const left = knights(h);
  h.check(S, "when one caster disconnects only their summons are removed", left.length === 3 && left.every((k) => near(k, G, 10)), { remaining: left.length });
  const w = await h.worldInfo();
  h.check(S, "the disconnected caster's spell routine ended", w && !w.routines.some((r) => r.endsWith(":Finn")), w?.routines);
  h.check(S, "the other caster's spell keeps running", w && w.routines.includes("I12:Gwen"), w?.routines);
  G.disconnect();
  await h.wait(40);
  h.check(S, "no summons remain after both casters left", knights(h).length === 0, knights(h).length);
}

// ------------------------------------------------------------------------- blocks + disconnect
async function blocks(h) {
  const S = "robust:blocks";
  const H = h.spawnPlayer("Hank", 96, 30);
  await h.wait(20);
  h.give(H, 0, P);
  H.selectedSlotIndex = 0;
  await h.resetCd("Hank");
  const center = { x: 96 + 12, y: -60, z: 30 };
  const gold = [];
  for (let dx = -8; dx <= 8; dx += 2) for (let dz = -8; dz <= 8; dz += 2) {
    if (dz === 0 || Math.abs(dx) + Math.abs(dz) < 4) continue; // keep the aim line and the centre clear
    gold.push({ x: center.x + dx, y: -60, z: center.z + dz });
  }
  const setAll = (id) => { for (const g of gold) { try { h.dim().getBlock(g)?.setType(id); } catch {} } };
  const intact = () => gold.filter((g) => { try { return h.dim().getBlock(g)?.typeId === "minecraft:gold_block"; } catch { return false; } }).length;
  const barriers = () => {
    let n = 0;
    for (let x = -16; x <= 16; x++) for (let z = -16; z <= 16; z++) for (let y = -60; y <= -54; y++) {
      try { if (h.dim().getBlock({ x: center.x + x, y, z: center.z + z })?.typeId === "grimoire:pressure_barrier") n++; } catch {}
    }
    return n;
  };
  setAll("minecraft:gold_block");
  await h.wait(5);
  h.check(S, "placed pre-existing blocks inside the labyrinth footprint", intact() === gold.length, { gold: gold.length });
  await h.selectSpell(H, "pressure", 7); // P08 Atmospheric Labyrinth
  await h.wait(10);
  const castLab = async () => {
    H.lookAtLocation({ x: center.x + 0.5, y: -59.5, z: center.z + 0.5 });
    await h.wait(3);
    await holdRelease(h, H, 24);
    await h.wait(60);
  };
  await castLab();
  let w = await h.worldInfo();
  h.check(S, "labyrinth raised temporary walls", w && w.tempBlocks > 10, w);
  h.check(S, "temporary walls never replace existing blocks (during the spell)", intact() === gold.length, { intact: intact(), of: gold.length });
  await h.wait(340);
  w = await h.worldInfo();
  h.check(S, "all temporary walls removed when the spell ends", w && w.tempBlocks === 0 && barriers() === 0, { w, barriers: barriers() });
  h.check(S, "existing blocks are intact after the spell", intact() === gold.length, { intact: intact(), of: gold.length });

  await h.resetCd("Hank");
  await castLab();
  w = await h.worldInfo();
  const during = w?.tempBlocks ?? 0;
  h.check(S, "second labyrinth is up before the owner disconnects", during > 10 && w.routines.includes("P08:Hank"), w);
  H.disconnect();
  await h.wait(30);
  w = await h.worldInfo();
  h.check(S, "owner disconnect mid-spell removes every temporary wall", w && w.tempBlocks === 0 && barriers() === 0, { w, barriers: barriers() });
  h.check(S, "owner disconnect mid-spell ends the routine and its constructs", w && w.fx === 0 && !w.routines.some((r) => r.endsWith(":Hank")), w);
  h.check(S, "existing blocks are intact after the disconnect cleanup", intact() === gold.length, { intact: intact(), of: gold.length });
  setAll("minecraft:air");
}

// ------------------------------------------------------------------------------------ six books
async function sixBooks(h) {
  const S = "robust:six";
  const books = ["grimoire:pressure", "grimoire:ice", "grimoire:blood", "grimoire:plasma", "grimoire:darkness", "grimoire:prism_light"];
  const schools = ["pressure", "ice", "blood", "plasma", "darkness", "prism_light"];
  const sp = h.spawnPlayer("Sixa", 16, -50);
  await h.wait(20);
  books.forEach((b, i) => h.give(sp, i, b));
  await h.resetCd("Sixa");
  for (let i = 0; i < 6; i++) {
    sp.selectedSlotIndex = i;
    await h.wait(4);
    for (let k = 0; k <= i; k++) await h.crouch(sp, 2);
  }
  const s = await h.state("Sixa");
  const ok = schools.every((sc, i) => s?.selected?.[sc] === i + 1);
  h.check(S, "six grimoires keep six independent selections in one hotbar", ok, s?.selected);
  sp.selectedSlotIndex = 3; // plasma: four crouches above selected spell 05, Stellarator Ward (charge 14)
  await h.wait(12);
  sp.useItemInSlot(3);
  await h.wait(18);
  sp.stopUsingItem();
  await h.wait(4);
  const s2 = await h.state("Sixa");
  h.check(S, "a plasma cast starts only the selected spell's cooldown", Object.keys(s2?.cooldowns ?? {}).join() === "plasma.stellarator_ward", s2?.cooldowns);
  sp.disconnect();
  await h.wait(10);
}

export const ROBUST_SUITES = {
  robustness: async (h) => {
    for (const [name, fn] of [["dimension", dimension], ["pvp", pvp], ["multiplayer", multiplayer], ["blocks", blocks], ["six", sixBooks]]) {
      if (h.only && h.only.length && !h.only.includes(name)) continue;
      try {
        await fn(h);
      } catch (err) {
        h.check(`robust:${name}`, `${name} crashed`, false, `${err} ${err?.stack ?? ""}`);
      }
    }
  },
};
