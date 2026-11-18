/**
 * Vesperra-specific scenarios: armour regions, Heirs, cocoon anchors, molting.
 */
export default async function suite({ test, check, begin, toPhase, untilTop, forceAttack, place, run, count, Bot, TOP }) {
  await test("vesperra: armour regions are hit by aim, crack, break and expose", async () => {
    const ctx = await begin("vesperra");
    const { enc, players } = ctx;
    toPhase(ctx, 1, []);
    const p = players[0];
    const armor = enc.controller.armor;
    const swing = (aim, dmg = 10) => {
      const eye = { x: p._loc.x, y: p._loc.y + 1.62, z: p._loc.z };
      const v = { x: aim.x - eye.x, y: aim.y - eye.y, z: aim.z - eye.z };
      const n = Math.hypot(v.x, v.y, v.z);
      p._aim = { x: v.x / n, y: v.y / n, z: v.z / n };
      enc.boss._hurtAt = -100;
      const before = enc.boss._health.currentValue;
      enc.boss.applyDamage(dmg, { cause: "entityAttack", damagingEntity: p });
      run(1);
      return before - enc.boss._health.currentValue;
    };
    const taken = (dmg, mult) => dmg * mult * ctx.CONFIG.bosses.vesperra.damageTaken;
    // stand on her left, aim at the left shell
    place(p, enc, 3.2, -90);
    const hpL = armor.hp.l;
    let d = swing(armor.anchor("l"));
    check(armor.hp.l === hpL - 10 && armor.hp.r === 70 && armor.hp.c === 55, `left plate ${armor.hp.l}, right ${armor.hp.r}, crown ${armor.hp.c}`);
    check(Math.abs(d - taken(10, 0.35)) < 1e-6, `damage through an intact plate was ${d}`);
    // from the same spot, aim past the shell at her body core from the front instead
    place(p, enc, 3.2, 0);
    d = swing({ x: enc.boss._loc.x, y: enc.boss._loc.y + 3.5, z: enc.boss._loc.z });
    check(armor.hp.l === hpL - 10, "a frontal body hit damaged the left plate");
    check(Math.abs(d - taken(10, 0.75)) < 1e-6, `body hit multiplier wrong (${d})`);
    // crown from the front
    d = swing(armor.anchor("c"));
    check(armor.hp.c === 45, `crown plate ${armor.hp.c} after a hit aimed at it`);
    // right shell is not reachable from the left side: the core is in the way
    place(p, enc, 3.2, -90);
    swing(armor.anchor("r"));
    check(armor.hp.r === 70, "right shell was damaged through the body from the left side");
    // crack then break the left shell
    while (armor.hp.l > 35) swing(armor.anchor("l"));
    check(enc.boss.getProperty("abm:armor_l") === 1, "cracked state not shown");
    const staggers = count("stagger");
    while (armor.hp.l > 0) swing(armor.anchor("l"));
    check(enc.boss.getProperty("abm:armor_l") === 2, "destroyed state not shown");
    check(count("stagger") === staggers + 1, "breaking a plate did not stagger her");
    d = swing(armor.anchor("l"));
    check(Math.abs(d - taken(10, 1.4)) < 1e-6, `exposed flank multiplier wrong (${d})`);
    check(enc.boss.getProperty("abm:armor_r") === 0 && enc.boss.getProperty("abm:armor_c") === 0, "other regions changed state");
    // projectile impact position decides the region
    const arrow = { isValid: true, location: armor.anchor("r") };
    enc.boss._hurtAt = -100;
    enc.boss.applyDamage(8, { cause: "projectile", damagingEntity: p, damagingProjectile: arrow });
    run(1);
    check(armor.hp.r === 62, `arrow on the right shell left it at ${armor.hp.r}`);
    return "left/right/crown independently tracked";
  });

  await test("vesperra: phase II keeps destroyed armour destroyed and intact armour protective", async () => {
    const ctx = await begin("vesperra");
    const { enc, players } = ctx;
    toPhase(ctx, 1, []);
    const armor = enc.controller.armor;
    armor.hp.l = 0;
    enc.force("phase2");
    untilTop(enc, TOP.P2, []);
    check(armor.broken("l") && !armor.broken("r"), "armour state changed across the transition");
    check(enc.boss.getProperty("abm:phase") === 2, "phase property not synced");
    const p = players[0];
    const hit = (side) => {
      place(p, enc, 3.4, side);
      const a = armor.anchor(side < 0 ? "l" : "r");
      const eye = { x: p._loc.x, y: 65.62, z: p._loc.z };
      const v = { x: a.x - eye.x, y: a.y - eye.y, z: a.z - eye.z };
      const n = Math.hypot(v.x, v.y, v.z);
      p._aim = { x: v.x / n, y: v.y / n, z: v.z / n };
      enc.boss._hurtAt = -100;
      const before = enc.boss._health.currentValue;
      enc.boss.applyDamage(10, { cause: "entityAttack", damagingEntity: p });
      run(1);
      return before - enc.boss._health.currentValue;
    };
    const k = ctx.CONFIG.bosses.vesperra.damageTaken;
    check(Math.abs(hit(-90) - 10 * 1.5 * k) < 1e-6, "open wound multiplier in phase II");
    check(Math.abs(hit(90) - 10 * 0.55 * k) < 1e-6, "intact shell multiplier in phase II");
  });

  await test("vesperra: Heirs are capped, guard exposed flanks, expire and clean up", async () => {
    const ctx = await begin("vesperra");
    const { enc, players } = ctx;
    const bot = new Bot(players[0], enc, { mode: "dodge" });
    toPhase(ctx, 1, [bot]);
    enc.controller.armor.hp.l = 0;
    const def = enc.controller.attacks.find((a) => a.id === "the_heirs");
    forceAttack(enc, def, [bot]);
    check(enc.helpers.count("heir") === 2, `${enc.helpers.count("heir")} heirs after the first call`);
    check(def.weight(enc) === 0, "The Heirs is still eligible at the cap");
    run(120, [bot]);
    const post = enc.controller.armor.anchor("l");
    const nearPost = enc.helpers.of("heir").filter((h) => Math.hypot(h.entity._loc.x - post.x, h.entity._loc.z - post.z) < 3.2).length;
    check(nearPost >= 1, "no Heir moved to guard the exposed flank");
    check(enc.controller.armor.guarded("l"), "exposed flank is not counted as guarded");
    // kill one: the cap frees up and the guard is recomputed
    const [victim, other] = enc.helpers.of("heir");
    victim.entity.applyDamage(100, { cause: "entityAttack", damagingEntity: players[0] });
    run(3, [bot]);
    check(enc.helpers.count("heir") === 1, "killed Heir still counted");
    run(520, [bot]);
    check(!other.entity.isValid, "an Heir outlived its lifetime");
    check(enc.helpers.count("heir") <= 2, "more than two Heirs alive");
  });

  await test("vesperra: destroying a cocoon anchor breaks the web", async () => {
    const ctx = await begin("vesperra");
    const { enc, players } = ctx;
    const bot = new Bot(players[0], enc, { mode: "stand" });
    toPhase(ctx, 1, [bot]);
    place(players[0], enc, 9, 0);
    const def = enc.controller.attacks.find((a) => a.id === "cocoon_edict");
    enc.scheduler.forced = def.id;
    enc.nextAttackAt = 0;
    run(300, [bot], () => enc.helpers.count("anchor") === 3);
    check(enc.helpers.count("anchor") === 3, "anchors were not spawned");
    const hp = players[0]._health.currentValue;
    enc.helpers.of("anchor")[0].entity.applyDamage(50, { cause: "entityAttack", damagingEntity: players[0] });
    run(120, [bot]);
    check(count("cocoon_broken") === 1, "web did not fail after an anchor was destroyed");
    check(players[0]._health.currentValue === hp, "player inside a broken web was still damaged");
    check(enc.helpers.count("anchor") === 0, "anchors were not removed afterwards");
  });

  await test("vesperra: Royal Molting sheds visibly without restoring armour", async () => {
    const ctx = await begin("vesperra");
    const { enc, players } = ctx;
    const bot = new Bot(players[0], enc, { mode: "dodge" });
    toPhase(ctx, 1, [bot]);
    enc.controller.armor.hp.r = 0;
    enc.controller.armor.sync();
    const def = enc.controller.attacks.find((a) => a.id === "royal_molting");
    forceAttack(enc, def, [bot]);
    check(enc.boss.getProperty("abm:molt") === 1, "molt stage not shown");
    check(enc.boss.getProperty("abm:armor_r") === 2 && enc.controller.armor.hp.r === 0, "molting restored destroyed armour");
  });
}
