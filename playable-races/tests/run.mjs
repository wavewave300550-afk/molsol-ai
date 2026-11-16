// Runtime smoke tests: run the compiled behavior-pack scripts on the strict API mock
// through real gameplay scenarios.  usage: node tests/run.mjs  (after tools/build.py)
import fs from "node:fs";
import path from "node:path";

const HERE = path.dirname(new URL(import.meta.url).pathname);
const ROOT = path.resolve(HERE, "..");
const RUN = path.join(HERE, ".run");

// ---- stage the compiled scripts next to mock @minecraft modules
fs.rmSync(RUN, { recursive: true, force: true });
fs.cpSync(path.join(ROOT, "packs/PlayableRaces_BP/scripts"), path.join(RUN, "scripts"), { recursive: true });
fs.writeFileSync(path.join(RUN, "package.json"), JSON.stringify({ type: "module" }));
for (const [name, file] of [["server", "server.mjs"], ["server-ui", "server-ui.mjs"]]) {
  const d = path.join(RUN, "node_modules/@minecraft", name);
  fs.mkdirSync(d, { recursive: true });
  fs.writeFileSync(path.join(d, "package.json"), JSON.stringify({ name: `@minecraft/${name}`, type: "module", main: "index.js" }));
  fs.writeFileSync(path.join(d, "index.js"), `export * from ${JSON.stringify(path.join(HERE, "mock", file))};\n`);
}

const M = await import(path.join(HERE, "mock/server.mjs"));
const UI = await import(path.join(HERE, "mock/server-ui.mjs"));
const { sim, world, system, harness, tickN, ItemStack, InputPermissionCategory } = M;
const { answer, ui } = UI;
console.warn = (...a) => sim.log.warns.push(a.map(String).join(" "));

