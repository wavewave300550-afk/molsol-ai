"""Assets that belong to the add-on as a whole: pack icon, codex item, shared text."""
from __future__ import annotations

import math

from PIL import Image, ImageDraw

from kit import icons
from kit import pack as K

BOSS_NAMES = {"vesperra": "Vesperra", "cantor": "Cantor XIII", "nomos": "Nomos", "orison": "Orison"}


def pack_icon() -> Image.Image:
    """256x256: a dark field quartered by four sigils, one per Miracle, around an empty centre."""
    s = 256
    img = Image.new("RGBA", (s, s), (16, 14, 20, 255))
    d = ImageDraw.Draw(img)
    for y in range(s):
        for x in range(0, s, 1):
            v = int(14 + 22 * (1 - math.hypot(x - 128, y - 128) / 182))
            img.putpixel((x, y), (v + 4, v, v + 8, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([6, 6, s - 7, s - 7], outline=(170, 150, 96, 255), width=3)
    d.line([(128, 18), (128, s - 19)], fill=(90, 80, 60, 255), width=2)
    d.line([(18, 128), (s - 19, 128)], fill=(90, 80, 60, 255), width=2)
    # ivory crown (Vesperra)
    for i, h in enumerate((30, 44, 58, 44, 30)):
        x = 38 + i * 13
        d.polygon([(x, 104), (x + 5, 104 - h), (x + 10, 104)], fill=(238, 228, 204, 255))
    d.rectangle([34, 102, 104, 110], fill=(194, 160, 74, 255))
    # bell (Cantor)
    d.pieslice([150, 40, 222, 124], 180, 360, fill=(168, 132, 62, 255))
    d.rectangle([150, 82, 222, 100], fill=(168, 132, 62, 255))
    d.rectangle([144, 100, 228, 108], fill=(96, 150, 140, 255))
    d.ellipse([180, 106, 192, 118], fill=(60, 44, 30, 255))
    # compass (Nomos)
    d.ellipse([40, 152, 100, 212], outline=(214, 196, 150, 255), width=4)
    d.polygon([(70, 156), (77, 182), (70, 208), (63, 182)], fill=(52, 150, 108, 255))
    d.line([(44, 182), (96, 182)], fill=(214, 196, 150, 255), width=2)
    # hourglass (Orison)
    d.polygon([(158, 150), (214, 150), (190, 182), (214, 214), (158, 214), (182, 182)], outline=(190, 198, 214, 255))
    d.polygon([(166, 156), (206, 156), (186, 180)], fill=(150, 160, 186, 255))
    d.polygon([(176, 208), (196, 208), (186, 196)], fill=(214, 196, 150, 255))
    d.ellipse([112, 112, 144, 144], fill=(10, 8, 12, 255), outline=(170, 150, 96, 255), width=2)
    return img


def build(keys) -> dict:
    lang = {
        "pack.name": K.ADDON_NAME,
        "pack.description": K.ADDON_TAGLINE,
        "item.abm:codex.name": "Codex of the Abandoned Miracles",
        "abm.msg.outside": "§7The Miracle does not notice what stands outside its hall.",
        "abm.msg.abandoned": "§7With no one left to witness it, the Miracle folds back into its seal.",
        "abm.msg.cancelled": "§7The encounter was dismissed.",
        "abm.summon.fail.overlap": "§cAnother Miracle is already awake too close to this place.",
        "abm.summon.fail.floor": "§cThis ground cannot hold it. A Miracle needs a wide, level, open floor (%s%% of what it needs was found).",
        "abm.summon.fail.ceiling": "§cThere is not enough open height here for a Miracle to stand.",
        "abm.summon.fail.unloaded": "§cThe area is not fully loaded yet. Step closer to the centre and try again.",
        "abm.summon.fail.unknown": "§cThis seal is silent.",
        "abm.summon.fail.spawn": "§cThe seal cracked, but nothing answered.",
        "abm.summon.warn.space": "§eThis Miracle was called into a cramped place. Its attacks assume a wide, level arena.",
        "abm.summon.need": "§7Needs a level, open circle about %s blocks across and %s blocks high.",
        "abm.arena.built": "§7An arena has been raised around you.",
        "abm.arena.denied": "§cOnly operators may raise an arena.",
        "abm.ui.title": "The Abandoned Miracles",
        "abm.ui.body1": "Four perfect miracles. Four catastrophic successes.",
        "abm.ui.body2": "Use a Seal on level, open ground to wake its Miracle. Every attack is marked on the floor before it lands: solid pulsing marks are danger, pale hollow lozenges are safety.",
        "abm.ui.settings": "Settings",
        "abm.ui.arena": "Raise a demonstration arena here",
        "abm.ui.arena.warn": "This REPLACES blocks in a %s x %s area around you with the arena and cannot be undone. Use it only on empty ground.",
        "abm.ui.confirm": "Raise it",
        "abm.ui.cancel": "Cancel",
        "abm.ui.dismiss": "Dismiss the nearest encounter",
        "abm.ui.difficulty": "Difficulty",
        "abm.ui.vfx": "Reduced decorative particles",
        "abm.ui.actionbar": "Action-bar status line",
        "abm.ui.movement": "Stepwise boss movement (fallback)",
        "abm.ui.saved": "§7Settings saved.",
        "itemGroup.name.abm": "The Abandoned Miracles",
    }
    icon = icons.icon([
        "................",
        "...kkkkkkkkkk...",
        "..kpppppppppgk..",
        "..kpddddddddgk..",
        "..kpdggddggdgk..",
        "..kpdgiddicdgk..",
        "..kpddddddddgk..",
        "..kpdd.gg.ddgk..",
        "..kpdnddddhdgk..",
        "..kpdnnddhhdgk..",
        "..kpddddddddgk..",
        "..kpdggggggdgk..",
        "..kpddddddddgk..",
        "..kpppppppppgk..",
        "...kkkkkkkkkk...",
        "................",
    ], {"k": "#120e14", "p": "#3a2a30", "d": "#241a22", "g": "#b08d3c", "i": "#f0e8d2", "c": "#a8843e", "n": "#34966c",
        "h": "#9aa2ba"})
    return {
        "pack_icon": pack_icon(),
        "lang": lang,
        "icons": {"abm_codex": icon},
        "items": {"codex": K.item("abm:codex", "abm_codex", stack=1, rarity="uncommon")},
        "recipes": {"codex": K.shaped_recipe("abm:codex", [" B ", "BKB", " B "],
                                             {"B": "minecraft:bone", "K": "minecraft:book"}, "abm:codex",
                                             ["minecraft:book"])},
    }
