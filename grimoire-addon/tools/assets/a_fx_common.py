"""Shared effects: attack telegraph rings (all three Grimoires), the particle sprite sheet and
generic particles.  Module name sorts first so the sheet exists before other modules add effects."""
from kit import glyphs, tex
from kit.anim import LIFE, Anim
from kit.geo import Model
from kit.particles import Particles

THEMES = [("dw", glyphs.FIRST_WORD, "#fff3c4", "#e0a93a"), ("dn", list(glyphs.DREAM.values()), "#ffd9ec", "#8a6ad6"),
          ("ed", glyphs.DRACONIC, "#ffe2a0", "#e0762a")]


def particles(pack):
    """One Particles instance shared by every asset module (pack.fx)."""
    if not hasattr(pack, "fx"):
        pack.fx = Particles(pack)
    return pack.fx


def build(pack):
    fx = particles(pack)
    fx.write_sheet()
    # generic bursts usable by any spell
    fx.effect("fx_flash", "glow", count=1, life=(0.25, 0.35), size=(1.2, 3.2), colors=["#ffffffff", "#ffffff00"])
    fx.effect("fx_dust", "puff", count=10, life=(0.6, 1.2), size=(0.35, 0.9), shape=("disc", 1.2), speed=(0.6, 1.8),
              accel=(0, 0.4, 0), drag=1.5, colors=["#b8ad98cc", "#8a826f00"], blend="blend", spin=(360, 40))
    fx.effect("fx_shock", "ringthin", count=1, life=(0.45, 0.55), size=(0.4, 5.5), facing="emitter_transform_xz",
              colors=["#ffffffff", "#ffffff00"])

    # ---- telegraph: flat warning ring.  kind 0 divine / 1 dream / 2 dragon; scale with grimoire:size (radius in blocks)
    models = []
    for name, script, c0, c1 in THEMES:
        m = Model(f"telegraph_{name}", density=2.0, bounds=(40, 4, (0, 0, 0)))
        root = m.bone("root")
        rim = m.bone("rim", root)
        rim.plane("y", (0, 0.4, 0), 32, 32, tex.magic_circle(script, c0, c1, glow=1.0, bands=((0.78, 0.94, 16),),
                                                             lines=(0.74, 0.985, 0.955)), faces=("up",))
        fill = m.bone("fill", root)
        fill.plane("y", (0, 0.25, 0), 32, 32, tex.shaped(tex.m_disc(0.72), c1, c0, glow=0.75, var=0, a=1.0,
                                                         key=f"tgfill{name}"), faces=("up",))
        models.append(m)
    warn = Anim("warn", loop=True, length=1.0)
    warn.rot("rim", (0, LIFE(0, 1, base=0) + _spin(50), 0))
    warn.scl("fill", {0: 0.05, 1.0: 1.0}, smooth=False)
    hold = Anim("hold", loop=True)
    hold.rot("rim", (0, _spin(50), 0))
    hold.scl("fill", LIFE(0.04, 0.5, base=0.97))
    flash = Anim("flash", length=0.35, loop="hold")
    flash.scl("root", {0: 1.0, 0.12: 1.18, 0.35: 0.0})
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    slow = Anim("warn_slow", loop=True, length=2.0)
    slow.rot("rim", (0, _spin(30), 0))
    slow.scl("fill", {0: 0.05, 2.0: 1.0}, smooth=False)
    pack.actor("telegraph", models[0], [warn, hold, flash, hidden, slow],
               {0: ["hidden"], 1: ["warn"], 2: ["hold"], 3: ["flash"], 4: ["warn_slow"]},
               kinds=models[1:], size_prop=True, lifetime=40, display="Warning Sigil", blend=0.0)
    pack.preview("telegraph", models[0], [(hold, 0.3)], views=((0, 70), (30, 30)))


def _spin(rate):
    from kit.anim import M
    return M(f"q.life_time*{rate}", lambda t: t * rate)
