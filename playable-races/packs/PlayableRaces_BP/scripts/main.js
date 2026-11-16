import { ButtonState, InputButton, ItemStack, system, world } from "@minecraft/server";
import { ENTITY_MIRAGE, FRESH_PRESS_GAP, INPUT_DEBOUNCE, ITEM_CODEX, SAVE_INTERVAL } from "./config.js";
import { cast, cycle, endChannel, raceOf, refreshForm, selected, tickChannel } from "./core/abilities.js";
import { setWeather } from "./core/env.js";
import { holdingFocus } from "./core/forms.js";
import { privateParticle, rgb, RGB } from "./core/fx.js";
import { updateHud } from "./core/hud.js";
import { all, drop, get, load, peek, save } from "./core/session.js";
import { settings } from "./core/settings.js";
import { aimTarget, chest } from "./core/targets.js";
import { cancel, startScheduler } from "./core/tasks.js";
import { warn } from "./core/util.js";
import { registerCommands } from "./commands.js";
import { tickStatuses } from "./systems/status.js";
import { integrity, restore } from "./lineage.js";
import { golemLightning, inWard } from "./races/golem.js";
import { moonhunt } from "./races/jackalope.js";
import { cleanupEnsnared, salamanderDrink } from "./races/salamander.js";
import { applyFog, bloodMoonTick, onBloodMoonChange } from "./systems/bloodmoon.js";
import { clearHeavenFog } from "./races/nurariten.js";
import { consume, markedBy, tickMarks } from "./systems/marks.js";
import { isMirage, pop, removeMiragesOf, tickMirages } from "./systems/mirage.js";
import { isProxy, proxyDied, proxyHurt, purgeOrphans, removeProxiesOf, tickProxies } from "./systems/proxies.js";
import { openCodex } from "./ui/menu.js";
import { RACES } from "./races/registry.js";
const INTERACTIVE = /(door|chest|barrel|button|lever|gate|table|furnace|smoker|anvil|shulker|bed|hopper|dispenser|dropper|crafter|lectern|loom|grindstone|stonecutter|cartography|smithing|brewing|beacon|bell|cake|noteblock|repeater|comparator|daylight|jukebox|campfire|composter|cauldron|respawn_anchor|lodestone|trapdoor|sign|frame|decorated_pot|chiseled_bookshelf|vault|trial_spawner)/;
function players() {
    try {
        return world.getPlayers();
    }
    catch {
        return [];
    }
}
function playerById(id) {
    return players().find((p) => p.id === id);
}
function releaseAll(id, reason) {
    removeProxiesOf(id);
    const s = peek(id);
    const race = s && raceOf(s);
    if (s && race?.release) {
        try {
            race.release(s, reason);
        }
        catch (e) {
            warn("race release failed", e);
        }
    }
}
function useFocus(p) {
    const s = get(p);
    const now = system.currentTick;
    const fresh = now - s.lastRawInput >= FRESH_PRESS_GAP;
    s.lastRawInput = now;
    if (!fresh)
        return;
    if (now - s.lastInput < INPUT_DEBOUNCE)
        return;
    s.lastInput = now;
    if (!raceOf(s)) {
        void openCodex(p);
        return;
    }
    if (p.isSneaking)
        cycle(p, s);
    else
        cast(p, s);
}
system.beforeEvents.startup.subscribe((ev) => {
    try {
        registerCommands(ev);
    }
    catch (e) {
        warn("command registration failed", e);
    }
    ev.itemComponentRegistry.registerCustomComponent("plrace:focus", {
        onUse: (e) => {
            const p = e.source;
            system.run(() => {
                if (p.isValid)
                    useFocus(p);
            });
        },
    });
    ev.itemComponentRegistry.registerCustomComponent("plrace:codex", {
        onUse: (e) => {
            const p = e.source;
            system.run(() => {
                if (p.isValid)
                    void openCodex(p);
            });
        },
    });
});
world.beforeEvents.playerInteractWithBlock.subscribe((ev) => {
    const it = ev.itemStack;
    if (!it || !it.hasTag("plrace:focus") || !ev.isFirstEvent)
        return;
    if (INTERACTIVE.test(ev.block.typeId))
        return;
    ev.cancel = true;
    const p = ev.player;
    system.run(() => {
        if (p.isValid)
            useFocus(p);
    });
});
world.afterEvents.playerButtonInput.subscribe((ev) => {
    const s = peek(ev.player.id);
    if (s?.channel?.ability === "root_metamorphosis")
        endChannel(ev.player, s, "cancel");
}, { buttons: [InputButton.Jump], state: ButtonState.Pressed });
function onJoin(p, first) {
    const s = load(p);
    restore(p, s);
    if (!s.data.joined) {
        s.data.joined = true;
        s.dirty = true;
        giveCodex(p);
        p.sendMessage("§dPlayable Races: §7open the §fLineage Codex");
        if (settings().autoOpen && !s.data.race)
            system.runTimeout(() => {
                if (p.isValid)
                    void openCodex(p, 6);
            }, 60);
    }
    save(p, s, true);
    if (first) {
        clearHeavenFog(p);
        applyFog(p);
    }
}
function giveCodex(p) {
    const codex = new ItemStack(ITEM_CODEX, 1);
    const inv = p.getComponent("minecraft:inventory")?.container;
    try {
        const left = inv?.addItem(codex);
        if (left || !inv)
            p.dimension.spawnItem(codex, p.location);
    }
    catch {
    }
}
world.afterEvents.playerSpawn.subscribe((ev) => {
    const p = ev.player;
    system.runTimeout(() => {
        if (!p.isValid)
            return;
        if (ev.initialSpawn)
            onJoin(p, true);
        else {
            const s = get(p);
            restore(p, s);
        }
    }, 10);
});
world.beforeEvents.playerLeave.subscribe((ev) => {
    const id = ev.player.id;
    system.run(() => {
        const s = peek(id);
        if (s) {
            s.channel = undefined;
            cancel(id);
            removeMiragesOf(id);
            releaseAll(id, "leave");
            drop(id);
        }
    });
});
world.afterEvents.playerDimensionChange.subscribe((ev) => {
    const p = ev.player;
    const s = get(p);
    if (s.channel)
        endChannel(p, s, "dimension");
    cancel(p.id);
    releaseAll(p.id, "dimension");
    system.runTimeout(() => {
        if (!p.isValid)
            return;
        applyFog(p);
        refreshForm(p, s);
    }, 5);
});
world.beforeEvents.entityHurt.subscribe((ev) => {
    const victim = ev.hurtEntity;
    if (victim.typeId === "minecraft:player") {
        const s = peek(victim.id);
        const race = s && raceOf(s);
        if (s && race?.onHurt)
            race.onHurt(victim, s, ev);
        if (!ev.cancel && inWard(victim))
            ev.damage *= 0.85;
    }
    const src = ev.damageSource.damagingEntity;
    if (src && src.typeId === "minecraft:player" && !ev.cancel) {
        const s = peek(src.id);
        const race = s && raceOf(s);
        if (s && race?.onDealDamage)
            race.onDealDamage(src, s, ev);
    }
});
world.afterEvents.entityHurt.subscribe((ev) => {
    const e = ev.hurtEntity;
    if (isProxy(e)) {
        proxyHurt(e, ev.damage, ev.damageSource.damagingEntity);
        return;
    }
    if (e.typeId === ENTITY_MIRAGE) {
        pop(e, true, playerById, ev.damageSource.damagingEntity);
        return;
    }
    if (e.typeId === "minecraft:player") {
        const s = peek(e.id);
        const race = s && raceOf(s);
        if (s && race?.afterHurt) {
            try {
                race.afterHurt(e, s, ev.damageSource.cause, ev.damage, ev.damageSource.damagingEntity?.id);
            }
            catch (err) {
                warn("afterHurt failed", err);
            }
        }
    }
});
world.afterEvents.entityDie.subscribe((ev) => {
    const e = ev.deadEntity;
    if (e.typeId === "minecraft:player") {
        const s = peek(e.id);
        if (s) {
            if (s.channel)
                endChannel(e, s, "death");
            cancel(e.id);
            s.tempVariant = undefined;
            s.flags.clear();
            removeMiragesOf(e.id);
            releaseAll(e.id, "death");
        }
        return;
    }
    if (isProxy(e)) {
        proxyDied(e);
        return;
    }
    if (isMirage(e))
        return;
    const by = markedBy(e.id);
    if (by) {
        consume(e);
        const p = playerById(by);
        const s = p && peek(p.id);
        if (p && s && raceOf(s)?.key === "jackalope")
            moonhunt(p, s);
    }
});
world.afterEvents.itemCompleteUse.subscribe((ev) => {
    const s = peek(ev.source.id);
    const race = s && raceOf(s);
    if (!s || !race)
        return;
    const typeId = ev.itemStack.typeId;
    if (typeId === "minecraft:potion" && race.key === "salamander")
        salamanderDrink(ev.source, s);
    if (race.onItemComplete) {
        try {
            race.onItemComplete(ev.source, s, typeId);
        }
        catch (e) {
            warn("onItemComplete failed", e);
        }
    }
});
world.afterEvents.explosion.subscribe((ev) => {
    let center;
    try {
        if (ev.source?.isValid)
            center = ev.source.location;
    }
    catch {
        center = undefined;
    }
    if (!center) {
        try {
            const blocks = ev.getImpactedBlocks().slice(0, 64);
            if (blocks.length) {
                const n = blocks.length;
                center = blocks.reduce((a, b) => ({ x: a.x + b.location.x / n, y: a.y + b.location.y / n, z: a.z + b.location.z / n }), { x: 0, y: 0, z: 0 });
            }
        }
        catch {
            center = undefined;
        }
    }
    if (!center)
        return;
    for (const p of players()) {
        if (p.dimension.id !== ev.dimension.id)
            continue;
        const s = peek(p.id);
        const race = s && raceOf(s);
        if (!s || !race?.onExplosion)
            continue;
        const d = Math.hypot(p.location.x - center.x, p.location.y - center.y, p.location.z - center.z);
        if (d > 14)
            continue;
        try {
            race.onExplosion(p, s, d);
        }
        catch (e) {
            warn("onExplosion failed", e);
        }
    }
});
world.afterEvents.weatherChange.subscribe((ev) => {
    if (ev.dimension === "minecraft:overworld" || ev.dimension === "overworld")
        setWeather(ev.newWeather);
});
world.afterEvents.entitySpawn.subscribe((ev) => {
    const e = ev.entity;
    if (!e.isValid || e.typeId !== "minecraft:lightning_bolt")
        return;
    for (const p of players()) {
        const s = peek(p.id);
        const race = s && raceOf(s);
        if (!s || !race || p.dimension.id !== e.dimension.id)
            continue;
        const d = Math.hypot(p.location.x - e.location.x, p.location.y - e.location.y, p.location.z - e.location.z);
        if (race.key === "golem")
            golemLightning(p, s, d);
        else if (race.onExplosion && d <= 12)
            race.onExplosion(p, s, d);
    }
});
onBloodMoonChange(() => {
    for (const p of players()) {
        const s = peek(p.id);
        if (s && raceOf(s)?.key === "jackalope")
            refreshForm(p, s);
    }
});
function reticle(p, s) {
    const race = raceOf(s);
    if (!race)
        return;
    const a = selected(s, race);
    if (!a.needsTarget || (!a.aim && !a.range))
        return;
    const t = a.aim ? a.aim(p, s) : aimTarget(p, a.range ?? 8, a.cone ?? 14);
    if (t)
        privateParticle(p, "plrace:target_reticle", chest(t), rgb(RGB.green));
}
function startLoops() {
    startScheduler();
    system.runInterval(() => {
        for (const s of all()) {
            if (!s.channel)
                continue;
            const p = playerById(s.id);
            if (p)
                tickChannel(p, s);
        }
        tickProxies();
    }, 1);
    let phase = 0;
    system.runInterval(() => {
        phase++;
        for (const p of players()) {
            const s = peek(p.id);
            const race = s && raceOf(s);
            if (!s || !race)
                continue;
            try {
                if (s.tempVariant && s.tempVariant.until <= system.currentTick)
                    refreshForm(p, s);
                else if (s.flags.size)
                    refreshForm(p, s);
                else if (!s.tempVariant && !s.data.veiled && !s.diag && race.variant(p, s) !== s.shownVariant)
                    refreshForm(p, s);
                race.tick5?.(p, s);
                updateHud(p, s);
                if (phase % 2 === 0 && holdingFocus(p, race))
                    reticle(p, s);
            }
            catch (e) {
                warn("tick5 failed", e);
            }
        }
        if (phase % 2 === 0) {
            tickMarks();
            tickMirages();
        }
        tickStatuses();
        for (const r of RACES) {
            if (!r.worldTick4)
                continue;
            try {
                r.worldTick4();
            }
            catch (e) {
                warn(`${r.key} world tick failed`, e);
            }
        }
    }, 4);
    system.runInterval(() => {
        for (const p of players()) {
            const s = peek(p.id);
            const race = s && raceOf(s);
            if (!s || !race)
                continue;
            try {
                race.tick20(p, s);
                integrity(p, s);
            }
            catch (e) {
                warn("tick20 failed", e);
            }
        }
        cleanupEnsnared();
    }, 20);
    system.runInterval(() => {
        try {
            bloodMoonTick();
        }
        catch (e) {
            warn("blood moon tick failed", e);
        }
    }, 40);
    system.runInterval(() => {
        for (const p of players()) {
            const s = peek(p.id);
            if (s)
                save(p, s);
        }
    }, SAVE_INTERVAL);
    system.runTimeout(() => {
        purgeOrphans();
        for (const p of players())
            clearHeavenFog(p);
    }, 40);
    system.runInterval(() => purgeOrphans(), 1200);
}
world.afterEvents.worldLoad.subscribe(() => {
    startLoops();
    for (const p of players())
        onJoin(p, false);
});
