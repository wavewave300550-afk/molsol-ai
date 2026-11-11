"""Caster poses played on the player with Entity.playAnimation (no player.entity.json override).

Third person only: every channel is gated by variable.is_first_person so the first-person arm
(which carries the floating book) is never displaced."""
from .anim import Anim, anim_file
from .fxdefs import dump

TP = "(variable.is_first_person ? 0 : 1)"


def write(rp):
    ch = Anim("animation.grimoire.player.channel", loop=True)
    ch.rot("rightarm", [f"{TP} * (-62 + math.sin(q.life_time * 260) * 2.5)", f"{TP} * -12", f"{TP} * 8"])
    ch.rot("leftarm", [f"{TP} * (-28 + math.cos(q.life_time * 200) * 2)", f"{TP} * 14", f"{TP} * -18"])
    ch.rot("body", [0, f"{TP} * -6", 0])
    rel = Anim("animation.grimoire.player.release", length=0.4)
    rel.rot("rightarm", {0: [f"{TP} * -62", 0, 0], 0.08: [f"{TP} * -96", f"{TP} * -10", 0], 0.4: [0, 0, 0]})
    rel.rot("leftarm", {0: [f"{TP} * -28", 0, 0], 0.1: [f"{TP} * -12", f"{TP} * 20", f"{TP} * -30"], 0.4: [0, 0, 0]})
    rel.rot("body", {0: [0, 0, 0], 0.08: [f"{TP} * 6", f"{TP} * -8", 0], 0.4: [0, 0, 0]})
    dump(f"{rp}/animations/grimoire/player_cast.animation.json", anim_file([ch, rel]))
