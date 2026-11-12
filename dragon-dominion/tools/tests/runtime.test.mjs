// Runtime tests for the compiled behavior-pack scripts (run after the build):
//     node --import ./tools/tests/mock/register.mjs --test tools/tests/runtime.test.mjs
// "@minecraft/server" resolves to tools/tests/mock/server.mjs. The creature and
// tier definitions below are test doubles only; they never ship in the packs.
import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";
import { __mock, Entity, EntityInitializationCause } from "@minecraft/server";

const SCRIPTS = new URL("../../build/behavior_packs/dragon_dominion/scripts/", import.meta.url);
const load = (path) => import(new URL(path, SCRIPTS).href);

const { VERSION } = await load("config.js");
const { TierRegistry } = await load("tiers/registry.js");
const { CreatureRegistry } = await load("creatures/registry.js");
const { CreatureRuntime } = await load("creatures/runtime.js");
const { PHASE_DYNAMIC_PROPERTY } = await load("encounters/runtime.js");
const { useAbility } = await load("abilities/use.js");
const { Cooldowns } = await load("core/cooldowns.js");
const { showActionBar } = await load("encounters/hud.js");

const logs = { info: [], warn: [], error: [] };
console.log = (...a) => logs.info.push(a.join(" "));
console.warn = (...a) => logs.warn.push(a.join(" "));
console.error = (...a) => logs.error.push(a.join(" "));

const TIER = { id: "test_tier", rank: 1, nameKey: "tier.dragon_dominion.test_tier.name" };

/** Builds a runtime for test definitions; `calls` records every hook invocation in order. */
function setup(definitions, tiers = [TIER]) {
  const tierRegistry = new TierRegistry(tiers);
  const registry = new CreatureRegistry(definitions, tierRegistry);
  assert.deepEqual(registry.problems, []);
  const runtime = new CreatureRuntime(registry, (id) => tierRegistry.get(id));
  __mock.defineEntityTypes(...registry.typeIds());
  runtime.start();
  return runtime;
}

function recorder(calls, name) {
  return (creature, ...rest) => calls.push([name, creature.entity.id, ...rest.filter((r) => typeof r === "string")]);
}

beforeEach(() => {
  for (const list of Object.values(logs)) list.length = 0;
});

// Must run first: main.js executes once per process.
test("main.js loads with no content: status command only, no entity hooks, no tick loop", async () => {
  await load("main.js");
  assert.equal(__mock.subscriptions("entitySpawn").length, 0);
  assert.equal(__mock.runCount, 0);
  __mock.startup();
  const status = __mock.commands.get("dragon_dominion:status");
  assert.ok(status, "status command registered");
  assert.equal(status.definition.cheatsRequired, false);
  const result = status.callback({});
  assert.equal(result.status, 0);
  assert.match(result.message, new RegExp(`v${VERSION.replace(/\./g, "\\.")}`));
  assert.match(result.message, /tiers: 0, creatures: 0/);
  __mock.loadWorld();
  assert.ok(logs.info.some((l) => l.includes(`v${VERSION} loaded`)));
  assert.deepEqual(logs.error, []);
});

test("tier registry orders by rank and reports invalid tiers", () => {
  const tiers = new TierRegistry([
    { id: "high", rank: 3, nameKey: "k.high" },
    { id: "low", rank: 1, nameKey: "k.low" },
    { id: "low", rank: 2, nameKey: "k.dupe" },
    { id: "Bad Id", rank: 0, nameKey: "k.bad" },
    { id: "nan", rank: Number.NaN, nameKey: "k.nan" },
  ]);
  assert.deepEqual(tiers.all().map((t) => t.id), ["low", "high"]);
  assert.ok(tiers.compare("low", "high") < 0);
  assert.throws(() => tiers.compare("low", "missing"), /unknown tier/);
  assert.equal(tiers.problems.length, 3);
});

