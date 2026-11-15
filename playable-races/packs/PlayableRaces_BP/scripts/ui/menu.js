import { EnchantmentType, EquipmentSlot, system } from "@minecraft/server";
import { ActionFormData, FormCancelationReason, MessageFormData, ModalFormData } from "@minecraft/server-ui";
import { raceOf, selected } from "../core/abilities.js";
import { captureEnchantments, headItem, isCrest } from "../core/forms.js";
import { get, save } from "../core/session.js";
import { settings, updateSettings } from "../core/settings.js";
import { warn } from "../core/util.js";
import { assignRace, changeBlocked, giveFocus, isOperator, raceBlocked, removeRace, setVeiled } from "../lineage.js";
import { RACES, raceByCode } from "../races/registry.js";
import { bloodMoonStatus } from "../systems/bloodmoon.js";
import { holderOf, isUnique, uniqueStatus } from "../systems/unique.js";
const UNIQUE_TAG = "§6§l✦ UNIQUE ✦§r";
function raceButton(r) {
    const tag = isUnique(r) ? ` ${UNIQUE_TAG}` : "";
    return `${r.color}§l${r.name}${tag}\n§r§8Race ${r.code} - ${r.title}`;
}
const PORTRAIT = (r) => `textures/plrace/races/ui/portrait_${r.code}`;
async function showAction(p, form, retries = 0) {
    const s = get(p);
    s.menuOpen = true;
    try {
        const r = await form.show(p);
        if (r.canceled) {
            if (r.cancelationReason === FormCancelationReason.UserBusy && retries > 0) {
                await wait(30);
                return showAction(p, form, retries - 1);
            }
            return undefined;
        }
        return r.selection;
    }
    catch (e) {
        warn("form failed", e);
        return undefined;
    }
    finally {
        s.menuOpen = false;
    }
}
function wait(ticks) {
    return new Promise((res) => system.runTimeout(() => res(), ticks));
}
export async function openCodex(p, retries = 0) {
    const s = get(p);
    const race = raceOf(s);
    const f = new ActionFormData().title("§lLineage Codex");
    const actions = [];
    if (race) {
        const a = selected(s, race);
        f.body(`${race.color}§l${race.name}§r §7(Race ${race.code})\n§o${race.title}§r\n\n§7Selected ability: §f${a.name}\n§7Form: ${s.data.veiled ? "§8veiled" : "§amanifest"}`);
        f.button(`${race.color}Your Lineage\n§8details, passives, lore`, PORTRAIT(race));
        actions.push(() => raceDetail(p, race, false));
    }
    else {
        f.body("§7You have not chosen a lineage.\nEach lineage reshapes your body, grants four abilities and changes how the world treats you.\n\n§fChoose carefully - changing later requires the Rite of Unbecoming.");
        f.button(`§l§2Choose a Lineage\n§r§8${RACES.length} lineages await`, "textures/plrace/races/items/codex");
        actions.push(() => chooseRace(p));
    }
    f.button("§lAbilities & Controls\n§r§8how to cast, cooldowns", "textures/plrace/races/items/focus_jackalope");
    actions.push(() => controls(p));
    if (race) {
        f.button(s.data.veiled ? "§lManifest Form\n§r§8show your racial body" : "§lVeil Form\n§r§8hide it; wear a helmet", "textures/plrace/races/items/crest_" + race.key);
        actions.push(() => {
            const msg = setVeiled(p, !s.data.veiled);
            p.sendMessage(msg);
        });
        f.button("§lInfuse Crest\n§r§8enchanted books -> your crest", "textures/plrace/races/items/focus_golem");
        actions.push(() => infuse(p));
        f.button("§lRecall Focus\n§r§8lost your focus item?", "textures/plrace/races/items/" + race.focusItem.split(":")[1]);
        actions.push(() => {
            giveFocus(p);
            p.sendMessage("§7Your focus returns to your hands (if it was missing).");
        });
        f.button("§lRite of Unbecoming\n§r§8change lineage", "textures/plrace/races/items/codex");
        actions.push(() => unbecoming(p));
    }
    f.button("§lLineage Archive\n§r§8all races", "textures/plrace/races/items/codex");
    actions.push(() => chooseRace(p, true));
    if (isOperator(p)) {
        f.button("§l§6World Settings\n§r§8operators only", "textures/plrace/races/items/focus_golem");
        actions.push(() => worldSettings(p));
    }
    const sel = await showAction(p, f, retries);
    if (sel === undefined)
        return;
    await actions[sel]?.();
}
export async function chooseRace(p, browseOnly = false) {
    const f = new ActionFormData().title(browseOnly ? "§lLineage Archive" : "§lChoose your Lineage");
    f.body(browseOnly ? "§7The known lineages of this world." : "§7Select a lineage to read about it. You will be asked to confirm before anything changes.");
    for (const r of RACES)
        f.button(raceButton(r), PORTRAIT(r));
    const sel = await showAction(p, f);
    if (sel === undefined)
        return;
    await raceDetail(p, RACES[sel], !browseOnly);
}
function detailText(r) {
    const lines = [];
    if (isUnique(r)) {
        lines.push(UNIQUE_TAG, "§7A Unique lineage: more elaborate systems, a signature ultimate ability and a presence the world reacts to." +
            (settings().uniqueExclusive ? " §eOnly one player in this world may hold it at a time." : ""));
        const h = holderOf(r.code);
        if (h && settings().uniqueExclusive)
            lines.push(`§6Current holder: §f${h.name}`);
        lines.push("");
    }
    lines.push(`§o§7${r.tagline}§r`);
    lines.push("");
    for (const para of r.lore)
        lines.push(`§f${para}`, "");
    lines.push("§a§lStrengths§r");
    for (const x of r.strengths)
        lines.push(`§a+ §f${x}`);
    lines.push("", "§c§lWeaknesses§r");
    for (const x of r.weaknesses)
        lines.push(`§c- §f${x}`);
    lines.push("", "§e§lPassive traits§r");
    for (const x of r.passives)
        lines.push(`§e${x.name}: §7${x.desc}`);
    lines.push("", "§d§lAbilities§r");
    r.abilities.forEach((a, i) => {
        const head = a.ultimate ? `§6§l${i + 1}. ${a.name} §r§6[UNIQUE ULTIMATE]` : `§d${i + 1}. ${a.name}`;
        lines.push(`${head} §7(${a.cooldown}s${a.charges || a.maxCharges ? ", charges" : ""})`);
        lines.push(`§7${a.desc}`);
    });
    return lines.join("\n");
}
async function raceDetail(p, r, offerChoose) {
    const s = get(p);
    const f = new ActionFormData().title(`${r.color}§l${r.name}`).body(detailText(r));
    const acts = [];
    const mine = s.data.race === r.code;
    const held = raceBlocked(p, r);
    if (offerChoose && !mine && !held) {
        f.button(`${r.color}§lBecome the ${r.name}`, PORTRAIT(r));
        acts.push(() => confirmChoice(p, r));
    }
    else if (offerChoose && !mine && held) {
        f.button(`§8${r.name}\n§8already held by another player`, PORTRAIT(r));
        acts.push(() => p.sendMessage(`§c${held}`));
    }
    f.button("§lBack");
    acts.push(() => (offerChoose ? chooseRace(p) : openCodex(p)));
    const sel = await showAction(p, f);
    if (sel === undefined)
        return;
    await acts[sel]?.();
}
async function confirmChoice(p, r) {
    const s = get(p);
    const blocked = changeBlocked(p, s) ?? raceBlocked(p, r);
    if (blocked) {
        p.sendMessage(`§c${blocked}`);
        return;
    }
    const set = settings();
    const policy = set.change === "free" ? "You may change again at any time." : set.change === "cooldown" ? `After this, the Rite of Unbecoming waits ${set.changeDays} in-game days.` : "Only operators can change it afterwards.";
    const m = new MessageFormData()
        .title(`${r.color}§lEmbrace the ${r.name}?`)
        .body(`§fYour body will become a ${r.name} (Race ${r.code}).${isUnique(r) ? `\n${UNIQUE_TAG}${settings().uniqueExclusive ? " §7While you hold it, no one else in this world can." : ""}` : ""}\n\n§7You receive a §f${r.focusName}§7 to cast abilities, and your racial form is worn as a locked crest in your helmet slot.\n\n§e${policy}`)
        .button1("§l§2Embrace")
        .button2("§lNot yet");
    s.menuOpen = true;
    let res;
    try {
        res = await m.show(p);
    }
    catch {
        return;
    }
    finally {
        s.menuOpen = false;
    }
    if (res.canceled || res.selection !== 0)
        return;
    if (changeBlocked(p, s) || raceBlocked(p, r))
        return;
    if (!assignRace(p, r.code))
        return;
    p.sendMessage(`${r.color}You are now a ${r.name}. §7Hold your focus: USE casts, SNEAK + USE switches ability.`);
}
async function unbecoming(p) {
    const s = get(p);
    const blocked = changeBlocked(p, s);
    if (blocked) {
        p.sendMessage(`§c${blocked}`);
        return;
    }
    const f = new ActionFormData().title("§lRite of Unbecoming").body("§7Choose a new lineage, or return to an ordinary body. Cooldowns and race resources reset.");
    for (const r of RACES)
        if (r.code !== s.data.race)
            f.button(`${r.color}${r.name}${isUnique(r) ? " §6✦" : ""}${raceBlocked(p, r) ? "\n§8held by another player" : ""}`, PORTRAIT(r));
    f.button("§7Return to an ordinary body");
    const others = RACES.filter((r) => r.code !== s.data.race);
    const sel = await showAction(p, f);
    if (sel === undefined)
        return;
    if (sel < others.length)
        await confirmChoice(p, others[sel]);
    else {
        removeRace(p);
        p.sendMessage("§7Your lineage fades. You are ordinary again.");
    }
}
async function controls(p) {
    const s = get(p);
    const race = raceOf(s);
    const lines = [
        "§l§fCasting§r",
        "§7Hold your racial §fFocus§7 item.",
        "§f USE §7(right-click / tap & hold / left trigger): cast the selected ability.",
        "§f SNEAK + USE§7: select the next ability.",
        "§7The action bar shows all four abilities: §a green§7 = ready, §8grey + seconds§7 = recovering, §f[brackets]§7 = selected, §dpink§7 = active.",
        "§7Targeted abilities show a reticle on the creature they will hit while you hold the focus. Failed casts (no target, conditions unmet) never spend the cooldown.",
        "",
        "§l§fOther controls§r",
        ...RACES.flatMap((r) => (r.controls ?? []).map((c) => `§7${c}`)),
        "§7Root Metamorphosis and Runic Bastion end early if you use them again (after 0.6 s).",
        "§7Commands: §f/plrace:codex§7 opens this book anywhere.",
    ];
    if (race) {
        lines.push("", `${race.color}§l${race.name} abilities§r`);
        race.abilities.forEach((a, i) => lines.push(`${a.ultimate ? "§6§l" : race.color}${i + 1}. ${a.name}${a.ultimate ? " §r§6[UNIQUE ULTIMATE]" : ""} §7- ${a.cooldown}s`, `§7${a.desc}`, `§8Original brief: ${a.original ?? "-"}`));
    }
    await showAction(p, new ActionFormData().title("§lAbilities & Controls").body(lines.join("\n")).button("§lBack"));
    await openCodex(p);
}
const HEAD_ENCHANTS = ["protection", "fire_protection", "blast_protection", "projectile_protection", "respiration", "aqua_affinity", "thorns"];
async function infuse(p) {
    const s = get(p);
    if (s.data.veiled || !isCrest(headItem(p))) {
        p.sendMessage("§cManifest your form first - the crest must be worn to be infused.");
        return;
    }
    const inv = p.getComponent("minecraft:inventory")?.container;
    if (!inv)
        return;
    const books = [];
    for (let i = 0; i < inv.size; i++) {
        const it = inv.getItem(i);
        if (!it || it.typeId !== "minecraft:enchanted_book")
            continue;
        try {
            const list = it.getComponent("minecraft:enchantable")?.getEnchantments() ?? [];
            const useful = list.filter((e) => HEAD_ENCHANTS.includes(e.type.id.replace("minecraft:", ""))).map((e) => [e.type.id, e.level]);
            if (useful.length)
                books.push({ slot: i, ench: useful });
        }
        catch {
        }
    }
    if (books.length === 0) {
        await showAction(p, new ActionFormData().title("§lInfuse Crest").body("§7Carry an §fenchanted book§7 with a helmet enchantment (Protection, Fire/Blast/Projectile Protection, Respiration, Aqua Affinity, Thorns). The crest absorbs the book's power permanently - it keeps it through every transformation and when veiled.").button("§lBack"));
        return;
    }
    const f = new ActionFormData().title("§lInfuse Crest").body("§7Choose a book to dissolve into your crest. Conflicting enchantments (e.g. two kinds of Protection) are rejected.");
    for (const b of books)
        f.button(b.ench.map(([id, l]) => `${id.replace("minecraft:", "").replace(/_/g, " ")} ${l}`).join(", "), "textures/items/book_enchanted");
    const sel = await showAction(p, f);
    if (sel === undefined)
        return;
    const chosen = books[sel];
    const crest = headItem(p);
    if (!crest || !isCrest(crest))
        return;
    const ench = crest.getComponent("minecraft:enchantable");
    if (!ench)
        return;
    let applied = 0;
    for (const [id, level] of chosen.ench) {
        try {
            const type = new EnchantmentType(id);
            const cur = ench.getEnchantment(type);
            const lvl = Math.min(type.maxLevel, Math.max(level, cur ? cur.level : 0));
            const e = { type, level: lvl };
            if (cur)
                ench.removeEnchantment(type);
            if (ench.canAddEnchantment(e)) {
                ench.addEnchantment(e);
                applied++;
            }
            else if (cur)
                ench.addEnchantment(cur);
        }
        catch {
        }
    }
    if (applied === 0) {
        p.sendMessage("§cThe crest rejects that book (conflicting or already stronger).");
        return;
    }
    try {
        p.getComponent("minecraft:equippable")?.setEquipment(EquipmentSlot.Head, crest);
        const book = inv.getItem(chosen.slot);
        if (book && book.typeId === "minecraft:enchanted_book") {
            if (book.amount > 1) {
                book.amount -= 1;
                inv.setItem(chosen.slot, book);
            }
            else
                inv.setItem(chosen.slot, undefined);
        }
    }
    catch (e) {
        warn("infusion failed", e);
        return;
    }
    captureEnchantments(p, s);
    save(p, s, true);
    p.sendMessage("§dThe crest drinks the book's power.");
}
async function worldSettings(p) {
    const cur = settings();
    const policies = ["free", "cooldown", "operators"];
    const f = new ModalFormData()
        .title("§lPlayable Races - World Settings")
        .toggle("Abilities can harm other players (also needs the pvp game rule)", { defaultValue: cur.pvp })
        .dropdown("Lineage changes", ["Free", "Cooldown (in-game days)", "Operators only"], { defaultValueIndex: policies.indexOf(cur.change) })
        .slider("Days between lineage changes", 0, 14, { valueStep: 1, defaultValue: cur.changeDays })
        .slider("Blood Moon chance per full moon (%)", 0, 100, { valueStep: 1, defaultValue: cur.bloodChance })
        .toggle("Crimson fog during the Blood Moon", { defaultValue: cur.bloodFog })
        .toggle("Open lineage selection for new players", { defaultValue: cur.autoOpen })
        .toggle("Show the ability HUD without holding the focus", { defaultValue: cur.hudAlways })
        .toggle(`Unique lineages: one holder per world (${uniqueStatus()})`, { defaultValue: cur.uniqueExclusive })
        .submitButton("Save");
    const s = get(p);
    s.menuOpen = true;
    let r;
    try {
        r = await f.show(p);
    }
    catch {
        return;
    }
    finally {
        s.menuOpen = false;
    }
    if (r.canceled || !r.formValues)
        return;
    const v = r.formValues.filter((x) => x !== undefined);
    updateSettings({
        pvp: !!v[0],
        change: policies[Number(v[1]) || 0],
        changeDays: Number(v[2]) || 0,
        bloodChance: Number(v[3]) || 0,
        bloodFog: !!v[4],
        autoOpen: !!v[5],
        hudAlways: !!v[6],
        uniqueExclusive: !!v[7],
    });
    p.sendMessage(`§6Settings saved. ${bloodMoonStatus()}`);
}
export function raceSummary(code) {
    const r = raceByCode(code);
    return r ? `${r.color}${r.name}` : "§7none";
}
