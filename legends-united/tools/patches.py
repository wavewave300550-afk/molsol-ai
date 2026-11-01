"""
Script patches applied to the copied packs (the original add-ons are never modified).
Each entry: script path inside the combined BP -> [(old, new), ...]; every `old` must occur exactly once.

What they do
  * rivalry   - each host's target pool and hit tests include the bosses of the other two hosts
                (shared/rivals.js); hits on a rival boss are multiplied by RIVAL_DAMAGE.
  * safety    - player-only calls (titles, names, taunts, threat) are skipped for boss targets;
                boss rivals never count as extra players for HP scaling.
  * teams     - Final Bosses' hit filter ignored the 11th-dimension beings (a copy-paste from that
                pack); it now ignores its own team instead.
  * eggs      - Legendary bosses that come out of a spawn egg start a full fight with entrance.
"""

FOES = '''
/** Legends United: players plus the bosses of the other two hosts. */
export function foesNear(dim, at, radius) {
    return [...playersNear(dim, at, radius), ...rivalsNear(TEAM, dim, at, radius)];
}
export function isFoe(e) {
    return e instanceof Player ? isCombatPlayer(e) : isRivalOf(TEAM, e);
}
'''


def engine_patches(team, players_line, taunt_line, threat_line):
    return [
        ('import { chest, healthOf, isCombatPlayer, lineOfSight, playersNear } from "./core/targets.js";',
         'import { chest, foesNear, healthOf, isCombatPlayer, isFoe, lineOfSight, playersNear } from "./core/targets.js";'),
        (players_line, players_line.replace("playersNear(", "foesNear(")),
        ("        return p instanceof Player && isCombatPlayer(p) && p.dimension.id === this.dim.id ? p : undefined;",
         "        return p && isFoe(p) && p.dimension.id === this.dim.id ? p : undefined;"),
        (taunt_line, taunt_line.replace("if (", "if (best instanceof Player && ", 1)),
        (threat_line, threat_line.replace("instanceof Player", "&& isFoe(" + threat_line.split("(")[1].split(" ")[0] + ")")),
    ]


def targets_patches(team, ignore=None):
    out = [
        ('import { add, dist, scale, sub } from "./vec.js";\n',
         'import { add, dist, scale, sub } from "./vec.js";\n'
         'import { isRivalOf, RIVAL_DAMAGE, rivalsNear } from "../../shared/rivals.js";\n'
         f'const TEAM = "{team}";\n'),
        ("export function playersNear(dim, at, radius) {\n    return dim.getPlayers({ location: at, maxDistance: radius }).filter(isCombatPlayer);\n}\n",
         "export function playersNear(dim, at, radius) {\n    return dim.getPlayers({ location: at, maxDistance: radius }).filter(isCombatPlayer);\n}\n" + FOES),
        ("    if (!target.isValid || amount <= 0)\n        return false;\n",
         "    if (!target.isValid || amount <= 0)\n        return false;\n    if (isRivalOf(TEAM, target))\n        amount *= RIVAL_DAMAGE;\n"),
    ]
    if ignore:
        out += ignore
    return out


TITLE = [("    p.onScreenDisplay.setTitle(main, {", "    p.onScreenDisplay?.setTitle(main, {")]

PATCHES = {
    "dim11/core/targets.js": targets_patches("dim11"),
    "dim11/core/fx.js": TITLE,
    "dim11/engine.js": engine_patches("dim11", "        const players = playersNear(this.dim, here, 56);",
                                      "            if (t - this.lastTargetCall > 300) {",
                                      "        if (by instanceof Player)"),
    "dim11/beings/archon.js": [("${target.name}.", '${target.name ?? "intruder"}.')],

    "fb/core/targets.js": targets_patches("fb", [
        ('const IGNORED_FAMILIES = new Set(["dim11_being", "dim11_minion", "dim11_illusion", "inanimate"]);',
         'const IGNORED_FAMILIES = new Set(["fb_boss", "fb_illusion", "inanimate"]);'),
        ('e.typeId.startsWith("dim11:")', 'e.typeId.startsWith("fb:")'),
    ]),
    "fb/core/fx.js": TITLE,
    "fb/engine.js": engine_patches("fb", "        const players = playersNear(this.dim, here, 64);",
                                   "            if (t - this.lastTaunt > 400) {",
                                   "        if (attacker instanceof Player)"),
    "fb/bosses/emperor.js": [("${target.name}.", '${target.name ?? "pretender"}.')],

    "legends/core/combat.js": [
        ('import { Difficulty, EntityDamageCause, EntityHealthComponent, GameMode, system, world, } from "@minecraft/server";\n',
         'import { Difficulty, EntityDamageCause, EntityHealthComponent, GameMode, Player, system, world, } from "@minecraft/server";\n'
         'import { isRivalOf, RIVAL_DAMAGE, rivalsNear } from "../../shared/rivals.js";\n'),
        ("export function isFighter(p) {\n    if (!p.isValid)\n        return false;\n",
         "export function isFighter(p) {\n    if (!p.isValid)\n        return false;\n    if (!(p instanceof Player))\n        return isRivalOf(\"legends\", p);\n"),
        ("        return dim.getPlayers({ location: at, maxDistance: radius }).filter(isFighter);\n",
         "        return [...dim.getPlayers({ location: at, maxDistance: radius }).filter(isFighter), ...rivalsNear(\"legends\", dim, at, radius)];\n"),
        ("    const dmg = Math.max(0.5, amount * difficultyMul());\n",
         "    const dmg = Math.max(0.5, amount * difficultyMul()) * (isRivalOf(\"legends\", p) ? RIVAL_DAMAGE : 1);\n"),
    ],
    "legends/bosses/boss.js": [
        ('import { EntityDamageCause, ItemStack } from "@minecraft/server";',
         'import { EntityDamageCause, ItemStack, Player } from "@minecraft/server";'),
        ("        this.maxFighters = Math.max(this.maxFighters, this.fighters.length);",
         "        this.maxFighters = Math.max(this.maxFighters, this.fighters.filter((p) => p instanceof Player).length);"),
    ],
    "legends/main.js": [
        ('import { adoptOrphans, clearAll, tickBeings } from "./bosses/registry.js";',
         'import { adoptOrphans, BOSS_IDS, clearAll, controlBoss, tickBeings } from "./bosses/registry.js";'),
        ("// --------------------------------------------------------------------------- main loop\n",
         "// --------------------------------------------------------------------------- spawn eggs\n"
         "// A legend hatched from a spawn egg starts a full fight (entrance included).\n"
         "world.afterEvents.entitySpawn.subscribe((ev) => {\n"
         "    const e = ev.entity;\n"
         "    if (!e.isValid || !BOSS_IDS.includes(e.typeId))\n"
         "        return;\n"
         "    system.runTimeout(() => {\n"
         "        if (e.isValid && !beings.has(e.id))\n"
         "            controlBoss(e, false);\n"
         "    }, 1);\n"
         "});\n"
         "// --------------------------------------------------------------------------- main loop\n"),
    ],
}


def apply(scripts_dir):
    import os
    n = 0
    for rel, reps in PATCHES.items():
        path = os.path.join(scripts_dir, rel)
        s = open(path, encoding="utf-8").read()
        for old, new in reps:
            c = s.count(old)
            if c != 1:
                raise SystemExit(f"patch {rel}: expected 1 match, found {c}: {old[:80]!r}")
            s = s.replace(old, new)
            n += 1
        open(path, "w", encoding="utf-8").write(s)
    return n