test("creature registry rejects invalid definitions with specific problems", () => {
  const tiers = new TierRegistry([TIER]);
  const registry = new CreatureRegistry(
    [
      { typeId: "minecraft:ender_dragon", tier: "test_tier" },
      { typeId: "dragon_dominion:no_tier", tier: "missing" },
      { typeId: "dragon_dominion:bad_interval", tier: "test_tier", tickInterval: 0 },
      { typeId: "dragon_dominion:dupe_ability", tier: "test_tier", abilities: [{ id: "a", cooldownTicks: 1, execute() {} }, { id: "a", cooldownTicks: -1, execute() {} }] },
      { typeId: "dragon_dominion:bad_encounter", tier: "test_tier", encounter: { phases: [], participantRadius: 0, phaseProperty: "phase" } },
      { typeId: "dragon_dominion:ok", tier: "test_tier" },
      { typeId: "dragon_dominion:ok", tier: "test_tier" },
    ],
    tiers,
  );
  const text = registry.problems.join("\n");
  for (const fragment of ["must be \"dragon_dominion:", "unknown tier \"missing\"", "tickInterval", "ability \"a\" is defined more than once",
    "cooldownTicks", "at least one phase", "participantRadius", "phaseProperty", "\"dragon_dominion:ok\": defined more than once"]) {
    assert.ok(text.includes(fragment), `missing problem: ${fragment}\n${text}`);
  }
  assert.deepEqual(registry.typeIds(), ["dragon_dominion:ok"]);
});

test("lifecycle hooks, tick interval, entity events, death and removal", () => {
  __mock.reset();
  const calls = [];
  const runtime = setup([{
    typeId: "dragon_dominion:t_life",
    tier: "test_tier",
    tickInterval: 2,
    onSpawn: (c, cause) => calls.push(["spawn", c.entity.id, cause, c.tier.id]),
    onTick: recorder(calls, "tick"),
    onHurt: recorder(calls, "hurt"),
    onDeath: recorder(calls, "death"),
    onEntityEvent: recorder(calls, "event"),
  }]);
  assert.equal(__mock.subscriptions("entityHurt")[0].options.entityTypes[0], "dragon_dominion:t_life");
  __mock.loadWorld();

  const entity = __mock.spawn("dragon_dominion:t_life");
  __mock.spawn("minecraft:zombie");
  assert.deepEqual(calls, [["spawn", entity.id, "Spawned", "test_tier"]]);
  assert.equal(runtime.activeCount, 1);

  calls.length = 0;
  __mock.tick(10);
  assert.equal(calls.filter((c) => c[0] === "tick").length, 5);

  calls.length = 0;
  __mock.hurt(entity);
  __mock.trigger(entity, "dragon_dominion:enrage");
  __mock.kill(entity);
  __mock.tick(4);
  assert.deepEqual(calls, [["hurt", entity.id], ["event", entity.id, "dragon_dominion:enrage"], ["death", entity.id]]);
  assert.equal(runtime.activeCount, 0, "dead creatures stop ticking");

  const second = __mock.spawn("dragon_dominion:t_life");
  assert.equal(runtime.activeCount, 1);
  __mock.remove(second);
  assert.equal(runtime.activeCount, 0);
  assert.deepEqual(logs.error, []);
});

test("world load: entities already loaded are tracked without onSpawn, missing entity types are reported", () => {
  __mock.reset();
  const calls = [];
  const tiers = new TierRegistry([TIER]);
  const registry = new CreatureRegistry([
    { typeId: "dragon_dominion:t_present", tier: "test_tier", onSpawn: recorder(calls, "spawn") },
    { typeId: "dragon_dominion:t_absent", tier: "test_tier" },
  ], tiers);
  const runtime = new CreatureRuntime(registry, (id) => tiers.get(id));
  __mock.defineEntityTypes("dragon_dominion:t_present");
  runtime.start(); // early execution: must not touch world APIs (the mock throws if it does)
  __mock.addEntity("dragon_dominion:t_present", { dimension: "minecraft:nether" });
  __mock.loadWorld();
  assert.equal(runtime.activeCount, 1);
  assert.deepEqual(calls, []);
  assert.ok(logs.error.some((l) => l.includes("dragon_dominion:t_absent") && l.includes("no such entity")));

  const reloaded = __mock.spawn("dragon_dominion:t_present", EntityInitializationCause.Loaded);
  assert.equal(runtime.activeCount, 2);
  assert.deepEqual(calls, [], "cause Loaded is a reload, not a spawn");
  assert.ok(runtime.get(reloaded));
});