// ---- tiny assertion framework
let passed = 0;
const failures = [];
let section = "";
const perSection = new Map();
function ok(cond, msg) {
  const r = perSection.get(section) ?? { pass: 0, fail: 0, msgs: [] };
  perSection.set(section, r);
  r.msgs.push(msg.replace(/ \(expected.*$/, ""));
  if (cond) {
    passed++;
    r.pass++;
  } else {
    failures.push(`[${section}] ${msg}`);
    r.fail++;
  }
}
function eq(a, b, msg) {
  ok(a === b, `${msg} (expected ${JSON.stringify(b)}, got ${JSON.stringify(a)})`);
}
async function settle(n = 2) {
  for (let i = 0; i < n; i++) {
    await new Promise((r) => setTimeout(r, 0));
    tickN(1);
    await new Promise((r) => setTimeout(r, 0));
  }
}
function begin(name) {
  section = name;
}

// ---- boot
const components = new Map();
const commands = new Map();
const enums = new Map();
await import(path.join(RUN, "scripts/main.js"));
system.beforeEvents.startup.fire({
  itemComponentRegistry: { registerCustomComponent: (id, c) => components.set(id, c) },
  customCommandRegistry: {
    registerCommand: (def, cb) => commands.set(def.name, { def, cb }),
    registerEnum: (n, v) => enums.set(n, v),
  },
});
world.afterEvents.worldLoad.fire({});
tickN(1);

begin("boot");
ok(components.has("plrace:focus") && components.has("plrace:codex"), "custom item components registered");
for (const c of ["plrace:codex", "plrace:setrace", "plrace:resetcooldowns", "plrace:bloodmoon"]) ok(commands.has(c), `command ${c} registered`);
ok(enums.get("plrace:race")?.includes("salamander") && enums.get("plrace:race")?.includes("003"), "race enum has keys and permanent codes");

// ---- helpers
const OW = harness.dims["minecraft:overworld"];
const head = (p) => p.getComponent("minecraft:equippable").getEquipment("Head");
const inv = (p) => p.getComponent("minecraft:inventory").container;
function hold(p, id) {
  const c = inv(p);
  for (let i = 0; i < c.size; i++) {
    const it = c.getItem(i);
    if (it && it.typeId === id) {
      p.selectedSlotIndex = i;
      return true;
    }
  }
  return false;
}
function faceTo(p, t) {
  const dx = t.location.x - p.location.x;
  const dz = t.location.z - p.location.z;
  const dy = (t.location.y + 0.9) - (p.location.y + 1.62);
  p.setRotation({ x: (-Math.atan2(dy, Math.hypot(dx, dz)) * 180) / Math.PI, y: (Math.atan2(-dx, dz) * 180) / Math.PI });
}
async function use(p, sneak = false) {
  p.isSneaking = sneak;
  const c = inv(p);
  components.get("plrace:focus").onUse({ source: p, itemStack: c.getItem(p.selectedSlotIndex) });
  await settle(2);
  p.isSneaking = false;
  tickN(6); // global cast lock / debounce window
}
function cdLeft(p, id) {
  const raw = p.getDynamicProperty("plrace:data");
  return raw ? JSON.parse(raw).cd?.[id] ?? 0 : 0;
}
function data(p) {
  return JSON.parse(p.getDynamicProperty("plrace:data"));
}
function mob(type, x, z) {
  return harness.spawnMob(type, { x, y: 64, z });
}
function hp(e) {
  return e.isValid ? e.getComponent("minecraft:health").currentValue : 0; // a creature that died (and despawned) has 0 left
}
function forceSave() {
  tickN(101);
}
const particles = (id) => sim.log.particles.filter((x) => x.id === id).length;

// ======================================================================== first join + selection UI
begin("first join & selection");
answer.action(0); // main codex: "Choose a Lineage"
answer.action(0); // race list: Salamander (001)
answer.action(0); // detail: "Become"
answer.message(0); // confirm: Embrace
const alice = harness.join("Alice");
await settle(12);
tickN(60);
await settle(20);
ok(inv(alice).slots.some((s) => s?.typeId === "plrace:codex"), "Lineage Codex given on first join");
ok(ui.shown.some((f) => f.title.includes("Lineage Codex")), "codex auto-opened for a new player");
ok(ui.shown.some((f) => f.kind === "action" && f.buttons.some((b) => b.icon === "textures/plrace/races/ui/portrait_001")), "selection list shows race portraits");
ok(ui.shown.some((f) => f.kind === "message" && f.title.includes("Embrace")), "confirmation dialog shown before assigning");
eq(data(alice).race, "001", "race 001 persisted");
ok(["plrace:form_salamander", "plrace:form_salamander_bloom"].includes(head(alice)?.typeId), "salamander form crest worn in head slot (stable or blooming in the sun)");
eq(head(alice)?.lockMode, "slot", "crest locked in slot");
ok(head(alice)?.keepOnDeath === true, "crest kept on death");
ok(inv(alice).slots.some((s) => s?.typeId === "plrace:focus_salamander" && s.lockMode === "inventory"), "focus given, locked to inventory");
ok(sim.log.titles.some((t) => String(t.t).includes("Aberrant Flora Salamander")), "transformation title shown");
ok(particles("plrace:rite_aura") > 0, "rite aura particle");

// ======================================================================== salamander abilities
begin("salamander: Sundew Snare");
hold(alice, "plrace:focus_salamander");
const z1 = mob("minecraft:zombie", 0.5, 7.5);
faceTo(alice, z1);
const before = hp(z1);
await use(alice);
ok(hp(z1) < before, "snare damages the target");
ok(z1.getEffect("slowness")?.amplifier === 2, "snare applies Slowness III");
ok(particles("plrace:snare_strand") > 0, "snare strand particle");
tickN(2);
eq(head(alice)?.typeId, "plrace:form_salamander_predatory", "predatory form shown after snare");
forceSave();
ok(cdLeft(alice, "sundew_snare") > 0, "snare cooldown persisted");
ok(!head(alice)?.typeId.includes("predatory"), "predatory form reverts after it expires");

begin("salamander: cooldown & failure feedback");
const strandsBefore = particles("plrace:snare_strand");
faceTo(alice, z1);
await use(alice);
ok(String(sim.log.actionbar.get(alice.id)).includes("recovering"), "recasting during the cooldown shows 'recovering'");
eq(particles("plrace:snare_strand"), strandsBefore, "nothing is cast while on cooldown");
commands.get("plrace:resetcooldowns").cb({ sourceEntity: alice }, [alice]);
await settle(2);
alice.setRotation({ x: 0, y: 180 }); // look away from every creature
await use(alice);
ok(String(sim.log.actionbar.get(alice.id)).includes("No prey"), "no target -> clear failure message");
forceSave();
eq(cdLeft(alice, "sundew_snare"), 0, "a failed cast does not spend the cooldown");

begin("salamander: Carnivorous Embrace");
await use(alice, true); // sneak+use cycles to Embrace
eq(data(alice).sel, 1, "selection cycled to ability 2");
const z2 = mob("minecraft:zombie", 0.5, 2.5);
faceTo(alice, z2);
alice._health = 10;
const zBefore = hp(z2);
await use(alice);
ok(hp(z2) <= zBefore - 6, "embrace deals at least 6 damage");
ok(alice._health > 10, "embrace heals the salamander");
ok(particles("plrace:trap_snap") > 0, "trap snap particle");

begin("salamander: Root Metamorphosis");
await use(alice, true); // -> Root
eq(data(alice).sel, 2, "selection cycled to Root");
await use(alice);
eq(alice.inputPermissions.isPermissionCategoryEnabled(InputPermissionCategory.LateralMovement), false, "walking disabled while rooted");
tickN(3);
eq(head(alice)?.typeId, "plrace:form_salamander_rooted", "rooted form worn");
ok(sim.log.anims.some((a) => a.name === "animation.plrace.pose.sal_root"), "rooting pose played");
alice.location = { x: alice.location.x + 3, y: 64, z: alice.location.z };
tickN(2);
ok(Math.abs(alice.location.x - 0.5) < 0.5, "knockback / displacement re-anchored while rooted");
world.afterEvents.playerButtonInput.fire({ player: alice, button: "Jump", newButtonState: "Pressed" });
tickN(6);
eq(alice.inputPermissions.isPermissionCategoryEnabled(InputPermissionCategory.LateralMovement), true, "JUMP uproots and restores movement");
ok(!String(head(alice)?.typeId).includes("rooted"), "rooted form removed after uprooting");

begin("salamander: Bladder Jet");
await use(alice, true); // -> Jet
const d0 = data(alice).res.hyd;
alice.setRotation({ x: 0, y: 0 });
const z3 = mob("minecraft:zombie", 0.5, alice.location.z + 2.5);
await use(alice);
ok(data(alice).res.hyd <= d0 - 19.9, `land jet consumes 20% hydration (${d0.toFixed(1)} -> ${data(alice).res.hyd.toFixed(1)})`);
forceSave();
ok(cdLeft(alice, "bladder_jet") > 0, "jet on cooldown after land use");
ok(z3.isValid, "jet does not kill");

begin("salamander: hydration states");
sim.biomeAt = () => "minecraft:desert";
const s0 = data(alice).res.hyd;
tickN(20 * 40);
forceSave();
ok(data(alice).res.hyd < s0, "hydration drains in the desert");
tickN(20 * 60);
forceSave();
eq(data(alice).st.sal, "dormant", "becomes dormant when parched");
eq(head(alice)?.typeId, "plrace:form_salamander_dormant", "dormant form shown");
ok(alice.getEffect("slowness") !== undefined, "dormant: slight slowness");
sim.biomeAt = () => "minecraft:plains";
sim.waterAt = (l) => l.y < 66 && l.x > 30;
alice.location = { x: 40.5, y: 64, z: 0.5 };
tickN(20 * 10);
forceSave();
ok(data(alice).res.hyd >= 70, "water rehydrates");
ok(alice.getEffect("conduit_power") !== undefined, "gills: conduit power in water");
ok(alice._uw > 0.02, "aquatic agility raises swim speed");
eq(data(alice).st.sal, "bloom", "blooms in water");
eq(head(alice)?.typeId, "plrace:form_salamander_bloom", "bloom form shown");
sim.waterAt = () => false;
alice.location = { x: 0.5, y: 64, z: 0.5 };
tickN(40);
eq(alice._uw, 0.02, "swim speed restored on land");

// ======================================================================== golem
begin("golem: assignment via command");
const bob = harness.join("Bob", { x: 100.5, y: 64, z: 0.5 });
await settle(15);
ui.answers.length = 0;
commands.get("plrace:setrace").cb({ sourceEntity: bob, initiator: bob }, "golem", [bob]);
await settle(3);
eq(data(bob).race, "002", "golem assigned by command");
eq(head(bob)?.typeId, "plrace:form_golem", "golem form crest");
tickN(21);
ok(bob.getEffect("health_boost")?.amplifier === 1, "Health Boost II");

begin("golem: Titan's Edict");
hold(bob, "plrace:focus_golem");
const g1 = mob("minecraft:zombie", 100.5, 4.0);
const g2 = mob("minecraft:skeleton", 100.5, 7.0);
const villager = harness.spawnMob("minecraft:villager_v2", { x: 101.5, y: 64, z: 3.5 }, OW, ["villager", "mob"]);
bob.setRotation({ x: 0, y: 0 });
const g1b = hp(g1), g2b = hp(g2), vb = hp(villager);
await use(bob);
tickN(1);
eq(head(bob)?.typeId, "plrace:form_golem_siege", "siege hammer configuration during the edict");
tickN(30);
ok(hp(g1) < g1b && hp(g2) < g2b, "shockwave hits enemies along its path");
eq(hp(villager), vb, "villagers are never hurt");
ok(particles("plrace:shock_rupture") >= 5, "shockwave travels (rupture particles)");
tickN(20);
eq(head(bob)?.typeId, "plrace:form_golem", "form reassembles after the edict");

begin("golem: Runic Bastion");
await use(bob, true);
await use(bob);
tickN(2);
eq(head(bob)?.typeId, "plrace:form_golem_bastion", "bastion configuration while braced");
const front = mob("minecraft:zombie", 100.5, 2);
bob._health = 40;
let h0 = bob._health;
bob.applyDamage(10, { cause: "entityAttack", damagingEntity: front });
ok(h0 - bob._health <= 3.01, "frontal melee reduced by bastion and stone body");
const back = mob("minecraft:zombie", 100.5, -2);
h0 = bob._health;
bob.applyDamage(10, { cause: "entityAttack", damagingEntity: back });
ok(h0 - bob._health > 3 && h0 - bob._health <= 5.3, "rear hits only partially reduced");
const arrowOk = bob.applyDamage(6, { cause: "projectile", damagingEntity: front });
ok(arrowOk === false, "frontal projectiles blocked outright");
tickN(110);
ok(!String(head(bob)?.typeId).includes("bastion"), "bastion ends after 5 s");

begin("golem: Glyph Dominion");
await use(bob, true);
const inner = mob("minecraft:zombie", 103.5, 0.5);
const outer = mob("minecraft:zombie", 108.5, 0.5);
await use(bob);
tickN(18);
ok(particles("plrace:glyph_circle") === 1, "rune circle inscribed");
tickN(6);
ok(inner.getEffect("slowness")?.amplifier === 2, "enemy inside is slowed (Slowness III)");
const before2 = outer.location.x;
outer.location = { x: 107.5, y: 64, z: 0.5 }; // approaches the rim
tickN(6);
ok(outer.location.x > 107.5 || outer._hits.length > 0, "approaching enemy is repelled");
bob._health = 40;
const wardBefore = bob._health;
bob.applyDamage(10, { cause: "magic" });
const taken = wardBefore - bob._health;
ok(Math.abs(taken - 8.5) < 0.01 || Math.abs(taken - 7.65) < 0.01, `golem inside its own circle is Warded (-15%, x0.9 if in Monolith Stance): took ${taken}`);
bob._health = 40;
tickN(170);

begin("golem: rune disruption");
commands.get("plrace:resetcooldowns").cb({ sourceEntity: bob }, [bob]);
await settle(2);
while (data(bob).sel !== 2) await use(bob, true);
bob.applyDamage(8, { cause: "magic" });
bob.applyDamage(8, { cause: "magic" });
bob.applyDamage(8, { cause: "magic" });
tickN(2);
eq(head(bob)?.typeId, "plrace:form_golem_disrupted", "disrupted form shown");
const castsBefore = data(bob).stats.casts;
await use(bob);
eq(data(bob).stats.casts, castsBefore, "Glyph Dominion blocked while disrupted");
ok(String(sim.log.actionbar.get(bob.id)).includes("disrupted"), "disruption explained on the HUD");
forceSave();
eq(data(bob).st.gol, "disrupted", "magic damage disrupts runes (persisted)");
tickN(20 * 20);
forceSave();
eq(data(bob).st.gol, "aligned", "runes realign over time");

begin("golem: Colossus Reassembly");
commands.get("plrace:resetcooldowns").cb({ sourceEntity: bob }, [bob]);
await settle(2);
await use(bob, true); // -> 3 (reform)
eq(data(bob).sel, 3, "selection on Reassembly");
bob.location = { x: 100.5, y: 64, z: 0.5 };
bob.setRotation({ x: 10, y: 0 });
const nearDest = mob("minecraft:zombie", 100.5, 10.5);
const startZ = bob.location.z;
await use(bob);
tickN(1);
eq(head(bob)?.typeId, "plrace:form_golem_scattered", "scattered configuration");
const invuln = bob.applyDamage(5, { cause: "entityAttack", damagingEntity: nearDest });
ok(invuln === false, "untouchable while scattered");
tickN(25);
ok(bob.location.z > startZ + 4, `teleported toward the view (${bob.location.z.toFixed(1)})`);
ok(nearDest._hits.some((h) => h.by === bob.id), "reconstruction burst hits nearby enemies");

// ======================================================================== held use button (repeats)
begin("held use button does not cancel channels");
async function holdUse(p, ticks, every = 5) {
  for (let t = 0; t < ticks; t += every) {
    components.get("plrace:focus").onUse({ source: p, itemStack: inv(p).getItem(p.selectedSlotIndex) });
    tickN(every);
    await settle(1);
  }
}
commands.get("plrace:resetcooldowns").cb({ sourceEntity: bob }, [bob]);
await settle(2);
bob.location = { x: 100.5, y: 64, z: 0.5 };
hold(bob, "plrace:focus_golem");
while (data(bob).sel !== 1) await use(bob, true);
components.get("plrace:focus").onUse({ source: bob, itemStack: inv(bob).getItem(bob.selectedSlotIndex) });
await settle(1);
await holdUse(bob, 40);
eq(head(bob)?.typeId, "plrace:form_golem_bastion", "Runic Bastion survives a held use button (2 s of repeats)");
const held1 = mob("minecraft:zombie", 100.5, 2);
bob._health = 40;
const hb0 = bob._health;
bob.applyDamage(10, { cause: "entityAttack", damagingEntity: held1 });
ok(hb0 - bob._health <= 3.01, "bastion still reduces frontal damage while the button is held");
tickN(10);
await use(bob); // a deliberate new press after the grace period drops the wall
tickN(2);
ok(!String(head(bob)?.typeId).includes("bastion"), "a deliberate second press drops the bastion (toggle)");
tickN(70);
commands.get("plrace:resetcooldowns").cb({ sourceEntity: bob }, [bob]);
await settle(2);
while (data(bob).sel !== 0) await use(bob, true);
await use(bob); // Titan's Edict
tickN(12);
await use(bob, true); // select Bastion right after the slam
await use(bob);
tickN(2);
eq(head(bob)?.typeId, "plrace:form_golem_bastion", "Bastion can be cast right after Titan's Edict (no lingering Busy)");
tickN(110);
commands.get("plrace:resetcooldowns").cb({ sourceEntity: bob }, [bob]);
await settle(2);
while (data(bob).sel !== 3) await use(bob, true);
bob.location = { x: 100.5, y: 64, z: 0.5 };
bob.setRotation({ x: 10, y: 0 });
const hz = bob.location.z;
components.get("plrace:focus").onUse({ source: bob, itemStack: inv(bob).getItem(bob.selectedSlotIndex) });
await settle(1);
await holdUse(bob, 30);
ok(bob.location.z > hz + 4, `Colossus Reassembly completes with a held use button (z ${hz} -> ${bob.location.z.toFixed(1)})`);
tickN(20);
commands.get("plrace:resetcooldowns").cb({ sourceEntity: bob }, [bob]);
await settle(2);
bob.location = { x: 100.5, y: 64, z: 0.5 };
bob.setRotation({ x: -60, y: 0 }); // looking at the sky
const sz = bob.location.z;
await use(bob);
tickN(25);
ok(bob.location.z > sz + 4, `Reassembly still works when looking at the sky (z ${sz} -> ${bob.location.z.toFixed(1)})`);
commands.get("plrace:resetcooldowns").cb({ sourceEntity: bob }, [bob]);
await settle(2);
bob.setRotation({ x: 85, y: 0 }); // looking at the feet
const fz = bob.location.z;
await use(bob);
tickN(25);
ok(bob.location.z > fz + 2, `Reassembly still works when looking down (z ${fz.toFixed(1)} -> ${bob.location.z.toFixed(1)})`);
bob.setRotation({ x: 0, y: 0 });

// ======================================================================== jackalope + blood moon
begin("jackalope: selection & passives");
const cat = harness.join("Cat", { x: -100.5, y: 64, z: 0.5 });
await settle(15);
ui.answers.length = 0;
commands.get("plrace:setrace").cb({ sourceEntity: cat }, "003", [cat]);
await settle(3);
eq(head(cat)?.typeId, "plrace:form_jackalope", "jackalope form");
tickN(21);
ok(cat.getEffect("speed") !== undefined && cat.getEffect("jump_boost") !== undefined, "speed and jump boost");
hold(cat, "plrace:focus_jackalope");

begin("jackalope: Lunar Bound");
cat.setRotation({ x: 0, y: 0 });
const z0 = cat.location.z;
await use(cat);
ok(cat.location.z > z0 + 2, "leap moves the jackalope");
ok(particles("plrace:crescent_trail") > 0, "crescent trail");
const fallOk = cat.applyDamage(6, { cause: "fall" });
ok(fallOk === false, "no fall damage right after a leap");

begin("jackalope: Antler Brand & sigil");
await use(cat, true);
cat.location = { x: -100.5, y: 64, z: 0.5 };
cat.setRotation({ x: 0, y: 0 });
const prey = mob("minecraft:zombie", -100.5, 3.5);
components.get("plrace:focus").onUse({ source: cat, itemStack: inv(cat).getItem(cat.selectedSlotIndex) });
await settle(1);
await holdUse(cat, 20); // held through the charge
ok(prey._hits.some((h) => h.by === cat.id && h.amount >= 5), "brand charge strikes for 5");
const b4 = prey._hits.length;
prey.applyDamage(2, { cause: "entityAttack", damagingEntity: cat });
const last = prey._hits[prey._hits.length - 1];
ok(prey._hits.length === b4 + 1 && last.amount === 5, "branded target takes +3 melee damage");
tickN(8);
ok(particles("plrace:moon_sigil") > 0, "lunar sigil shown over the target");

begin("jackalope: Velvet Mirage");
commands.get("plrace:resetcooldowns").cb({ sourceEntity: cat }, [cat]);
await settle(2);
await use(cat, true);
const hunter = mob("minecraft:zombie", -96.5, 0.5);
await use(cat);
const decoys = OW.getEntities({ type: "plrace:velvet_mirage" });
eq(decoys.length, 1, "illusion spawned");
ok(hunter._hits.some((h) => h.by === decoys[0]?.id), "nearby hostiles are provoked by the illusion");
const evaded = cat.applyDamage(5, { cause: "entityAttack", damagingEntity: hunter });
ok(evaded === false, "Velvet Step evades the next blow");
decoys[0].applyDamage(3, { cause: "entityAttack", damagingEntity: hunter });
tickN(3);
ok(!decoys[0].isValid, "struck illusion bursts");
ok(hunter.getEffect("blindness") !== undefined, "attacker dazzled (blindness)");

begin("jackalope: Crimson Waltz");
for (const e of [prey, hunter]) if (e.isValid) e.remove();
await use(cat, true);
cat.location = { x: -100.5, y: 64, z: 0.5 };
const dancer = mob("minecraft:ravager", -100.5, 5.5);
dancer._maxHealth = 100;
dancer._health = 100;
faceTo(cat, dancer);
components.get("plrace:focus").onUse({ source: cat, itemStack: inv(cat).getItem(cat.selectedSlotIndex) });
await settle(1);
await holdUse(cat, 40); // button held for the whole dance
const waltzHits = dancer._hits.filter((h) => h.by === cat.id).length;
ok(waltzHits >= 5, `waltz: 4 leaps + finale (${waltzHits} hits)`);
ok(particles("plrace:crimson_slash") >= 5, "crimson crescent slashes");
ok(Math.hypot(cat.location.x - dancer.location.x, cat.location.z - dancer.location.z) < 4, "the jackalope ends the waltz beside its target");

begin("blood moon: lifecycle");
sim.day = 8; // full moon (day % 8 == 0)
sim.time = 11990;
commands.get("plrace:bloodmoon").cb({}, "next");
await settle(2);
tickN(60);
let bm = JSON.parse(world.getDynamicProperty("plrace:bloodmoon"));
eq(bm.phase, "omen", "full moon dusk rolls the forced Blood Moon (omen)");
sim.time = 12990;
tickN(80);
bm = JSON.parse(world.getDynamicProperty("plrace:bloodmoon"));
eq(bm.phase, "active", "Blood Moon rises at moonrise");
ok(cat._fog.includes("plrace_bm") && alice._fog.includes("plrace_bm"), "crimson fog pushed for overworld players");
tickN(25);
eq(head(cat)?.typeId, "plrace:form_jackalope_awakened", "jackalope awakens");
ok(sim.log.fades.some((f) => f.p === cat.id), "awakening camera fade");
eq(cat.getEffect("speed")?.amplifier, 1, "Speed II while awakened");
commands.get("plrace:resetcooldowns").cb({ sourceEntity: cat }, [cat]);
await settle(2);
while (data(cat).sel !== 0) await use(cat, true);
await use(cat);
await use(cat);
forceSave();
ok(data(cat).res["chg:lunar_bound"] === 0, "two Lunar Bound charges under the Blood Moon");
harness.changeDimension(cat, "minecraft:nether");
tickN(30);
ok(!cat._fog.includes("plrace_bm"), "fog removed in the Nether");
eq(head(cat)?.typeId, "plrace:form_jackalope", "awakening suspended away from the moon");
harness.changeDimension(cat, "minecraft:overworld");
tickN(30);
ok(cat._fog.includes("plrace_bm"), "fog restored back in the overworld");
sim.time = 23470;
tickN(45);
bm = JSON.parse(world.getDynamicProperty("plrace:bloodmoon"));
eq(bm.phase, "idle", "Blood Moon ends at dawn");
ok(!cat._fog.includes("plrace_bm") && !alice._fog.includes("plrace_bm"), "fog removed for everyone at dawn");
tickN(25);
eq(head(cat)?.typeId, "plrace:form_jackalope", "jackalope returns to the ordinary lunar form");

// ======================================================================== robustness
begin("death during a channel");
alice.location = { x: 0.5, y: 64, z: 0.5 };
alice.isOnGround = true;
hold(alice, "plrace:focus_salamander");
commands.get("plrace:resetcooldowns").cb({ sourceEntity: alice }, [alice]);
await settle(2);
while (data(alice).sel !== 2) await use(alice, true);
components.get("plrace:focus").onUse({ source: alice, itemStack: inv(alice).getItem(alice.selectedSlotIndex) });
await settle(1);
await holdUse(alice, 40);
eq(alice.inputPermissions.isPermissionCategoryEnabled(InputPermissionCategory.LateralMovement), false, "still rooted after holding the button for 2 s");
alice.kill();
tickN(2);
eq(alice.inputPermissions.isPermissionCategoryEnabled(InputPermissionCategory.LateralMovement), true, "death ends rooting and restores movement");
harness.respawn(alice);
tickN(20);
ok(head(alice)?.typeId?.startsWith("plrace:form_salamander"), "form restored after respawn");

begin("disconnect mid-ability & relog persistence");
commands.get("plrace:resetcooldowns").cb({ sourceEntity: alice }, [alice]);
await settle(2);
await use(alice);
eq(alice.inputPermissions.isPermissionCategoryEnabled(InputPermissionCategory.LateralMovement), false, "rooted before logout");
forceSave();
harness.leave(alice);
tickN(5);
alice.inputPermissions.setPermissionCategory(InputPermissionCategory.LateralMovement, false); // permission persisted on the client
harness.rejoin(alice);
tickN(20);
eq(alice.inputPermissions.isPermissionCategoryEnabled(InputPermissionCategory.LateralMovement), true, "movement restored on rejoin");
eq(data(alice).race, "001", "race restored after relog");
ok(cdLeft(alice, "root_metamorphosis") > 0, "cooldowns survive relog");

begin("multiplayer independence");
commands.get("plrace:resetcooldowns").cb({}, [alice, bob, cat]);
await settle(2);
ok(data(alice).race === "001" && data(bob).race === "002" && data(cat).race === "003", "three players keep three different races");
ok(head(alice).typeId.includes("salamander") && head(bob).typeId.includes("golem") && head(cat).typeId.includes("jackalope"), "each wears their own form");

begin("pvp rules");
const pvpTarget = harness.join("Dee", { x: 0.5, y: 64, z: 4.5 });
await settle(15);
ui.answers.length = 0;
hold(alice, "plrace:focus_salamander");
while (data(alice).sel !== 0) await use(alice, true);
faceTo(alice, pvpTarget);
sim.pvp = false;
const dh = hp(pvpTarget);
await use(alice);
eq(hp(pvpTarget), dh, "abilities do not hurt players when pvp is off");
sim.pvp = true;

begin("race change policy & cleanup");
const cdPolicy = JSON.parse(world.getDynamicProperty("plrace:settings") ?? "{}");
cat.playerPermissionLevel = 0;
cat.commandPermissionLevel = 0;
answer.action(5); // main: Rite of Unbecoming (index varies) - may be blocked anyway
components.get("plrace:codex").onUse({ source: cat });
await settle(4);
ok(sim.log.messages.some((m) => m.p === cat.id && m.m.includes("Rite of Unbecoming needs")) || ui.shown.length > 0, "lineage change gated by the cooldown policy");
commands.get("plrace:setrace").cb({}, "none", [cat]);
await settle(3);
ok(!head(cat), "removing a lineage removes the form");
ok(!inv(cat).slots.some((s) => s?.typeId?.startsWith("plrace:focus")), "removing a lineage removes the focus");
eq(OW.getEntities({ type: "plrace:velvet_mirage" }).length, 0, "no stray illusions after removal");
void cdPolicy;

begin("crest infusion keeps enchantments across swaps");
const book = new ItemStack("minecraft:enchanted_book", 1);
book.getComponent("minecraft:enchantable").addEnchantment({ type: new M.EnchantmentType("protection"), level: 4 });
inv(bob).addItem(book);
answer.action(3); // main menu: Infuse Crest (Your lineage, Abilities, Veil, Infuse ...)
answer.action(0);
components.get("plrace:codex").onUse({ source: bob });
await settle(6);
ok(head(bob)?._ench.some((e) => e.id === "protection" && e.level === 4), "crest absorbed Protection IV");
commands.get("plrace:resetcooldowns").cb({}, [bob]);
await settle(2);
hold(bob, "plrace:focus_golem");
while (data(bob).sel !== 0) await use(bob, true);
await use(bob);
tickN(2);
eq(head(bob)?.typeId, "plrace:form_golem_siege", "configuration swap during edict");
ok(head(bob)?._ench.some((e) => e.id === "protection"), "enchantment carried across the swap");

begin("veil and manifest");
inv(bob).addItem(new ItemStack("minecraft:diamond_helmet", 1));
tickN(40);
answer.action(2); // Veil Form
components.get("plrace:codex").onUse({ source: bob });
await settle(4);
ok(!head(bob), "veiled: head slot free");
bob.getComponent("minecraft:equippable").setEquipment("Head", new ItemStack("minecraft:diamond_helmet", 1));
tickN(25);
eq(head(bob)?.typeId, "minecraft:diamond_helmet", "veiled golem can wear a real helmet");
answer.action(2); // Manifest Form
components.get("plrace:codex").onUse({ source: bob });
await settle(4);
ok(head(bob)?.typeId?.startsWith("plrace:form_golem"), "manifest restores the form");
ok(inv(bob).slots.some((s) => s?.typeId === "minecraft:diamond_helmet"), "the helmet is moved to the inventory, not lost");

// ======================================================================== race 004 Xenentoma
begin("xenentoma: assignment & form");
const xia = harness.join("Xia", { x: 200.5, y: 64, z: 0.5 });
await settle(12);
tickN(60);
await settle(10);
commands.get("plrace:setrace").cb({ sourceEntity: xia }, "xenentoma", [xia]);
await settle(4);
eq(data(xia).race, "004", "race 004 persisted");
eq(head(xia)?.typeId, "plrace:form_xenentoma", "xenentoma crest worn");
ok(inv(xia).slots.some((s) => s?.typeId === "plrace:focus_xenentoma"), "Sensillum Focus given");
hold(xia, "plrace:focus_xenentoma");
tickN(25);
ok(String(sim.log.actionbar.get(xia.id)).includes("Clarity"), "HUD shows Sensory Clarity");

begin("xenentoma: eyeless & vibration sense");
xia.addEffect("blindness", 200, { amplifier: 0 });
xia.addEffect("darkness", 200, { amplifier: 0 });
const xmover = mob("minecraft:zombie", 205.5, 0.5);
xmover._vel = { x: 0.12, y: 0, z: 0 };
const pingsBefore = sim.log.privateParticles.filter((x) => x.id === "plrace:vibration_ping").length;
tickN(21);
ok(!xia.getEffect("blindness") && !xia.getEffect("darkness"), "Blindness and Darkness are removed (no eyes)");
ok(sim.log.privateParticles.filter((x) => x.id === "plrace:vibration_ping").length > pingsBefore, "a moving creature on the ground sends a private vibration ping");
ok(sim.log.particles.every((x) => x.id !== "plrace:vibration_ping"), "vibration pings are private (never broadcast)");
ok(/Tremors 1/.test(String(sim.log.actionbar.get(xia.id))), "HUD counts the tremor");

begin("xenentoma: Foretarsal Survey");
const xstill = mob("minecraft:zombie", 203.5, 0.5); // still, within 5 blocks
const xfar = mob("minecraft:zombie", 209.5, 0.5); // still, 9 blocks: not felt
await use(xia);
tickN(2);
eq(head(xia)?.typeId, "plrace:form_xenentoma_survey", "survey form raises the forelimbs");
tickN(12);
ok(String(sim.log.actionbar.get(xia.id)).includes("Survey"), "survey reports vibrations on the HUD");
const traces = sim.log.privateParticles.filter((x) => x.id === "plrace:vibration_trace").length;
ok(traces > 0, "a still creature close by is felt faintly");
forceSave();
ok(cdLeft(xia, "foretarsal_survey") > 0, "survey cooldown spent");

begin("xenentoma: sensory overload");
world.afterEvents.explosion.fire({ dimension: OW, source: mob("minecraft:creeper", 202.5, 0.5), getImpactedBlocks: () => [] });
tickN(5);
ok(String(sim.log.actionbar.get(xia.id)).includes("OVERLOADED"), "an explosion 2 blocks away overloads the senses");
commands.get("plrace:resetcooldowns").cb({}, [xia]);
await settle(2);
await use(xia);
ok(String(sim.log.actionbar.get(xia.id)).includes("overloaded"), "survey refuses while overloaded");
forceSave();
eq(cdLeft(xia, "foretarsal_survey"), 0, "refused cast spends no cooldown");
tickN(20 * 12);
ok(String(sim.log.actionbar.get(xia.id)).includes("Clarity"), "clarity recovers over time");

begin("xenentoma: Exuvia Proxy");
await use(xia, true); // -> Exuvia
eq(data(xia).sel, 1, "selected ability 2");
const xz = mob("minecraft:zombie", 204.5, 0.5);
const proxiesBefore = OW.getEntities({ type: "plrace:exuvia" }).length;
await use(xia);
const shells = OW.getEntities({ type: "plrace:exuvia" });
eq(shells.length, proxiesBefore + 1, "the shed exuvia stays behind");
ok(shells[0]?._families.includes("plrace_proxy") && shells[0]?._families.includes("player"), "the shell is a decoy hostile mobs hunt");
ok(hp(xz) < 20, "nearby hostiles are provoked by the shell (it strikes them first)");
tickN(2);
eq(head(xia)?.typeId, "plrace:form_xenentoma_teneral", "teneral (freshly moulted) form");
ok(xia.getEffect("speed")?.amplifier === 1, "springs free with Speed II");
const tBefore = xia._health;
xia.applyDamage(5, { cause: "entityAttack", damagingEntity: xz });
ok(tBefore - xia._health >= 6 - 0.01, "teneral body takes +20% damage");
xia._health = 20;
tickN(82);
ok(!!xia.getEffect("resistance"), "the new cuticle hardens (Resistance)");
tickN(90);
eq(OW.getEntities({ type: "plrace:exuvia" }).length, proxiesBefore, "the exuvia expires and is removed");

begin("xenentoma: Interstitial Glide");
await use(xia, true); // -> Glide
const gz = mob("minecraft:zombie", xia.location.x, xia.location.z + 2);
xia.setRotation({ x: 0, y: 0 });
const gx0 = { ...xia.location };
await use(xia);
tickN(12);
ok(Math.hypot(xia.location.x - gx0.x, xia.location.z - gx0.z) > 3, "slides several blocks along the ground");
ok(!!gz.getEffect("slowness"), "a creature slipped past is tripped");
xia.isOnGround = false;
commands.get("plrace:resetcooldowns").cb({}, [xia]);
await settle(2);
await use(xia);
ok(String(sim.log.actionbar.get(xia.id)).includes("ground contact"), "glide refuses in mid-air");
xia.isOnGround = true;

begin("xenentoma: Anamorphic Surge");
await use(xia, true); // -> Surge
const xsz = mob("minecraft:zombie", xia.location.x, xia.location.z + 4);
faceTo(xia, xsz);
const xsHp = hp(xsz);
await use(xia);
tickN(2);
eq(head(xia)?.typeId, "plrace:form_xenentoma_surge", "surge form: the abdomen extends and arches");
tickN(30);
ok(xsHp - hp(xsz) >= 14, "three timed strikes at range (4 + 4 + 6)");
ok(!!xsz.getEffect("weakness"), "the final strike injects through the stylet (Weakness)");

begin("xenentoma: cleanup");
await use(xia, true); // -> Survey
await use(xia, true); // -> Exuvia
commands.get("plrace:resetcooldowns").cb({}, [xia]);
await settle(2);
await use(xia);
ok(OW.getEntities({ type: "plrace:exuvia" }).length > 0, "shell present");
xia.kill();
tickN(2);
eq(OW.getEntities({ type: "plrace:exuvia" }).length, 0, "the exuvia is removed when its owner dies");
harness.respawn(xia);
await settle(15);

// ======================================================================== race 005 Flying Spaghetti Monster
begin("spaghetti: assignment & form");
const pasta = harness.join("Pasta", { x: 400.5, y: 64, z: 0.5 });
await settle(12);
tickN(60);
await settle(10);
commands.get("plrace:setrace").cb({ sourceEntity: pasta }, "spaghetti", [pasta]);
await settle(4);
eq(data(pasta).race, "005", "race 005 persisted");
eq(head(pasta)?.typeId, "plrace:form_spaghetti", "spaghetti crest worn");
ok(inv(pasta).slots.some((s) => s?.typeId === "plrace:focus_spaghetti"), "Holy Colander Focus given");
hold(pasta, "plrace:focus_spaghetti");
tickN(25);
ok(String(sim.log.actionbar.get(pasta.id)).includes("Sauce"), "HUD shows Sauce");

begin("spaghetti: His Noodly Touch");
const nz1 = mob("minecraft:zombie", 400.5, 5.5);
faceTo(pasta, nz1);
const nzHp = hp(nz1);
const nzZ = nz1.location.z;
await use(pasta);
ok(hp(nz1) <= nzHp - 3, "the noodles wrap the target (3 damage)");
eq(nz1.getEffect("slowness")?.amplifier, 3, "the target is held (Slowness IV)");
ok(nz1.location.z < nzZ, "the target is pulled toward the monster");
ok(particles("plrace:noodle_strand") > 0, "a noodle strand extends to the target");
nz1.remove();
commands.get("plrace:resetcooldowns").cb({}, [pasta]);
await settle(2);
const drop = OW.spawnItem(new ItemStack("minecraft:apple", 1), { x: 400.5, y: 64, z: 4.5 });
pasta.setRotation({ x: 10, y: 0 });
await use(pasta);
ok(Math.abs(drop.location.z - pasta.location.z) < 1, "with no creature in reach the noodles gather dropped items");
commands.get("plrace:resetcooldowns").cb({}, [pasta]);
await settle(2);
drop.remove();
pasta.setRotation({ x: 0, y: 180 });
await use(pasta);
ok(String(sim.log.actionbar.get(pasta.id)).includes("Nothing within reach"), "nothing to touch -> clear failure, no cooldown");

begin("spaghetti: Al Dente Reversal");
await use(pasta, true); // -> Al Dente
await use(pasta);
tickN(2);
eq(head(pasta)?.typeId, "plrace:form_spaghetti_rigid", "the strands lock into the al dente lattice");
const sk = mob("minecraft:skeleton", 400.5, 3.5);
const pBefore = pasta._health;
pasta.applyDamage(6, { cause: "projectile", damagingEntity: sk });
eq(pasta._health, pBefore, "projectiles are stopped outright");
const brute = mob("minecraft:zombie", 400.5, 2.0);
const bruteHp = hp(brute);
pasta.applyDamage(10, { cause: "entityAttack", damagingEntity: brute });
ok(pBefore - pasta._health <= 4.01, "melee damage reduced by 60%");
ok(hp(brute) <= bruteHp - 4, "the first melee attacker is countered");
pasta._health = 20;
sk.remove();
brute.remove();
tickN(60);
eq(head(pasta)?.typeId, "plrace:form_spaghetti", "the lattice relaxes afterwards");

begin("spaghetti: Meatball Ricochet");
await use(pasta, true); // -> Meatballs
const mz1 = mob("minecraft:zombie", 403.5, 3.5);
const mz2 = mob("minecraft:zombie", 397.5, 4.5);
const h1 = hp(mz1);
const h2 = hp(mz2);
await use(pasta);
const balls = OW.getEntities({ type: "plrace:meatball" });
eq(balls.length, 2, "both meatballs detach");
tickN(2);
eq(head(pasta)?.typeId, "plrace:form_spaghetti_detached", "the body shows its empty meatball sockets");
const hb = pasta._health;
pasta.applyDamage(5, { cause: "entityAttack", damagingEntity: mz1 });
ok(hb - pasta._health >= 6 - 0.01, "softer while the meatballs are away (+20%)");
pasta._health = 20;
tickN(120);
ok(h1 - hp(mz1) + (h2 - hp(mz2)) >= 12, "the meatballs ricochet between targets (several 4-damage hits)");
ok(particles("plrace:sauce_splash") > 0, "sauce splashes on impact");
tickN(50);
eq(OW.getEntities({ type: "plrace:meatball" }).length, 0, "the meatballs return and are removed");
tickN(2);
eq(head(pasta)?.typeId, "plrace:form_spaghetti", "meatballs back in place");
mz1.remove();
mz2.remove();

begin("spaghetti: The Great Pasta Revelation");
await use(pasta, true); // -> Revelation
const rz = mob("minecraft:zombie", 400.5, 7.5);
const rzHp = hp(rz);
await use(pasta);
tickN(2);
eq(head(pasta)?.typeId, "plrace:form_spaghetti_revelation", "the body unfolds into the spiral vortex");
tickN(30);
ok(rz.location.z < 7.4, "enemies are dragged toward the vortex");
tickN(40);
ok(rzHp - hp(rz) >= 8, "the sauce shockwave lands");
ok(particles("plrace:sauce_wave") > 0, "sauce shockwave ring");
tickN(10);
ok(head(pasta)?.typeId !== "plrace:form_spaghetti_revelation", "the vortex folds back up");
rz.remove();

begin("spaghetti: sauce, fire and falling");
world.afterEvents.itemCompleteUse.fire({ source: pasta, itemStack: new ItemStack("minecraft:mushroom_stew", 1), useDuration: 0 });
world.afterEvents.itemCompleteUse.fire({ source: pasta, itemStack: new ItemStack("minecraft:mushroom_stew", 1), useDuration: 0 });
tickN(5);
ok(String(sim.log.actionbar.get(pasta.id)).includes("SAUCY"), "stews fill the sauce to SAUCY");
pasta.applyDamage(2, { cause: "fire" });
tickN(5);
eq(head(pasta)?.typeId, "plrace:form_spaghetti_brittle", "fire makes the pasta brittle");
pasta.isOnGround = false;
pasta.isSneaking = true;
pasta._vel = { x: 0, y: -0.6, z: 0 };
tickN(5);
ok(!!pasta.getEffect("slow_falling"), "sneaking in the air opens the noodle parachute");
pasta.isOnGround = true;
pasta.isSneaking = false;
pasta._vel = { x: 0, y: 0, z: 0 };
pasta._health = 20;

// ======================================================================== race 006 Nurariten (Unique)
const J = await import(path.join(RUN, "scripts/systems/jurisdiction.js")); // the add-on's own module instance
async function select(p, idx) {
  for (let k = 0; k < 6 && data(p).sel !== idx; k++) await use(p, true);
}
begin("nurariten: assignment & unique claim");
sim.time = 6000; // midday
const sov = harness.join("Sovereign", { x: 600.5, y: 64, z: 0.5 });
await settle(12);
tickN(60);
await settle(10);
const n_msgBefore = sim.log.messages.length;
commands.get("plrace:setrace").cb({ sourceEntity: sov }, "nurariten", [sov]);
await settle(4);
eq(data(sov).race, "006", "race 006 persisted");
eq(head(sov)?.typeId, "plrace:form_nurariten", "Nurariten crest worn");
ok(inv(sov).slots.some((x) => x?.typeId === "plrace:focus_nurariten"), "Mandate Shaku Focus given");
ok(sim.log.messages.slice(n_msgBefore).some((m) => m.p === "*" && String(m.m).includes("Uninvited Sovereign")), "the arrival of a Unique is announced to the world");
eq(JSON.parse(world.getDynamicProperty("plrace:unique") ?? "{}")["006"]?.id, sov.id, "the Unique claim is stored with the world");
hold(sov, "plrace:focus_nurariten");
tickN(25);
ok(String(sim.log.actionbar.get(sov.id)).includes("Midday Mandate"), "HUD shows the sun's mandate (midday)");
const n_rival = harness.join("Rival", { x: 640.5, y: 64, z: 40.5 });
await settle(12);
tickN(60);
await settle(10);
commands.get("plrace:setrace").cb({ sourceEntity: n_rival }, "nurariten", [n_rival]);
await settle(4);
ok(data(n_rival).race !== "006", "a second player cannot take a Unique lineage that is already held");
ok(sim.log.messages.some((m) => m.p === n_rival.id && String(m.m).includes("Could not assign")), "the refusal is explained");

begin("nurariten: Unannounced Arrival");
sov.setRotation({ x: 0, y: 0 });
const n_az = mob("minecraft:zombie", 600.5, 11.8);
for (let x = 598; x <= 603; x++) for (let z = 9; z <= 15; z++) sim.solids.add(`${x},67,${z}`); // a roof over the arrival
await use(sov);
ok(Math.abs(sov.location.z - 12.5) < 0.6, "the Sovereign steps 12 blocks along its gaze");
ok(particles("plrace:arrival_gate") >= 2, "gates of light mark departure and arrival");
tickN(2);
ok(!!n_az.getEffect("slowness"), "creatures at the arrival are pushed aside and slowed");
ok(!!sov.getEffect("absorption"), "arriving under a roof it is received as the master of the house");
for (let x = 598; x <= 603; x++) for (let z = 9; z <= 15; z++) sim.solids.delete(`${x},67,${z}`);
n_az.remove();
commands.get("plrace:resetcooldowns").cb({}, [sov]);
await settle(2);
sov.teleport({ x: 600.5, y: 64, z: 0.5 });
for (let x = 596; x <= 605; x++) for (let y = 64; y <= 67; y++) sim.solids.add(`${x},${y},5`); // a wall
await use(sov);
ok(sov.location.z < 5, "never through walls");
for (let x = 596; x <= 605; x++) for (let y = 64; y <= 67; y++) sim.solids.delete(`${x},${y},5`);
sov.teleport({ x: 600.5, y: 64, z: 0.5 });
sov.setRotation({ x: 0, y: 0 });

begin("nurariten: Edict of the Lowered Gaze");
await select(sov, 1); // -> Lowered Gaze
const n_gz = mob("minecraft:zombie", 600.5, 5.5);
const n_gBehind = mob("minecraft:zombie", 600.5, -4.5);
await use(sov);
eq(n_gz.getEffect("weakness")?.amplifier, 1, "enemies in the cone are weakened (II)");
eq(n_gz.getEffect("slowness")?.amplifier, 1, "and staggered (Slowness II)");
ok(n_gz.getRotation().x >= 50, "the creature bows its head");
ok(!n_gBehind.getEffect("weakness"), "nothing behind the Sovereign is affected");
ok(particles("plrace:judgment_seal") > 0, "a judgment seal appears above the judged");
n_gBehind.remove();
const n_gHead = (sov.getRotation().x);
sov.setRotation({ x: 0, y: 180 });
commands.get("plrace:resetcooldowns").cb({}, [sov]);
await settle(2);
await use(sov);
ok(String(sim.log.actionbar.get(sov.id)).includes("No one stands before you"), "no one in front -> clear failure, no cooldown");
sov.setRotation({ x: n_gHead, y: 0 });

begin("nurariten: Imperial Expulsion (marks)");
await select(sov, 3); // -> Expulsion
const n_exHp = hp(n_gz);
const n_exZ = n_gz.location.z;
await use(sov);
ok(n_exHp - hp(n_gz) >= 8 - 0.01, "5 damage +3 for its judgment mark");
ok(n_gz.location.z > n_exZ + 3, "thrown out of the Sovereign's presence");
n_gz.remove();
commands.get("plrace:resetcooldowns").cb({}, [sov]);
await settle(2);
sov.setRotation({ x: 0, y: 180 });
await use(sov);
ok(String(sim.log.actionbar.get(sov.id)).includes("No one here to expel"), "no target -> clear failure");
sov.setRotation({ x: 0, y: 0 });

begin("nurariten: The Uninvited Temple");
await select(sov, 2); // -> Temple
commands.get("plrace:resetcooldowns").cb({}, [sov]);
await settle(2);
const n_tz = mob("minecraft:zombie", 600.5, 3.5);
n_tz._maxHealth = 60;
n_tz._health = 60;
await use(sov);
tickN(2);
eq(head(sov)?.typeId, "plrace:form_nurariten_court", "the architecture on its back unfolds");
sov.applyDamage(5, { cause: "entityAttack", damagingEntity: n_tz });
tickN(4);
ok(String(sim.log.actionbar.get(sov.id)).includes("interrupted"), "a heavy blow interrupts the declaration (Judicial Weakness)");
const n_half = cdLeft(sov, "uninvited_temple");
forceSave();
ok(cdLeft(sov, "uninvited_temple") > 0 && cdLeft(sov, "uninvited_temple") < 35 * 20 * 0.6, "half of the cooldown is returned");
eq(OW.getEntities({ type: "plrace:celestial_gate" }).length, 0, "no court was declared");
sov._health = 20;
commands.get("plrace:resetcooldowns").cb({}, [sov]);
await settle(2);
await use(sov);
tickN(24);
eq(OW.getEntities({ type: "plrace:celestial_gate" }).length, 1, "the court's gate stands at its edge");
eq(head(sov)?.typeId, "plrace:form_nurariten_court", "inside its court it keeps the court form");
ok(String(sim.log.actionbar.get(sov.id)).includes("Court"), "HUD shows the court timer");
ok(!!n_tz.getEffect("slowness"), "enemies inside the court are slowed");
const n_tzHp = hp(n_tz);
n_tz.applyDamage(5, { cause: "entityAttack", damagingEntity: sov });
ok(Math.abs(n_tzHp - hp(n_tz) - 6) < 0.01, "+20% damage dealt inside its own court");
const n_before = sov._health;
sov.applyDamage(10, { cause: "entityAttack", damagingEntity: n_tz });
ok(Math.abs(n_before - sov._health - 8.5) < 0.01, "-15% damage taken inside its own court");
sov._health = 20;
tickN(70);
ok(particles("plrace:court_pillar") > 0 && particles("plrace:court_ring") > 0, "pillars of light and a ring mark the boundary");
const n_pil0 = particles("plrace:court_pillar"), n_ring0 = particles("plrace:court_ring");
tickN(40);
ok(particles("plrace:court_pillar") - n_pil0 >= 32 && particles("plrace:court_ring") - n_ring0 >= 2,
  "the boundary keeps drawing: 8 pillars every 0.4 s and the ring every second, whatever tick the court opened on");
ok(OW.getEntities({ type: "minecraft:zombie" }).length >= 1, "the court changes no blocks and summons nothing hostile");
// expel from inside the court: the creature is barred from returning
await select(sov, 3); // -> Expulsion
faceTo(sov, n_tz);
await use(sov);
const n_exiled = { ...n_tz.location };
ok(n_exiled.z > 7, "expelled out of the court");
n_tz.teleport({ x: 600.5, y: 64, z: 4.5 });
tickN(8);
ok(n_tz.location.z > 4.6, "an exiled creature is turned back at the threshold");
sov.setRotation({ x: 0, y: 0 });
// Broken Mandate: leaving your own court
sov.teleport({ x: 600.5, y: 64, z: -12.5 });
tickN(8);
eq(OW.getEntities({ type: "plrace:celestial_gate" }).length, 0, "leaving the court breaks it (gate dissolves)");
ok(!!sov.getEffect("weakness"), "Broken Mandate: the Sovereign is weakened");
tickN(5);
eq(head(sov)?.typeId, "plrace:form_nurariten", "the back architecture folds away");
n_tz.remove();
sov.teleport({ x: 600.5, y: 64, z: 0.5 });
sov.removeEffect("weakness");

begin("nurariten: HYAKUTEN CHUKO - interruption");
await select(sov, 4); // -> Hyakuten Chuko
commands.get("plrace:resetcooldowns").cb({}, [sov]);
await settle(2);
tickN(110);
const n_witness = harness.join("Witness", { x: 606.5, y: 64, z: 2.5 });
await settle(12);
tickN(60);
await settle(10);
sov.setRotation({ x: 0, y: 0 });
const n_fadesBefore = sim.log.fades.length;
await use(sov);
ok(sim.log.titles.some((t) => t.p === sov.id && String(t.t).includes("百天昼行")), "the title 百天昼行 is shown");
ok(sim.log.fades.length > n_fadesBefore, "one soft golden fade for those near");
ok(sov._fog.includes("plrace_hh") && n_witness._fog.includes("plrace_hh"), "a golden haze for the caster and witnesses only (no world sky change)");
ok(!sim.log.commands.some((c) => /time|weather|gamerule/.test(c.cmd)), "the world's time, weather and rules are untouched");
const n_skyGate = OW.getEntities({ type: "plrace:celestial_gate" });
eq(n_skyGate.length, 1, "a gate opens in the sky");
eq(n_skyGate[0]?._spawnEvent, "plrace:huge", "the sky gate is the vast form");
eq(sov.inputPermissions.isPermissionCategoryEnabled(InputPermissionCategory.LateralMovement), false, "the Sovereign stands still");
const n_iz = mob("minecraft:zombie", 600.5, 3.5);
sov.applyDamage(7, { cause: "entityAttack", damagingEntity: n_iz });
tickN(4);
ok(String(sim.log.actionbar.get(sov.id)).includes("interrupted"), "a heavy blow during Stage I interrupts it");
eq(OW.getEntities({ type: "plrace:celestial_gate" }).length, 0, "the sky closes");
ok(!sov._fog.includes("plrace_hh") && !n_witness._fog.includes("plrace_hh"), "every haze is removed");
eq(sov.inputPermissions.isPermissionCategoryEnabled(InputPermissionCategory.LateralMovement), true, "movement restored");
forceSave();
const n_ucd = cdLeft(sov, "hyakuten_chuko");
ok(n_ucd > 50 * 20 && n_ucd < 100 * 20, `half of the 180 s cooldown is returned (${(n_ucd / 20).toFixed(0)} s left)`);
sov._health = 20;
n_iz.remove();

begin("nurariten: HYAKUTEN CHUKO - five stages");
commands.get("plrace:resetcooldowns").cb({}, [sov]);
await settle(2);
sov.removeEffect("weakness");
tickN(110);
const n_foes = [mob("minecraft:zombie", 606.5, 3.5), mob("minecraft:zombie", 594.5, 4.5), mob("minecraft:skeleton", 600.5, 8.5), mob("minecraft:zombie", 603.5, -5.5)];
let n_foeHp;
for (const f of n_foes) {
  f._maxHealth = 80; // sturdy enough to live through all five stages
  f._health = 80;
}
await use(sov);
tickN(60);
eq(OW.getEntities({ type: "plrace:herald" }).length, 1, "II: two heralds descend with the decree");
ok(n_foes.every((f) => J.marksOn(f, sov.id) >= 1), "II: every enemy within 16 is judged (judgment mark)");
ok(n_foes.every((f) => (f.getEffect("slowness")?.amplifier ?? -1) >= 1), "II: and bows (Slowness II)");
tickN(20);
eq(OW.getEntities({ type: "plrace:procession" }).length, 8, "III: eight columns (96 attendants) march - one entity per column, no AI");
ok(OW.getEntities({ type: "plrace:procession" }).every((e) => Math.abs(Math.hypot(e.location.x - 600.5, e.location.z - 0.5) - 11.6) < 1.6), "III: the columns circle the Sovereign");
n_foeHp = n_foes.map(hp);
for (const f of n_foes) if (f.isValid) f.teleport({ x: 600.5 + (f.location.x - 600.5) * 0.1, y: 64, z: 0.5 + 11 });
tickN(40);
ok(n_foes.some((f, i) => hp(f) < n_foeHp[i]), "III: the procession tramples whoever stands in its way");
for (const [i, f] of n_foes.entries()) if (f.isValid) f.teleport({ x: 600.5 + [3, -3, 0, 2][i], y: 64, z: 0.5 + [2, 3, 5, -4][i] });
tickN(15);
eq(head(sov)?.typeId, "plrace:form_nurariten_throne", "IV: the throne without permission");
ok(!!sov.getEffect("resistance"), "IV: the enthroned Sovereign is protected");
ok(n_foes.every((f) => !!f.getEffect("weakness")), "IV: all within 12 are weakened");
const n_preStrike = n_foes.map(hp);
tickN(45);
ok(n_foes.every((f, i) => n_preStrike[i] - hp(f) >= 12 - 0.01 || hp(f) <= 0), "V: the Final Edict strikes 4 +4 per judgment mark");
ok(particles("plrace:seal_converge") > 0, "V: the seals converge on the judged");
tickN(40);
eq(OW.getEntities({ type: "plrace:procession" }).length + OW.getEntities({ type: "plrace:herald" }).length + OW.getEntities({ type: "plrace:celestial_gate" }).length, 0, "everything dissolves afterwards");
ok(!sov._fog.includes("plrace_hh") && !n_witness._fog.includes("plrace_hh"), "the haze is lifted for everyone");
eq(sov.inputPermissions.isPermissionCategoryEnabled(InputPermissionCategory.LateralMovement), true, "movement restored");
eq(head(sov)?.typeId, "plrace:form_nurariten", "the Sovereign returns to its usual form");
for (const f of n_foes) if (f.isValid) f.remove();

begin("nurariten: logout during the procession");
commands.get("plrace:resetcooldowns").cb({}, [sov]);
await settle(2);
tickN(110);
await use(sov);
tickN(90);
ok(OW.getEntities({ type: "plrace:procession" }).length === 8, "procession under way");
harness.leave(sov);
await settle(2);
tickN(4);
eq(OW.getEntities({ type: "plrace:procession" }).length + OW.getEntities({ type: "plrace:celestial_gate" }).length + OW.getEntities({ type: "plrace:herald" }).length, 0, "the caster's helpers are removed when it leaves");
ok(!n_witness._fog.includes("plrace_hh"), "the witness' haze is lifted");
harness.rejoin(sov);
await settle(14);
eq(sov.inputPermissions.isPermissionCategoryEnabled(InputPermissionCategory.LateralMovement), true, "movement restored on rejoin");
ok(!sov._fog.includes("plrace_hh"), "no haze left on rejoin");
eq(data(sov).race, "006", "the lineage and its Unique claim survive the relog");

begin("nurariten: the sun");
sim.time = 18000;
tickN(8);
eq(head(sov)?.typeId, "plrace:form_nurariten_nocturne", "at night it shines (Nocturne Radiance)");
hold(sov, "plrace:focus_nurariten");
tickN(30);
ok(String(sim.log.actionbar.get(sov.id) ?? "").includes("Nocturne"), "HUD shows the night (Nocturne)");
sim.time = 12500;
tickN(8);
hold(sov, "plrace:focus_nurariten");
await select(sov, 0);
commands.get("plrace:resetcooldowns").cb({}, [sov]);
await settle(2);
sov.teleport({ x: 600.5, y: 64, z: 0.5 });
sov.setRotation({ x: 0, y: 0 });
await use(sov);
const n_z1 = sov.location.z;
sov.setRotation({ x: 0, y: 180 });
await use(sov);
ok(n_z1 > 8 && sov.location.z < n_z1 - 8, "dusk is the hour of visiting: two arrivals in a row");
sim.time = 6000;
tickN(8);
commands.get("plrace:setrace").cb({ sourceEntity: sov }, "none", [sov]);
await settle(4);
ok(!JSON.parse(world.getDynamicProperty("plrace:unique") ?? "{}")["006"], "taking the Rite of Unbecoming releases the Unique claim");
commands.get("plrace:setrace").cb({ sourceEntity: n_rival }, "nurariten", [n_rival]);
await settle(4);
eq(data(n_rival).race, "006", "then another player may become Nurariten");
commands.get("plrace:setrace").cb({ sourceEntity: n_rival }, "none", [n_rival]);
await settle(4);
harness.leave(n_witness);
harness.leave(n_rival);

// ======================================================================== 007 The Unknown Dinosauroid (v1.4)
begin("dinosauroid: lineage");
const dino = harness.join("Dino", { x: 1000.5, y: 64, z: 0.5 });
await settle(12);
tickN(60);
await settle(10);
commands.get("plrace:setrace").cb({ sourceEntity: dino }, "dinosauroid", [dino]);
await settle(4);
eq(data(dino).race, "007", "race 007 persisted");
eq(head(dino)?.typeId, "plrace:form_dinosauroid", "dinosauroid crest worn");
ok(inv(dino).slots.some((s) => s?.typeId === "plrace:focus_dinosauroid"), "Fossil Quill Focus given");
hold(dino, "plrace:focus_dinosauroid");
const driftAt = [[0, "Plumed"], [1500, "Webbed"], [3000, "Toothed"], [4500, "Fanned"]];
for (const [t, name] of driftAt) {
  sim.time = t;
  tickN(25);
  ok(String(sim.log.actionbar.get(dino.id)).includes(name), `drift follows world time: ${name} at ${t}`);
}
sim.time = 6000;
sim.light = 3;
tickN(25);
eq(head(dino)?.typeId, "plrace:form_dinosauroid_night", "in the dark the display skin glows (night form)");
sim.light = 15;
tickN(25);

begin("dinosauroid: Hindwing Veer");
dino.setRotation({ x: 0, y: 0 });
const dz0 = dino.location.z;
await use(dino);
tickN(4);
ok(dino.location.z > dz0 + 2, "the hindwings throw the body forward");
ok(particles("plrace:veer_burst") > 0, "feathers and dust burst at take-off");
eq(dino.applyDamage(6, { cause: "fall" }), false, "no fall damage from the leap");

begin("dinosauroid: Crest of Misclassification");
dino.location = { x: 1000.5, y: 64, z: 0.5 };
await use(dino, true); // -> Crest
const dz1 = mob("minecraft:zombie", 1000.5, 4.5);
await use(dino);
tickN(2);
eq(head(dino)?.typeId, "plrace:form_dinosauroid_display", "crest, pouch and fans open (display form)");
eq(dz1.getEffect("slowness")?.amplifier, 1, "the witness is misclassified (Slowness II)");
ok(dz1.getEffect("weakness"), "and weakened");
ok(particles("plrace:crest_wave") > 0 && particles("plrace:misclass_mark") > 0, "display wave and the broken cladogram mark");
const realRandom = Math.random;
Math.random = () => 0;
const dhp = dino._health;
dino.applyDamage(5, { cause: "entityAttack", damagingEntity: dz1 });
eq(dino._health, dhp, "a misclassified creature's blow can miss outright");
Math.random = realRandom;

begin("dinosauroid: Sickle Testament");
await use(dino, true); // -> Sickle
dino.setRotation({ x: 0, y: 0 });
dz1.location = { x: 1000.5, y: 64, z: 2.6 };
const dz2 = mob("minecraft:zombie", 1001.5, 2.2);
const m1 = hp(dz1);
const m2 = hp(dz2);
await use(dino);
tickN(6);
ok(m1 - hp(dz1) >= 10 - 0.01, "the misclassified victim is opened up (10 damage)");
eq(dz1.getEffect("slowness")?.amplifier, 3, "and pinned (Slowness IV)");
ok(m2 - hp(dz2) >= 6 - 0.01 && m2 - hp(dz2) < 10, "an ordinary target takes the plain strike");
if (dz1.isValid) dz1.remove();
if (dz2.isValid) dz2.remove();

begin("dinosauroid: Taxonomic Error");
await use(dino, true); // -> Error
await use(dino);
tickN(2);
eq(head(dino)?.typeId, "plrace:form_dinosauroid_overflow", "every structure activates (overflow form)");
ok(dino.getEffect("speed") && dino.getEffect("jump_boost"), "enhanced mobility");
const dz3 = mob("minecraft:zombie", 1000.5, 3.5);
tickN(45);
ok(dz3.getEffect("slowness"), "the aura misclassifies creatures that come close");
tickN(220);
eq(head(dino)?.typeId, "plrace:form_dinosauroid", "the body folds back afterwards");
ok(dino.getEffect("slowness") && dino.getEffect("weakness"), "and is spent (Slowness, Weakness)");
if (dz3.isValid) dz3.remove();
dino._health = 20;

// ======================================================================== 008 Bathyas, the Sun-Impaled [Unique] (v1.4)
begin("bathyas: lineage");
const bat = harness.join("Bat", { x: 1100.5, y: 64, z: 0.5 });
await settle(12);
tickN(60);
await settle(10);
commands.get("plrace:setrace").cb({ sourceEntity: bat }, "bathyas", [bat]);
await settle(4);
eq(data(bat).race, "008", "race 008 persisted");
ok(JSON.parse(world.getDynamicProperty("plrace:unique") ?? "{}")["008"], "the Unique claim is recorded");
eq(head(bat)?.typeId, "plrace:form_bathyas", "impaled form worn");
hold(bat, "plrace:focus_bathyas");
tickN(25);
ok(String(sim.log.actionbar.get(bat.id)).includes("Stability"), "HUD shows Stability and Photic Strain");
ok(bat.getEffect("health_boost") && bat.getEffect("water_breathing"), "the impaled core: Health Boost; breathes water");

begin("bathyas: Lure of the Impaled Sun");
bat.setRotation({ x: 0, y: 0 });
const bz1 = mob("minecraft:zombie", 1100.5, 6.5);
const bzZ = bz1.location.z;
await use(bat);
tickN(2);
eq(head(bat)?.typeId, "plrace:form_bathyas_lure", "the sun blazes, a hand shields the eyes (lure form)");
ok(bz1.getEffect("slowness") && bz1.getEffect("weakness"), "the lured creature is Sun-Marked (slowed, weakened)");
ok(bz1.location.z < bzZ, "and drawn toward the light");
ok(particles("plrace:lure_pulse") > 0, "a warped ring of light");

begin("bathyas: Goblin Maw Rush");
await use(bat, true); // -> Maw
faceTo(bat, bz1);
const bh = hp(bz1);
bat._health = 12;
await use(bat);
tickN(14);
ok(bh - hp(bz1) >= 11 - 0.01, "the jaw shoots out: a Sun-Marked victim takes 11");
ok(bat._health > 12, "and the bite feeds Bathyas");
ok(particles("plrace:maw_bite") > 0, "teeth and a dark splash");
bat._health = 20;

begin("bathyas: Isopod Bastion");
await use(bat, true); // -> Bastion
await use(bat);
tickN(2);
eq(head(bat)?.typeId, "plrace:form_bathyas_bastion", "the plates close (bastion form)");
eq(bat.getEffect("resistance")?.amplifier, 1, "Resistance II");
bz1.location = { x: 1100.5, y: 64, z: 2.0 };
const bh2 = hp(bz1);
bat.applyDamage(4, { cause: "entityAttack", damagingEntity: bz1 });
tickN(2);
ok(bh2 - hp(bz1) >= 3 - 0.01, "a blow on the plates answers with a counterpulse");
tickN(130);
if (bz1.isValid) bz1.remove();

begin("bathyas: Draw the Sun");
await use(bat, true); // -> Draw
await use(bat);
tickN(16);
eq(inv(bat).getItem(bat.selectedSlotIndex)?.typeId, "plrace:sun_sword", "the sun is in the hand: a real weapon item");
eq(inv(bat).getItem(bat.selectedSlotIndex)?.lockMode, "inventory", "it cannot be dropped");
eq(inv(bat).slots.some((x) => x?.typeId === "plrace:focus_bathyas"), true, "the focus moved to a free slot");
tickN(2);
eq(head(bat)?.typeId, "plrace:form_bathyas_unshackled", "the open wound glows (unshackled form)");
forceSave();
eq(cdLeft(bat, "draw_the_sun"), 0, "drawing is free - the cooldown waits for the return");
tickN(25);
ok(bat.getEffect("strength") && bat.getEffect("speed"), "unshackled: Strength and Speed");
const st0 = data(bat).res.stab;
tickN(400);
forceSave();
ok(data(bat).res.stab < st0 - 10, "Stability drains while the sun is out");
inv(bat).setItem(30, new ItemStack("plrace:sun_sword", 1));
tickN(25);
eq(inv(bat).slots.filter((x) => x?.typeId === "plrace:sun_sword").length, 1, "a second sun never survives");
hold(bat, "plrace:focus_bathyas");
await use(bat);
tickN(2);
eq(inv(bat).slots.some((x) => x?.typeId === "plrace:sun_sword"), false, "Return the Sun: the blade goes home");
eq(head(bat)?.typeId, "plrace:form_bathyas", "the impaled form is back");
forceSave();
ok(cdLeft(bat, "draw_the_sun") > 0, "the cooldown starts on the return");

begin("bathyas: recovery");
commands.get("plrace:resetcooldowns").cb({}, [bat]);
await settle(2);
await use(bat);
tickN(16);
eq(data(bat).st.sun, "drawn", "drawn again");
bat.kill();
await settle(2);
harness.respawn(bat);
await settle(6);
tickN(25);
eq(inv(bat).slots.some((x) => x?.typeId === "plrace:sun_sword"), false, "death returns the sun to the chest (no sword left)");
ok(data(bat).st.sun !== "drawn", "and the state is impaled again");
bat._health = 20;
commands.get("plrace:resetcooldowns").cb({}, [bat]);
await settle(2);
hold(bat, "plrace:focus_bathyas");
await use(bat);
tickN(16);
harness.leave(bat);
await settle(2);
harness.rejoin(bat);
await settle(10);
tickN(25);
eq(inv(bat).slots.some((x) => x?.typeId === "plrace:sun_sword"), false, "logout returns the sun as well");

begin("bathyas: Abyssal Daybreak");
hold(bat, "plrace:focus_bathyas");
commands.get("plrace:resetcooldowns").cb({}, [bat]);
await settle(2);
await use(bat, true); // -> Daybreak (fifth)
const bz3 = mob("minecraft:zombie", 1100.5, 5.5);
const bz4 = mob("minecraft:zombie", 1104.5, 0.5);
const b3 = hp(bz3);
await use(bat);
eq(bat.inputPermissions.isPermissionCategoryEnabled(InputPermissionCategory.LateralMovement), false, "Bathyas stands his ground");
tickN(34);
ok(bat._fog.includes("plrace_ab"), "Abyssal Extinction: the deep closes in (a local dark haze)");
tickN(40);
ok(particles("plrace:sunrise_pillar") > 0, "Impossible Sunrise: a pillar of daylight");
tickN(40);
ok(particles("plrace:leviathan") >= 3, "Leviathan silhouettes pass through the light");
tickN(40);
ok(particles("plrace:solar_execution") > 0, "Solar Execution");
ok(b3 - hp(bz3) >= 10 - 0.01, "Abyssal Daybreak: 10+ damage to everything within 9 blocks");
tickN(40);
ok(!bat._fog.includes("plrace_ab"), "the haze lifts afterwards");
eq(bat.inputPermissions.isPermissionCategoryEnabled(InputPermissionCategory.LateralMovement), true, "movement restored");
ok(bat.getEffect("slowness") && bat.getEffect("weakness"), "and Bathyas is spent");
tickN(60);
if (bz3.isValid) bz3.remove();
if (bz4.isValid) bz4.remove();
commands.get("plrace:setrace").cb({ sourceEntity: bat }, "none", [bat]);
await settle(4);
ok(!JSON.parse(world.getDynamicProperty("plrace:unique") ?? "{}")["008"], "leaving the lineage releases the Unique claim");
harness.leave(bat);

// ======================================================================== 009 Octamyces Undecimus (v1.4)
begin("octamyces: lineage");
const octa = harness.join("Octa", { x: 1200.5, y: 64, z: 0.5 });
await settle(12);
tickN(60);
await settle(10);
commands.get("plrace:setrace").cb({ sourceEntity: octa }, "octamyces", [octa]);
await settle(4);
eq(data(octa).race, "009", "race 009 persisted");
eq(head(octa)?.typeId, "plrace:form_octamyces", "octamyces crest worn");
hold(octa, "plrace:focus_octamyces");

begin("octamyces: Parallax Sporeveil");
const oz1 = mob("minecraft:zombie", 1203.5, 2.5);
const ogol = mob("minecraft:iron_golem", 1197.5, 2.5);
await use(octa);
tickN(2);
eq(head(octa)?.typeId, "plrace:form_octamyces_sporeveil", "the gills unfold (sporeveil form)");
ok(oz1.getEffect("slowness"), "the zombie is parallax-infected");
ok(!ogol.getEffect("slowness"), "an iron golem's senses are not fooled");
Math.random = () => 0;
const oh = octa._health;
octa.applyDamage(4, { cause: "entityAttack", damagingEntity: oz1 });
eq(octa._health, oh, "an infected creature strikes a version of you that is not there");
Math.random = realRandom;
const echoes0 = particles("plrace:parallax_echo");
for (let k = 0; k < 6; k++) {
  oz1.location = { x: 1203.5, y: 64, z: 2.5 + k * 0.4 };
  tickN(8);
}
ok(particles("plrace:parallax_echo") > echoes0, "the infected leave false afterimages where they stood");
if (ogol.isValid) ogol.remove();

begin("octamyces: The Eye That Records");
await use(octa, true); // -> Record
oz1.location = { x: 1200.5, y: 64, z: 8.5 };
faceTo(octa, oz1);
await use(octa);
tickN(2);
eq(head(octa)?.typeId, "plrace:form_octamyces_record", "the eye focuses (record form)");
for (let k = 0; k < 20; k++) {
  oz1.location = { x: 1200.5 + k * 0.3, y: 64, z: 8.5 - k * 0.2 };
  tickN(4);
}
tickN(20);
ok(/recorded §f(\d+)/.test(String(sim.log.actionbar.get(octa.id))) && Number(/recorded §f(\d+)/.exec(String(sim.log.actionbar.get(octa.id)))[1]) >= 10, "the path is recorded point by point");

begin("octamyces: Hyphal Offset");
await use(octa, true); // -> Offset
octa.location = { x: 1200.5, y: 64, z: 0.5 };
octa.setRotation({ x: 0, y: 180 });
sim.solids.add("1200,64,-3");
sim.solids.add("1200,65,-3");
const oz0 = octa.location.z;
await use(octa);
ok(octa.location.z < oz0 - 1.4 && octa.location.z > -3, `the body is elsewhere, stopped short of the wall (z ${octa.location.z.toFixed(2)})`);
ok(OW.getEntities({ type: "plrace:hyphal_echo" }).length === 1, "an echo lingers where it was");
tickN(70);
eq(OW.getEntities({ type: "plrace:hyphal_echo" }).length, 0, "the echo collapses after 3 s");
sim.solids.delete("1200,64,-3");
sim.solids.delete("1200,65,-3");
commands.get("plrace:resetcooldowns").cb({}, [octa]);
await settle(2);
octa.setOnFire(5);
await use(octa);
ok(String(sim.log.actionbar.get(octa.id)).includes("cannot resonate"), "no offset while burning");
octa.extinguishFire?.();
octa._fire = 0;

begin("octamyces: The Eleventh Frame");
await use(octa, true); // -> Frame
const strikes0 = particles("plrace:frame_strike");
const of1 = hp(oz1);
await use(octa);
eq(octa.inputPermissions.isPermissionCategoryEnabled(InputPermissionCategory.LateralMovement), false, "the eye stops; the body is still");
tickN(2);
eq(head(octa)?.typeId, "plrace:form_octamyces_frame", "the eleven rings open (frame form)");
tickN(72);
ok(particles("plrace:frame_strike") - strikes0 >= 6, "the network strikes along the recorded path");
ok(of1 - hp(oz1) >= 6 - 0.01, "the observed creature is struck where it walked");
eq(octa.inputPermissions.isPermissionCategoryEnabled(InputPermissionCategory.LateralMovement), true, "movement restored");
tickN(8);
ok(String(sim.log.actionbar.get(octa.id)).includes("no recording"), "the recording is spent");
if (oz1.isValid) oz1.remove();
harness.leave(octa);

// ======================================================================== display check (v1.3.1)
begin("display check");
const dia = harness.join("Dia", { x: 900.5, y: 64, z: 0.5 });
await settle(6);
commands.get("plrace:setrace").cb({ sourceEntity: dia }, "spaghetti", [dia]);
await settle(4);
eq(head(dia)?.typeId, "plrace:form_spaghetti", "the Spaghetti Monster's crest is worn");
ui.answers.length = 0;
const camsBefore = sim.log.cameras.length;
answer.action(7); // main codex: Display Check
answer.action(0); // intro: Start
answer.modal([false, false, false, false, true, false, false, false, false]); // could not see: 005
answer.modal([false]); // the still twin of 005 was visible
commands.get("plrace:codex").cb({ sourceEntity: dia });
await settle(2);
const dcSeen = [];
for (let i = 0; i < 10 * 60 + 40; i++) {
  tickN(1);
  await new Promise((r) => setTimeout(r, 0));
  const id = head(dia)?.typeId;
  if (id && dcSeen[dcSeen.length - 1] !== id) dcSeen.push(id);
}
await settle(4);
const dcOrder = ["salamander", "golem", "jackalope", "xenentoma", "spaghetti", "nurariten", "dinosauroid", "bathyas", "octamyces"].map((k) => `plrace:form_${k}`);
ok(dcOrder.every((id, i) => dcSeen.indexOf(id) >= 0 && (i === 0 || dcSeen.indexOf(id) > dcSeen.indexOf(dcOrder[i - 1]))), `every lineage's body is shown in turn (${dcSeen.join(" > ")})`);
ok(dcSeen.includes("plrace:form_spaghetti_static"), "a body reported missing is shown again as its still twin");
const dcCams = sim.log.cameras.slice(camsBefore).filter((c) => c.p === dia.id);
ok(dcCams.filter((c) => c.preset === "minecraft:free").length >= 10 && dcCams[dcCams.length - 1]?.clear, "a camera in front of the player, cleared afterwards");
eq(head(dia)?.typeId, "plrace:form_spaghetti", "the player's own form is back");
eq(dia.inputPermissions.isPermissionCategoryEnabled(InputPermissionCategory.LateralMovement), true, "movement restored after the check");
const dcMsg = sim.log.messages.filter((x) => x.p === dia.id).map((x) => x.m).join("\n");
ok(/hidden: §f005/.test(dcMsg) && /still hidden without animation: §fnone/.test(dcMsg), "the result names what was hidden, with and without animation");
ok(dcMsg.includes("%plrace.rp_version%"), "the result names the resource-pack version the client resolves");
harness.leave(dia);

// ======================================================================== summary
const warns = sim.log.warns.concat();
begin("script health");
eq(warns.length, 0, `no listener/job exceptions (${warns.slice(0, 3).join(" | ")})`);
if (process.env.REPORT) {
  for (const [name, r] of perSection) console.log(`| ${name} | ${r.pass}/${r.pass + r.fail} | ${r.msgs.join("; ")} |`);
}
console.log(`\n${passed} assertions passed, ${failures.length} failed`);
for (const f of failures) console.log("  FAIL", f);
fs.rmSync(RUN, { recursive: true, force: true });
process.exit(failures.length ? 1 : 0);
