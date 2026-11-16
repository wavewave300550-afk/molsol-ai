"""
preview_anims.py - render animation previews of VESPER-0 through the client simulator.

    python3 tools/preview_anims.py <out_dir> [sequence ...]

Each sequence is a server-style property timeline (what the script sets and when); the
client simulator runs the real pre_animation scripts, controllers and animations.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw  # noqa: E402

import render  # noqa: E402
import vesper_anims as va  # noqa: E402
import vesper_model as vm  # noqa: E402
from client_sim import ClientSim  # noqa: E402

DEFAULTS = {"sab:phase": 0, "sab:act": 0, "sab:heading": 0.0, "sab:pitch": 0.0, "sab:bank": 0.0,
            "sab:look_yaw": 0.0, "sab:look_pitch": 0.0, "sab:charge": 0.0, "sab:shield": False, "sab:skin": 0,
            "sab:rings": True, "sab:plates": True, "sab:limbs": False, "sab:censers": True, "sab:enrage": False}

A = va.ACT
SEQUENCES = {
    "transform": (10.0, [(0.0, {"sab:phase": 1, "sab:shield": True}), (3.0, {"sab:rings": False}),
                         (3.5, {"sab:limbs": True}), (3.95, {"sab:plates": False}), (6.6, {"sab:skin": 1}),
                         (9.0, {"sab:phase": 2, "sab:shield": False})], {}),
    "lance": (6.5, [(0.3, {"sab:act": A["lance_charge"], "sab:charge": 0.6}), (2.1, {"sab:act": A["lance_fire"], "sab:charge": 1.0}),
                    (4.8, {"sab:act": 0, "sab:charge": 0.0})], {}),
    "rite": (5.5, [(0.2, {"sab:act": A["rite"]}), (4.6, {"sab:act": 0})], {}),
    "pray_p1": (5.0, [(0.2, {"sab:act": A["pray"], "sab:shield": True, "sab:censers": False})], {}),
    "genuflect": (5.0, [(0.2, {"sab:act": A["genuflect"]}), (3.2, {"sab:act": A["vent_flare"]}), (4.7, {"sab:act": 0})], {}),
    "p2_lunge": (5.0, [(0.0, {}), (0.4, {"sab:act": A["lunge_windup"]}), (1.7, {"sab:act": A["lunge"]}), (2.4, {"sab:act": A["anchored"]}),
                       (4.4, {"sab:act": 0})], {"sab:phase": 2, "sab:skin": 1, "sab:rings": False, "sab:plates": False, "sab:limbs": True, "sab:censers": False}),
    "p2_nova": (5.0, [(0.3, {"sab:act": A["nova_charge"], "sab:charge": 1.0}), (3.3, {"sab:act": A["nova_release"], "sab:charge": 0.0}), (4.6, {"sab:act": 0})],
                {"sab:phase": 2, "sab:skin": 1, "sab:rings": False, "sab:plates": False, "sab:limbs": True, "sab:censers": False}),
    "p2_talons": (3.0, [(0.2, {"sab:act": A["talons"]})], {"sab:phase": 2, "sab:skin": 1, "sab:rings": False, "sab:plates": False, "sab:limbs": True, "sab:censers": False}),
    "death": (8.5, [(0.0, {"sab:phase": 3})], {"sab:phase": 2, "sab:skin": 1, "sab:rings": False, "sab:plates": False, "sab:limbs": True, "sab:censers": False}),
}


def hidden_for(props):
    hidden = ["shield"]
    if not props["sab:limbs"]:
        hidden += vm.LIMB_BONES
    if not props["sab:plates"]:
        hidden += vm.PLATE_BONES
    if not props["sab:rings"]:
        hidden += vm.RING_BONES
    if not props["sab:censers"]:
        hidden += vm.CENSER_BONES
    return hidden


def build_sim():
    anims = {va.short_name(a.name): a for a in va.all_anims()}
    ctrls = va.controllers()
    cmap = {"phase_controller": ctrls[0], "act_controller": ctrls[1]}
    return ClientSim(anims, cmap, va.ANIMATE, va.PRE_ANIMATION, va.INITIALIZE)


def run(name, out, model, textures, fps=8, size=(640, 400), cam=((30, 9, 26), (0, 4, 0)), sheet_cols=6,
        sheet_n=12, gif=True):
    duration, timeline, base_props = SEQUENCES[name]
    props = dict(DEFAULTS)
    props.update(base_props)
    if base_props.get("sab:phase") == 2:
        pass
    sim = build_sim()
    # pre-roll so the phase controller settles into its state before the timeline starts
    if props["sab:phase"] == 2:
        for _ in range(4):
            sim.step(1 / fps, dict(props))
    frames = []
    n = int(duration * fps)
    pending = sorted(timeline, key=lambda e: e[0])
    for i in range(n):
        t = i / fps
        while pending and pending[0][0] <= t + 1e-6:
            props.update(pending.pop(0)[1])
        pose = sim.step(1 / fps, dict(props))
        skin = "p2" if props["sab:skin"] else "p1"
        sc = render.Scene(size[0], size[1], bg_top=(10, 12, 26) if skin == "p1" else (16, 6, 24),
                          bg_bottom=(46, 38, 70) if skin == "p1" else (56, 22, 64))
        sc.set_camera(cam[0], cam[1], 42)
        render.ground_plane(sc, y=-6.0, size=48, checker=4)
        sc.add_model(model, {"main": textures[skin], "glow": textures["glow_" + skin]}, pose=pose,
                     hidden=hidden_for(props), position=(0, 0, 0))
        img = sc.image()
        ImageDraw.Draw(img).text((8, 8), f"{name}  t={t:4.1f}s  act={props['sab:act']} phase={props['sab:phase']}",
                                 fill=(255, 255, 255))
        frames.append(img)
    if gif:
        frames[0].save(os.path.join(out, f"{name}.gif"), save_all=True, append_images=frames[1:],
                       duration=int(1000 / fps), loop=0, optimize=False)
    step = max(1, len(frames) // sheet_n)
    picks = frames[::step][:sheet_n]
    cols = sheet_cols
    rows = (len(picks) + cols - 1) // cols
    tw, th = size[0] // 2, size[1] // 2
    sheet = Image.new("RGB", (tw * cols, th * rows))
    for k, im in enumerate(picks):
        sheet.paste(im.resize((tw, th)), ((k % cols) * tw, (k // cols) * th))
    sheet.save(os.path.join(out, f"{name}_sheet.png"))
    return sim.transitions_log


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    names = sys.argv[2:] or list(SEQUENCES)
    model, main_atlas, glow_atlas, _ = vm.build()
    textures = {"p1": main_atlas.render("p1"), "p2": main_atlas.render("p2"),
                "glow_p1": glow_atlas.render("p1"), "glow_p2": glow_atlas.render("p2")}
    for n in names:
        log = run(n, out, model, textures)
        print(n, "transitions:", log[:12])


if __name__ == "__main__":
    main()