function bossDefinition(typeId, calls, { property = "dragon_dominion:phase" } = {}) {
  let enraged = false;
  const phase = (id, next) => ({
    id,
    onEnter: recorder(calls, `enter:${id}`),
    onExit: recorder(calls, `exit:${id}`),
    next: next ? () => (enraged ? next : undefined) : undefined,
  });
  return {
    enrage: () => (enraged = true),
    definition: {
      typeId,
      tier: "test_tier",
      encounter: {
        phases: [phase("first", "second"), phase("second")],
        participantRadius: 16,
        phaseProperty: property,
        onStart: recorder(calls, "start"),
        onDefeat: (c, enc) => calls.push(["defeat", enc.phase.id, enc.participants().map((p) => p.name).join(",")]),
      },
    },
  };
}

test("encounter: start, persisted phase transitions, client property mirror, defeat with participants", () => {
  __mock.reset();
  const calls = [];
  const boss = bossDefinition("dragon_dominion:t_boss", calls);
  const runtime = setup([boss.definition]);
  __mock.loadWorld();
  __mock.addPlayer("near", { location: { x: 5, y: 64, z: 0 } });
  __mock.addPlayer("far", { location: { x: 500, y: 64, z: 0 } });

  const entity = __mock.spawn("dragon_dominion:t_boss", "Spawned", { properties: ["dragon_dominion:phase"] });
  assert.deepEqual(calls.map((c) => c[0]), ["start", "enter:first"]);
  assert.equal(entity.getDynamicProperty(PHASE_DYNAMIC_PROPERTY), "first");
  assert.equal(entity.getProperty("dragon_dominion:phase"), 0);
  assert.equal(runtime.get(entity).encounter.phase.id, "first");

  __mock.tick(3);
  assert.equal(runtime.get(entity).encounter.phase.id, "first");
  boss.enrage();
  __mock.tick(1);
  assert.deepEqual(calls.map((c) => c[0]), ["start", "enter:first", "exit:first", "enter:second"]);
  assert.equal(entity.getDynamicProperty(PHASE_DYNAMIC_PROPERTY), "second");
  assert.equal(entity.getProperty("dragon_dominion:phase"), 1);

  __mock.kill(entity);
  assert.deepEqual(calls.at(-1), ["defeat", "second", "near"]);
  assert.deepEqual(logs.error, []);
});

test("encounter: a reloaded boss resumes its saved phase without re-running onStart/onEnter", () => {
  __mock.reset();
  const calls = [];
  const runtime = setup([bossDefinition("dragon_dominion:t_resume", calls).definition]);
  __mock.loadWorld();
  const saved = new Entity("dragon_dominion:t_resume", { properties: ["dragon_dominion:phase"] });
  saved.setDynamicProperty(PHASE_DYNAMIC_PROPERTY, "second");
  __mock.load(saved);
  assert.equal(runtime.get(saved).encounter.phase.id, "second");
  assert.equal(saved.getProperty("dragon_dominion:phase"), 1);
  assert.deepEqual(calls, []);

  const unknown = __mock.addEntity("dragon_dominion:t_resume", { properties: ["dragon_dominion:phase"] });
  unknown.setDynamicProperty(PHASE_DYNAMIC_PROPERTY, "removed_phase");
  __mock.load(unknown);
  assert.equal(runtime.get(unknown).encounter.phase.id, "first", "unknown saved phase restarts the encounter");
  assert.deepEqual(calls.map((c) => c[0]), ["start", "enter:first"]);
});

