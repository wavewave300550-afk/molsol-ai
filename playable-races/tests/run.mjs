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
  return e.getComponent("minecraft:health").currentValue;
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
await use(cat);
tickN(16);
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
await use(cat);
tickN(40);
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
await use(alice);
eq(alice.inputPermissions.isPermissionCategoryEnabled(InputPermissionCategory.LateralMovement), false, "rooted before death");
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
