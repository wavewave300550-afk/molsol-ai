// Control-system tests (sections 3.3 - 3.5 and the "General Controls"/"Cooldowns" test cases).
export default function ({ mock, test, eq, ok }) {
  const { world, system, tick, addPlayer, addMob, ItemStack, reset } = mock;
  const A = world.afterEvents;
  const sel = (p) => p.getDynamicProperty("grim:sel") ?? "0,0,0";
  const cds = (p) => JSON.parse(p.getDynamicProperty("grim:cd") ?? "{}");
  const press = (p) => A.itemStartUse.emit({ source: p, itemStack: p.hotbar[p.selectedSlotIndex], useDuration: 1440000 });
  const letGo = (p) => { A.itemReleaseUse.emit({ source: p, itemStack: p.hotbar[p.selectedSlotIndex], useDuration: 1439990 }); A.itemStopUse.emit({ source: p, itemStack: p.hotbar[p.selectedSlotIndex], useDuration: 0 }); };
  const stopOnly = (p) => A.itemStopUse.emit({ source: p, itemStack: p.hotbar[p.selectedSlotIndex], useDuration: 0 });
  const crouch = (p, on) => { p.isSneaking = on; tick(1); };
  const fresh = (name = "Tester") => {
    reset();
    const p = addPlayer(name);
    p.hotbar[0] = new ItemStack("grimoire:divine_word");
    p.hotbar[1] = new ItemStack("grimoire:dream_nightmare");
    p.hotbar[2] = new ItemStack("grimoire:elemental_dragon");
    p.hotbar[3] = new ItemStack("minecraft:stick");
    p.hotbar[4] = new ItemStack("grimoire:divine_word"); // duplicate book
    addMob("minecraft:zombie", { x: 0.5, y: 64, z: 8.5 }, 4000);
    tick(2);
    return p;
  };

  test("exactly three grimoire items exist", () => {
    eq([...mock.assets.items].sort().join(), "grimoire:divine_word,grimoire:dream_nightmare,grimoire:elemental_dragon");
  });
  test("one crouch press advances exactly one spell; holding crouch does not repeat", () => {
    const p = fresh();
    crouch(p, true); eq(sel(p), "1,0,0");
    tick(40); eq(sel(p), "1,0,0", "held crouch");
    crouch(p, false); eq(sel(p), "1,0,0", "releasing crouch");
    crouch(p, true); crouch(p, false); eq(sel(p), "2,0,0");
  });
  test("selection wraps 06 -> 01", () => {
    const p = fresh();
    for (let i = 0; i < 6; i++) { crouch(p, true); crouch(p, false); }
    eq(sel(p), "0,0,0");
  });
  test("selection is separate per grimoire and survives switching books", () => {
    const p = fresh();
    crouch(p, true); crouch(p, false);
    p.selectedSlotIndex = 1; tick(1);
    crouch(p, true); crouch(p, false); crouch(p, true); crouch(p, false);
    p.selectedSlotIndex = 2; tick(1);
    eq(sel(p), "1,2,0");
    p.selectedSlotIndex = 0; tick(1); eq(sel(p), "1,2,0");
  });
  test("crouching without a grimoire in hand selects nothing", () => {
    const p = fresh();
    p.selectedSlotIndex = 3; tick(1);
    crouch(p, true); crouch(p, false); eq(sel(p), "0,0,0");
  });
  test("HUD shows grimoire, spell number, name and READY", () => {
    const p = fresh(); tick(12);
    ok(/Divine Word/.test(p.actionBar) && /01/.test(p.actionBar) && /Seraphic Litany/.test(p.actionBar) && /READY/.test(p.actionBar), p.actionBar);
  });
  test("pressing Use does not cast; holding does not auto-cast; release casts exactly once", () => {
    const p = fresh();
    press(p); tick(1); eq(Object.keys(cds(p)).length, 0, "cast on press");
    tick(200); eq(Object.keys(cds(p)).length, 0, "auto cast while holding");
    letGo(p); tick(1);
    eq(Object.keys(cds(p)).join(), "dw01");
    const before = cds(p).dw01;
    letGo(p); letGo(p); tick(2); // duplicate callbacks
    eq(cds(p).dw01, before, "duplicate release recast");
  });
  test("stop arriving before release in the same tick still casts once", () => {
    const p = fresh();
    press(p); tick(10);
    stopOnly(p); A.itemReleaseUse.emit({ source: p, itemStack: p.hotbar[0], useDuration: 5 });
    tick(2); eq(Object.keys(cds(p)).join(), "dw01");
  });
  test("cannot begin casting while crouched", () => {
    const p = fresh();
    p.isSneaking = true; tick(1); // selects spell 2
    press(p); tick(10); letGo(p); tick(2);
    eq(Object.keys(cds(p)).length, 0);
  });
  test("crouching during preparation cancels it; no cooldown; no delayed cast", () => {
    const p = fresh();
    press(p); tick(10);
    p.isSneaking = true; tick(1);
    eq(sel(p), "0,0,0", "cancel must not also advance the selection");
    p.isSneaking = false; tick(1);
    letGo(p); tick(40);
    eq(Object.keys(cds(p)).length, 0);
  });
  test("changing the held item cancels; a later stop/release does nothing", () => {
    const p = fresh();
    press(p); tick(10);
    p.selectedSlotIndex = 3; stopOnly(p); tick(2);
    A.itemReleaseUse.emit({ source: p, itemStack: p.hotbar[3], useDuration: 5 }); tick(20);
    eq(Object.keys(cds(p)).length, 0);
  });
  test("switching to another grimoire mid-hold cancels", () => {
    const p = fresh();
    press(p); tick(10);
    p.selectedSlotIndex = 1; tick(1);
    letGo(p); tick(5);
    eq(Object.keys(cds(p)).length, 0);
  });
  test("an item-stop without a release is NOT treated as a release", () => {
    const p = fresh();
    press(p); tick(10); stopOnly(p); tick(5);
    eq(Object.keys(cds(p)).length, 0);
  });
  test("completing the charge without release never auto-casts", () => {
    const p = fresh();
    press(p); tick(10);
    A.itemCompleteUse.emit({ source: p, itemStack: p.hotbar[0], useDuration: 0 }); tick(5);
    eq(Object.keys(cds(p)).length, 0);
  });
  test("a too-short tap is cancelled without cooldown", () => {
    const p = fresh();
    press(p); tick(2); letGo(p); tick(5);
    eq(Object.keys(cds(p)).length, 0);
  });
  test("dying during preparation cancels the pending cast", () => {
    const p = fresh();
    press(p); tick(10);
    A.entityDie.emit({ deadEntity: p }); tick(1);
    letGo(p); tick(5);
    eq(Object.keys(cds(p)).length, 0);
  });
  test("cooldowns are per spell: another spell is castable immediately, no global cooldown", () => {
    const p = fresh();
    press(p); tick(10); letGo(p); tick(3);
    crouch(p, true); crouch(p, false); // spell 2
    press(p); tick(10); letGo(p); tick(3);
    eq(Object.keys(cds(p)).sort().join(), "dw01,dw02");
    p.selectedSlotIndex = 2; tick(1);
    press(p); tick(10); letGo(p); tick(3);
    eq(Object.keys(cds(p)).sort().join(), "dw01,dw02,ed01");
  });
  test("a spell on cooldown cannot be prepared; a duplicate book does not bypass it", () => {
    const p = fresh();
    press(p); tick(10); letGo(p); tick(3);
    const first = cds(p).dw01;
    press(p); tick(10); letGo(p); tick(3);
    eq(cds(p).dw01, first, "recast while cooling");
    p.selectedSlotIndex = 4; tick(1); // second copy of the same book
    press(p); tick(10); letGo(p); tick(3);
    eq(cds(p).dw01, first, "duplicate book bypassed cooldown");
    ok(/\d+s/.test(p.actionBar), "HUD should show remaining cooldown: " + p.actionBar);
  });
  test("approved cooldown values are applied", () => {
    const want = { dw01: 15, dw02: 28, dw03: 35, dw04: 45, dw05: 180, dw06: 360, dn01: 16, dn02: 24, dn03: 38, dn04: 46, dn05: 180, dn06: 360,
      ed01: 28, ed02: 24, ed03: 32, ed04: 20, ed05: 180, ed06: 360 };
    const order = [["dw", 0], ["dn", 1], ["ed", 2]];
    for (const [pre, slot] of order) {
      const p = fresh(pre);
      p.selectedSlotIndex = slot; tick(1);
      for (let i = 0; i < 6; i++) {
        const id = `${pre}0${i + 1}`;
        const t0 = Date.now();
        press(p); tick(10); letGo(p); tick(2);
        const got = (cds(p)[id] - t0) / 1000;
        ok(Math.abs(got - want[id]) < 1.5, `${id}: cooldown ${got}s, want ${want[id]}s`);
        crouch(p, true); crouch(p, false);
      }
    }
  });
  test("cooldowns are independent per player", () => {
    const p = fresh("One");
    const q = addPlayer("Two", { x: 20.5, y: 64, z: 0.5 });
    q.hotbar[0] = new ItemStack("grimoire:divine_word"); tick(2);
    press(p); tick(10); letGo(p); tick(3);
    eq(Object.keys(cds(q)).length, 0, "other player got a cooldown");
    press(q); tick(10); letGo(q); tick(3);
    eq(Object.keys(cds(q)).join(), "dw01");
  });
  test("switching items does not reset cooldowns", () => {
    const p = fresh();
    press(p); tick(10); letGo(p); tick(3);
    const first = cds(p).dw01;
    p.selectedSlotIndex = 3; tick(5); p.selectedSlotIndex = 0; tick(5);
    eq(cds(p).dw01, first);
  });
  test("books are not consumed and have no durability or mana", () => {
    const p = fresh();
    press(p); tick(10); letGo(p); tick(3);
    eq(p.hotbar[0].typeId, "grimoire:divine_word"); eq(p.hotbar[0].amount, 1);
    eq(p.health, 20, "casting must not cost HP");
  });
}
