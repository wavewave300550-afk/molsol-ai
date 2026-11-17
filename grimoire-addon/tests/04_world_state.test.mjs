// World-level effects of ED06 (src/lib/terraform.ts, atmos.ts, cinema.ts): the real ground it turns into
// the ancient world, the caster's fog, the world's time of day, the camera shot - each must come back
// exactly as it was: after a normal cast, when the caster leaves, after a crash, with chunks unloaded,
// with overlapping casts, and whatever other players or commands do in the meantime.
export default function ({ mock, test, eq, ok }) {
  const { world, system, tick, addPlayer, addMob, reset, constructs, changedBlocks, problems, stats, getDimension } = mock;
  const GY = mock.GROUND_Y;
  const SE = system.afterEvents.scriptEventReceive;
  const send = (id, message = "", sourceEntity) => SE.emit({ id, message, sourceEntity });
  const TAG = "grimoire_ed6";
  const T = { shotFrom: 121, shotTo: 216, held: 300, seal: 1098, end: 1176 };   // ED06 scene ticks (see the spell's timeline)

  let t0 = 0;
  function fresh() { reset(); t0 = system.currentTick; }
  function caster(name, loc = { x: 0.5, y: GY, z: 0.5 }) {
    const p = addPlayer(name, loc);
    p.rotation = { x: 12, y: 0 };
    return p;
  }
  function enemies(c = { x: 0.5, z: 0.5 }) {
    return [[0, 15], [3, 17], [-3, 16], [1.5, 19]].map(([x, z]) => addMob("minecraft:zombie", { x: c.x + x, y: GY, z: c.z + z }, 5000));
  }
  /** Cast ED06 (force-cast: no input or cooldown) and run `ticks` scene ticks, calling `each(sceneTick)` every tick. */
  function run(p, ticks, each) {
    send("grimoire:cast", "ed06", p);
    for (let t = 0; t < ticks; t++) { tick(1); each?.(t); }
  }
  const naturalTime = () => 6000 + (system.currentTick - t0);
  const kinds = () => { const m = {}; for (const [, id] of changedBlocks()) m[id] = (m[id] ?? 0) + 1; return m; };
  const noProblems = (what) => eq(problems.join(" || "), "", `${what} problems:`);

  test("ed06 living ground: rings of moss, ferns, basalt and magma grow in, then the ground goes back exactly", () => {
    fresh();
    const p = caster("Ground");
    enemies();
    let peak = 0, mid = {};
    run(p, T.end + 40, (t) => {
      const n = changedBlocks().length;
      if (n > peak) { peak = n; }
      if (t === 400) mid = kinds();
    });
    ok(peak >= 1200, `only ${peak} blocks of living ground`);
    for (const id of ["minecraft:moss_block", "minecraft:podzol", "minecraft:basalt", "minecraft:magma", "minecraft:mud", "minecraft:fern", "minecraft:short_grass"]) {
      ok((mid[id] ?? 0) > 0, `no ${id} in the ancient world: ${JSON.stringify(mid)}`);
    }
    eq(changedBlocks().length, 0, "ground left changed:");
    eq(constructs().length, 0, "entities left:");
    ok(stats.maxGroundEditsPerTick <= 80, `${stats.maxGroundEditsPerTick} ground changes in one tick`);
    ok(stats.maxGroundSubchunksPerTick <= 4, `${stats.maxGroundSubchunksPerTick} chunk sections of ground rebuilt in one tick`);
    eq([...mock.worldDynamic.keys()].filter((k) => k === "grim:tod").join(","), "", "time record left behind:");
    console.log(`         ed06 ground: peak ${peak} cells, ${stats.blockEdits} edits; ground max ${stats.maxGroundEditsPerTick}/tick in ` +
      `${stats.maxGroundSubchunksPerTick} sections (all blocks: ${stats.maxEditsPerTick}/tick, ${stats.maxSubchunksPerTick} sections)`);
    noProblems("ground");
  });

  test("ed06 living ground on hills, and natural grass and flowers come back", () => {
    fresh();
    mock.setTerrain((x, z) => GY + Math.round(2.5 * Math.sin(x * 0.21) + 2 * Math.cos(z * 0.17)));
    mock.setCover((x, z) => ((x * 7 + z * 13) % 5 === 0 ? "minecraft:short_grass" : (x * 3 + z) % 11 === 0 ? "minecraft:poppy" : undefined));
    const p = caster("Hills", { x: 0.5, y: mock.heightAt(0, 0), z: 0.5 });
    let peak = 0;
    run(p, T.end + 40, () => { peak = Math.max(peak, changedBlocks().length); });
    ok(peak >= 900, `only ${peak} blocks of living ground on hills`);
    eq(changedBlocks().length, 0, "hills left changed:");
    noProblems("hills");
  });

  test("ed06 leaves a player's builds and containers alone (and the ground right next to them)", () => {
    fresh();
    const d = getDimension();
    const build = [];
    for (let x = 3; x <= 6; x++) { d.fixture({ x, y: GY - 1, z: 4 }, "minecraft:oak_planks"); build.push([x, GY - 1, 4, "minecraft:oak_planks"]); }
    d.fixture({ x: -5, y: GY, z: 2 }, "minecraft:chest"); build.push([-5, GY, 2, "minecraft:chest"]);
    d.fixture({ x: -8, y: GY - 1, z: -3 }, "minecraft:cobblestone"); build.push([-8, GY - 1, -3, "minecraft:cobblestone"]);
    const near = new Set();
    for (const [x, , z] of build) for (const [ox, oz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) near.add(`${x + ox},${z + oz}`);
    const fixtures = new Set(build.map(([x, y, z]) => `${x},${y},${z}`));
    const p = caster("Builder");
    let touched = "";
    run(p, T.end + 40, (t) => {
      if (t % 20) return;
      for (const [k] of changedBlocks()) {
        if (fixtures.has(k)) continue;
        const [x, y, z] = k.split(",").map(Number);
        if (near.has(`${x},${z}`) && (y === GY - 1 || y === GY)) touched = k;   // the ground layer and the plant layer
      }
    });
    eq(touched, "", "a cell next to a build was changed:");
    for (const [x, y, z, id] of build) eq(d.blockAt(x, y, z), id, `build at ${x},${y},${z}:`);
    eq(changedBlocks().length, build.length, "anything but the builds left changed:");
    noProblems("builds");
  });

  test("ed06 fog, camera shot, inputs and the sunset are all handed back (daylight cycle on)", () => {
    fresh();
    const p = caster("Atmos");
    enemies();
    let fogSeen = 0, sunset = false, camDuring = false, locked = false, hurtInShot = 0;
    run(p, T.end + 40, (t) => {
      if (p.fogSettings.getTags().includes(TAG)) fogSeen++;
      const tod = world.getTimeOfDay();
      if (t >= T.held && t < T.seal && Math.abs(tod - 12000) > 15) sunset = `t=${t} tod=${tod}`;
      if (t === T.held) ok(Math.abs(tod - 12000) <= 15, `not at golden hour at t=${t}: ${tod}`);
      if (t === 160) {
        camDuring = p.cam.active;
        locked = [1, 4, 5, 6].every((c) => p.inputPermissions.isPermissionCategoryEnabled(c) === false);
        const h0 = p.health; p.applyDamage(6); hurtInShot = h0 - p.health;
      }
    });
    ok(fogSeen > 600, `fog only on ${fogSeen} ticks`);
    eq(sunset, false, "time drifted off golden hour while held:");
    ok(camDuring, "no camera shot at the all-hearts beat");
    ok(locked, "inputs not paused during the shot");
    eq(hurtInShot, 0, "caster hurt during the shot:");
    eq(p.fogSettings.getTags().includes(TAG), false, "fog left on the caster");
    eq(p.cam.active, false, "camera not handed back");
    ok(p.cam.clears >= 1, "camera never cleared");
    for (const c of [1, 4, 5, 6]) eq(p.inputPermissions.isPermissionCategoryEnabled(c), true, `input category ${c} left off:`);
    eq(p.getDynamicProperty("grim:cam"), undefined, "camera flag left");
    eq(p.getDynamicProperty("grim:fog"), undefined, "fog flag left");
    const dt = world.getAbsoluteTime() - naturalTime();
    ok(Math.abs(dt) <= 2, `world clock off by ${dt} ticks after the cast`);
    noProblems("atmosphere");
  });

  test("ed06 with the daylight cycle off: the exact original time comes back", () => {
    fresh();
    world.gameRules.doDayLightCycle = false;
    world.setAbsoluteTime(30000);                       // day 1, 06:00
    const p = caster("Frozen");
    let reached = false;
    run(p, T.end + 40, (t) => { if (t === T.held) reached = world.getTimeOfDay() === 12000; });
    ok(reached, "never reached golden hour");
    eq(world.getAbsoluteTime(), 30000, "time not restored exactly:");
    noProblems("cycle off");
  });

  test("ed06 at night rewinds to golden hour and still gives the clock back", () => {
    fresh();
    world.setAbsoluteTime(24000 * 3 + 19000);           // night of day 3
    const start = world.getAbsoluteTime(), at0 = system.currentTick;
    const p = caster("Night");
    let min = Infinity;
    run(p, T.end + 40, () => { min = Math.min(min, world.getAbsoluteTime()); });
    ok(min < start, "the night was not rewound toward the sunset");
    const dt = world.getAbsoluteTime() - (start + (system.currentTick - at0));
    ok(Math.abs(dt) <= 2, `clock off by ${dt}`);
    noProblems("night");
  });

  test("ed06 lets go of the clock for good when someone else changes the time", () => {
    fresh();
    const p = caster("Command");
    let at = 0;
    run(p, T.end + 40, (t) => { if (t === 400) { world.setAbsoluteTime(50000); at = system.currentTick; } });
    eq(world.getAbsoluteTime(), 50000 + (system.currentTick - at), "the spell overwrote someone else's time:");
    noProblems("time command");
  });

  test("ed06 leaves the time alone when another player is far away (fog only)", () => {
    fresh();
    const p = caster("Near");
    caster("Far", { x: 400.5, y: GY, z: 0.5 });
    let fog = false;
    run(p, T.end + 40, (t) => { if (t === 400) fog = p.fogSettings.getTags().includes(TAG); });
    eq(mock.clock.sets, 0, "the clock was changed with a far player online:");
    ok(fog, "no fog");
    noProblems("far player");
  });

  test("ed06 skips the camera shot when an enemy is right next to the caster", () => {
    fresh();
    const p = caster("Close");
    addMob("minecraft:zombie", { x: 2.5, y: GY, z: 1.5 }, 5000);
    run(p, T.end + 40);
    eq(p.cam.sets, 0, "camera shot played with an enemy 2 blocks away:");
    noProblems("close enemy");
  });

  test("ed06 caster leaving mid-shot: ground and time back at once; fog, camera and inputs on the next join", () => {
    fresh();
    const p = caster("Leaver");
    enemies();
    run(p, 170);
    ok(p.cam.active, "expected to be in the shot at t=170");
    p.isValid = false; p.dimension.entities.delete(p);
    tick(5);
    eq(changedBlocks().length, 0, "ground left changed after the caster left:");
    eq(constructs().length, 0, "entities left after the caster left:");
    const dt = world.getAbsoluteTime() - naturalTime();
    ok(Math.abs(dt) <= 2, `clock off by ${dt} after the caster left`);
    // rejoin: the engine keeps the player's fog stack and camera across a save
    p.isValid = true; p.dimension.entities.add(p);
    world.afterEvents.playerSpawn.emit({ player: p, initialSpawn: true });
    tick(15);
    eq(p.fogSettings.getTags().includes(TAG), false, "fog still on the player after rejoining");
    eq(p.cam.active, false, "camera still detached after rejoining");
    for (const c of [1, 4, 5, 6]) eq(p.inputPermissions.isPermissionCategoryEnabled(c), true, `input ${c} still off after rejoining:`);
    noProblems("leave");
  });

  // A real 26.62 server killed hard saved a chunk's blocks and the entities in it within ~10 s, but world
  // dynamic properties (and the clock) only every half minute: the world that loads after a crash can
  // have the spell's blocks without any world-level record of them.
  test("ed06 hard crash mid-cast (chunks saved, world data older): the next load still puts every block back", () => {
    fresh();
    const level = mock.snapshotWorld();                  // the world data as last saved, before the cast
    const p = caster("Crash");
    enemies();
    let snap, cells = 0;
    run(p, T.end + 40, (t) => { if (t === 420) { snap = mock.snapshotWorld(); cells = changedBlocks().length; } });
    ok(cells > 1000, `only ${cells} cells changed at the crash`);
    const markers = snap.dims.overworld.e.filter((e) => e.typeId === "grimoire:ledger").length;
    ok(markers >= 4, `only ${markers} chunk markers at the crash`);
    mock.restoreWorld(snap, level);                      // load the world as the crash left it
    eq(changedBlocks().length, cells, "crash state not loaded");
    eq(mock.worldDynamic.has("grim:tod"), false, "world data should be the older save (no time record)");
    mock.setUnloaded((x) => x >= 16);                    // the chunks east of x = 16 are not loaded yet
    send("grimoire:recover");
    const left = changedBlocks().length;
    ok(left > 0 && left < cells, `expected only the unloaded part left, ${left} of ${cells}`);
    mock.setUnloaded(null);                              // the player walks over: those chunks (and markers) load
    tick(3);
    eq(changedBlocks().length, 0, "blocks left after the crash:");
    eq(constructs().length, 0, "markers or entities left after recovery:");
    noProblems("hard crash");
  });

  test("ed06 save and quit mid-cast: ground, temporary blocks and the clock come back on the next load", () => {
    fresh();
    const p = caster("Quit");
    enemies();
    let snap, snapTick = 0;
    run(p, T.end + 40, (t) => { if (t === 700) { snap = mock.snapshotWorld(); snapTick = system.currentTick; } });
    mock.restoreWorld(snap);                             // everything saved together, then loaded again
    ok(changedBlocks().length > 1000, "nothing to recover");
    send("grimoire:recover");
    tick(3);
    eq(changedBlocks().length, 0, "blocks left after save and quit:");
    eq(constructs().length, 0, "markers or entities left:");
    // the time record is at most 20 ticks old: the clock comes back to (start + elapsed at the save) within that
    const dt = world.getAbsoluteTime() - (6000 + (snapTick - t0));
    ok(dt <= 2 && dt >= -22, `clock off by ${dt} after recovery`);
    eq([...mock.worldDynamic.keys()].filter((k) => k === "grim:tod").join(","), "", "time record left:");
    noProblems("save and quit");
  });

  test("ed06 holds its blocks: they cannot be broken or blown up while the spell runs", () => {
    fresh();
    const p = caster("Guard");
    run(p, 400);
    const d = getDimension();
    const [k] = changedBlocks().find(([, id]) => id === "minecraft:moss_block") ?? [];
    ok(k, "no moss to test on");
    const [x, y, z] = k.split(",").map(Number);
    const ev = { cancel: false, block: d.getBlock({ x, y, z }), player: p };
    world.beforeEvents.playerBreakBlock.emit(ev);
    ok(ev.cancel, "breaking a spell block was not cancelled");
    const out = { cancel: false, block: d.getBlock({ x: 60, y: GY - 1, z: 60 }), player: p };
    world.beforeEvents.playerBreakBlock.emit(out);
    eq(out.cancel, false, "breaking an ordinary block was cancelled");
    let kept;
    const blocks = [d.getBlock({ x, y, z }), d.getBlock({ x: 60, y: GY - 1, z: 60 })];
    world.beforeEvents.explosion.emit({ getImpactedBlocks: () => blocks, setImpactedBlocks: (b) => { kept = b; } });
    eq(kept?.length, 1, "explosion still destroys spell blocks:");
    for (let i = 0; i < T.end; i++) tick(1);
    eq(changedBlocks().length, 0, "ground left changed:");
    noProblems("guard");
  });

  test("ed06 two overlapping casts share the ground and the clock and put everything back", () => {
    fresh();
    const a = caster("First"), b = caster("Second", { x: 10.5, y: GY, z: -6.5 });
    enemies();
    send("grimoire:cast", "ed06", a);
    for (let t = 0; t < 150; t++) tick(1);
    let peak = 0;
    send("grimoire:cast", "ed06", b);
    for (let t = 0; t < T.end + 60; t++) { tick(1); peak = Math.max(peak, changedBlocks().length); }
    ok(peak > 1200, `overlap peak ${peak}`);
    ok(peak <= 3000 + 200, `overlap over budget: ${peak}`);
    eq(changedBlocks().length, 0, "overlap left ground changed:");
    const dt = world.getAbsoluteTime() - naturalTime();
    ok(Math.abs(dt) <= 2, `clock off by ${dt} after overlapping casts`);
    for (const q of [a, b]) eq(q.fogSettings.getTags().includes(TAG), false, `fog left on ${q.name}`);
    noProblems("overlap");
  });
}