test("encounter: invalid transitions and undeclared properties are reported, not fatal", () => {
  __mock.reset();
  const calls = [];
  const runtime = setup([{
    typeId: "dragon_dominion:t_badphase",
    tier: "test_tier",
    encounter: { phases: [{ id: "only", next: () => "nowhere" }], participantRadius: 8, phaseProperty: "dragon_dominion:undeclared" },
    onTick: recorder(calls, "tick"),
  }]);
  __mock.loadWorld();
  const entity = __mock.spawn("dragon_dominion:t_badphase");
  __mock.tick(2);
  assert.equal(runtime.get(entity).encounter.phase.id, "only");
  assert.equal(calls.length, 2, "creature keeps ticking");
  assert.ok(logs.error.some((l) => l.includes('unknown phase "nowhere"')));
  assert.ok(logs.error.some((l) => l.includes("dragon_dominion:undeclared")));
});

test("errors in one creature are isolated and rate-limited", () => {
  __mock.reset();
  let healthyTicks = 0;
  setup([
    { typeId: "dragon_dominion:t_broken", tier: "test_tier", onTick: () => { throw new Error("boom"); } },
    { typeId: "dragon_dominion:t_healthy", tier: "test_tier", onTick: () => healthyTicks++ },
  ]);
  __mock.loadWorld();
  __mock.spawn("dragon_dominion:t_broken");
  __mock.spawn("dragon_dominion:t_healthy");
  __mock.tick(10);
  assert.equal(healthyTicks, 10);
  const reports = logs.error.filter((l) => l.includes("dragon_dominion:t_broken onTick failed: boom"));
  assert.equal(reports.length, 3);
  assert.match(reports[2], /further errors from this source are suppressed/);
});

test("abilities: cooldown gate, canUse, unknown ids and failures", () => {
  __mock.reset();
  let executed = 0;
  let allowed = true;
  const runtime = setup([{
    typeId: "dragon_dominion:t_caster",
    tier: "test_tier",
    abilities: [
      { id: "strike", cooldownTicks: 20, canUse: () => allowed, execute: () => executed++ },
      { id: "faulty", cooldownTicks: 5, execute: () => { throw new Error("bad ability"); } },
    ],
  }]);
  __mock.loadWorld();
  const creature = runtime.get(__mock.spawn("dragon_dominion:t_caster"));
  assert.equal(useAbility(creature, "strike"), "used");
  assert.equal(useAbility(creature, "strike"), "on_cooldown");
  assert.equal(creature.cooldowns.remaining("strike"), 20);
  __mock.tick(19);
  assert.equal(useAbility(creature, "strike"), "on_cooldown");
  __mock.tick(1);
  allowed = false;
  assert.equal(useAbility(creature, "strike"), "blocked");
  allowed = true;
  assert.equal(useAbility(creature, "strike"), "used");
  assert.equal(executed, 2);
  assert.equal(useAbility(creature, "nope"), "unknown");
  assert.equal(useAbility(creature, "faulty"), "failed");
  assert.equal(useAbility(creature, "faulty"), "on_cooldown", "a failing ability still waits out its cooldown");
});

test("cooldowns: start, clear, validation", () => {
  let now = 100;
  const cd = new Cooldowns(() => now);
  assert.equal(cd.isReady("x"), true);
  cd.start("x", 10);
  now += 9;
  assert.equal(cd.remaining("x"), 1);
  now += 1;
  assert.equal(cd.isReady("x"), true);
  cd.start("y", 5);
  cd.clear();
  assert.equal(cd.isReady("y"), true);
  assert.throws(() => cd.start("z", 1.5), RangeError);
});

test("hud: messages reach valid players and skip players who left", () => {
  __mock.reset();
  const here = __mock.addPlayer("here");
  const gone = __mock.addPlayer("gone");
  gone.isValid = false;
  showActionBar([here, gone], "Phase two");
  assert.deepEqual(here.actionBar, ["Phase two"]);
  assert.deepEqual(gone.actionBar, []);
});
