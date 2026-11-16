"""Race 009 Octamyces Undecimus - attachable animation set.

GATE A/B PLACEHOLDER (v1.5 redesign in progress): only the structural layers the new body needs
(view switching, the look cancel that keeps the cap on its stalk, a slow hover, gaze, a lean
into movement) and an intro + fx per form.  The full performance set - jellyfish tendrils,
blink, four idle behaviours, the vigil, attack / hurt / swim / landing and the form loops -
replaces this file at gate C.  Same public interface: anims(model) -> {"anims", "animate",
"particles", "controllers", "pre"}.
"""
from __future__ import annotations

from typing import Dict

from anims.core import NS, T, n
from anims.life import MOVE, S, KeyLayer, Layer, Rig, body, drain_shared, lin, mul, shared_vars
from anims.races import A, TP, view_anims
from models.octamyces import FLOAT_C, MYC_PTS, RING_SIDES, RINGS, VARIANTS

R = "octamyces"
RIG = Rig("float", FLOAT_C, [("r_arm_g", MYC_PTS[0][0]), ("l_arm_g", MYC_PTS[1][0])], legs=(), tail=None)
SPIN = [14.0, -11.0, 9.0, -7.5, 6.0, -5.0, 4.2, -3.5, 2.9, -2.4, 2.0]   # degrees per second, alternating


def hover(ly: Layer, lean=None, roll=None, bob=None) -> None:
    body(ly, RIG, lean=lean, roll=roll, bob=bob)
    ly.rot("float_h", lean, None, roll)
    if bob is not None:
        ly.pos("float_h", None, bob, None)


def anims(model) -> Dict[str, object]:
    r = R
    fp, tp = view_anims(r)
    for g in (0, 1):                     # first person: only the sleeves show
        fp.bone(f"myc{g}_0", scale=0)

    steady = Layer(r, "steady", loop=True)
    steady.rot("head_g", "-q.target_x_rotation", None, None)
    steady.rot("steady", None, "-q.target_y_rotation", None)

    gaze = Layer(r, "gaze", loop=True)
    gaze.rot("cap", "math.clamp(q.target_x_rotation, -50, 50) * 0.1", "math.clamp(q.target_y_rotation, -70, 70) * 0.2", None)
    gaze.rot("iris", "math.clamp(q.target_x_rotation * 0.3, -12, 12)", "math.clamp(q.target_y_rotation * 0.3, -14, 14)", None)
    for k in range(RINGS):
        gaze.rot(f"ring{k}", None, None, f"{T} * {n(SPIN[k])}")
    gaze.rot("pupil", None, None, f"{T} * -6")

    life = Layer(r, "life", loop=True)
    hover(life, roll=mul(1.2, S(0.13)), bob=lin([(0.7, S(0.3)), (0.15, S(0.9, 40))]))

    loco = Layer(r, "locomotion", loop=True)
    hover(loco, lean=mul(6.0, MOVE))
    loco.rot("cap", mul(3.0, MOVE), None, None)

    intro, fx = {}, {}
    for v in VARIANTS:
        ki = KeyLayer(r, f"intro_{v}", 0.6, loop="hold")
        for k in range(RINGS):
            ki.scale(f"ring{k}", {0: 0.85, 0.03 * k + 0.2: 1.04, 0.6: 1.0})
        intro[v] = ki
        fx[v] = A(r, f"fx_{v}", length=5.0).particle(0.0, "motes", "eye_c")

    built = [fp, tp, steady.anim(), gaze.anim(), life.anim(), loco.anim(), *[a.anim() for a in intro.values()],
             *fx.values()]
    animate = {}
    for v in VARIANTS:
        animate[v] = [("first_person", "c.is_first_person"), ("third_person", TP), ("steady", TP), ("gaze", TP),
                      ("life", TP), ("locomotion", f"{TP} && !q.is_riding"), (f"intro_{v}", None), (f"fx_{v}", TP)]
    particles = {"spores": f"{NS}:geo_spores", "motes": f"{NS}:parallax_motes", "echo": f"{NS}:parallax_echo"}
    _ = RING_SIDES
    return {"anims": built, "animate": animate, "particles": particles, "controllers": {},
            "pre": shared_vars() + ["v.plr_bob = 0;"] + drain_shared()}
