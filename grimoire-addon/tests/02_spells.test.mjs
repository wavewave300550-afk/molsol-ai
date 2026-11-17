// Smoke + behaviour tests for all eighteen spells (headless).  Every spell is cast through the
// real input path, simulated until its scene ends, and checked for: no script warnings, no unknown
// entity / particle / sound ids, entities and temporary blocks fully cleaned up, and (for
// offensive spells) real damage dealt to hostile mobs.
const SPELLS = {
  dw01: { off: true }, dw02: { off: true }, dw03: { off: true }, dw04: { off: false }, dw05: { off: true }, dw06: { off: true },
  dn01: { off: true }, dn02: { off: true }, dn03: { off: false }, dn04: { off: true }, dn05: { off: true }, dn06: { off: true },
  ed01: { off: true }, ed02: { off: true }, ed03: { off: true }, ed04: { off: true }, ed05: { off: true }, ed06: { off: true },
};
const SLOT = { dw: 0, dn: 1, ed: 2 };
const BOOK = { dw: "grimoire:divine_word", dn: "grimoire:dream_nightmare", ed: "grimoire:elemental_dragon" };

export default function ({ mock, test, eq, ok, arg }) {
  // eslint-disable-next-line no-unused-vars
  const { world, tick, addPlayer, addMob, ItemStack, reset, constructs, tempBlocks, problems, stats } = mock;
  const A = world.afterEvents;
  const only = arg ? arg.split(",") : null;

  function castThroughInput(id, withMobs, groundY) {
    reset();
    mock.setTerrain(groundY === undefined ? null : () => groundY);
    const gy = groundY ?? mock.GROUND_Y;
    const pre = id.slice(0, 2), idx = Number(id.slice(2)) - 1;
    const p = addPlayer("Caster_" + id + (withMobs ? "" : "_solo"), { x: 0.5, y: gy, z: 0.5 });
    p.rotation = { x: 12, y: 0 }; // looking slightly down toward +Z
    p.hotbar[0] = new ItemStack(BOOK[pre]);
    const mobs = [];
    if (withMobs) {
      const spots = [[0, 9], [3, 11], [-3, 10], [1.5, 13], [-2, 14], [5, 9]];
      for (const [x, z] of spots) mobs.push(addMob("minecraft:zombie", { x: x + 0.5, y: gy, z: z + 0.5 }, 5000));
    }
    tick(2);
    for (let i = 0; i < idx; i++) { p.isSneaking = true; tick(1); p.isSneaking = false; tick(1); }
    A.itemStartUse.emit({ source: p, itemStack: p.hotbar[0], useDuration: 1 });
    tick(14);
    ok(constructs().length >= 0);
    A.itemReleaseUse.emit({ source: p, itemStack: p.hotbar[0], useDuration: 1 });
    A.itemStopUse.emit({ source: p, itemStack: p.hotbar[0], useDuration: 0 });
    tick(1);
    const cd = JSON.parse(p.getDynamicProperty("grim:cd") ?? "{}");
    ok(cd[id] !== undefined, `${id} did not activate (no cooldown started)`);
    return { p, mobs };
  }

  function runToEnd(maxTicks = 3600) {
    let peak = 0, ticks = 0, sawActors = false;
    for (; ticks < maxTicks; ticks++) {
      tick(1);
      const n = constructs().length;
      peak = Math.max(peak, n);
      if (n > 0) sawActors = true;
      if (sawActors && n === 0 && ticks > 20) break;
    }
    return { peak, ticks, sawActors };
  }

  for (const [id, info] of Object.entries(SPELLS)) {
    if (only && !only.includes(id)) continue;
    test(`${id}: full cast with enemies - runs clean, hits, and cleans up`, () => {
      const { p, mobs } = castThroughInput(id, true);
      const r = runToEnd();
      tick(40);
      ok(r.sawActors, `${id} spawned no spell entities (still a stub?)`);
      eq(constructs().length, 0, `${id} left entities behind:`);
      eq(tempBlocks().length, 0, `${id} left temporary blocks behind:`);
      eq(problems.join(" || "), "", `${id} problems:`);
      const dealt = mobs.reduce((s, m) => s + (5000 - m.health), 0);
      if (info.off) ok(dealt > 0, `${id} dealt no damage to enemies`);
      ok(p.health === 20, `${id} hurt its own caster`);
      ok(r.ticks < 3500, `${id} never ended`);
      // screen effects are well formed (ED06 shakes its impacts and flashes its climax and its seal)
      for (const c of p.commands) ok(/^camerashake add @s \d+(\.\d+)? \d+(\.\d+)? positional$/.test(c), `${id} bad command: ${c}`);
      for (const f of p.fades) ok(["red", "green", "blue"].every((k) => f.fadeColor[k] >= 0 && f.fadeColor[k] <= 1), `${id} bad fade colour`);
      if (id === "ed06") {
        ok(p.commands.length >= 6, `ed06 shook the screen only ${p.commands.length} times`);
        ok(p.fades.length >= 2, `ed06 flashed ${p.fades.length} times`);
      }
      console.log(`         ${id}: ${r.ticks} ticks, peak ${r.peak} entities, ${Math.round(dealt)} dmg, ${stats.particles} particles, ${stats.sounds} sounds`);
    });
    test(`${id}: cast with no enemies - runs clean and cleans up`, () => {
      castThroughInput(id, false);
      const r = runToEnd();
      tick(40);
      eq(constructs().length, 0, `${id} left entities behind:`);
      eq(tempBlocks().length, 0, `${id} left temporary blocks behind:`);
      eq(problems.join(" || "), "", `${id} problems:`);
    });
    test(`${id}: superflat world (ground 4 blocks above the bottom) - nothing goes missing`, () => {
      const { mobs } = castThroughInput(id, true, -60);
      const r = runToEnd();
      tick(40);
      mock.setTerrain(null);
      ok(r.sawActors, `${id} spawned no spell entities on superflat`);
      eq(problems.join(" || "), "", `${id} problems on superflat:`);
      eq(constructs().length, 0, `${id} left entities behind on superflat:`);
      eq(tempBlocks().length, 0, `${id} left temporary blocks behind on superflat:`);
      if (info.off) ok(mobs.reduce((s, m) => s + (5000 - m.health), 0) > 0, `${id} dealt no damage on superflat`);
    });
    test(`${id}: caster leaving mid-spell removes everything`, () => {
      const { p } = castThroughInput(id, true);
      tick(45);
      p.isValid = false; p.dimension.entities.delete(p);
      tick(5);
      eq(constructs().length, 0, `${id} left entities after caster left:`);
      eq(tempBlocks().length, 0, `${id} left temporary blocks after caster left:`);
      eq(problems.join(" || "), "", `${id} problems:`);
    });
  }
}
