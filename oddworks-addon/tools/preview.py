"""
Preview renders of every ODDWORKS model, in isolation and held by the player (third and
first person), using the same pose data that build.py writes into the resource pack.

    BEDROCK_SAMPLES=<path to Mojang/bedrock-samples> python3 tools/preview.py [out_dir]
"""
from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import anims  # noqa: E402
import modelkit as mk  # noqa: E402
import models  # noqa: E402
import rig  # noqa: E402

BG = (28, 32, 42, 255)
SKY = (124, 168, 222, 255)


def emissive_model(m: mk.Model):
    """Mark faces painted with low alpha as emissive (entity_emissive_alpha semantics)."""
    if m.texture is None:
        m.paint()
    img = m.texture
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if 0 < a < 250:
                px[x, y] = (r, g, b, 255)
    return m


def showcase(m: mk.Model, target, dist, yaw, pitch, hide=(), pose=None, size=(420, 420), ortho=None):
    mats = mk.world_matrices(m, mk.Pose(**(pose or {})))
    sc = mk.Scene()
    sc.add_model(m, mats, hide=hide)
    cam = mk.orbit_camera(target=target, dist=dist, yaw=yaw, pitch=pitch, fov=26, ortho_height=ortho)
    return mk.glow(sc.render(cam, size, bg=BG), radius=5, strength=0.55)


def held(item: mk.Model, ppose, ipose, cam, size=(420, 420), first_person=False, bg=BG, extra_hide=()):
    player = rig.player_model()
    pm, im = rig.attach(player, ppose, item, mk.Pose(**ipose))
    sc = mk.Scene()
    hide = rig.FP_HIDE if first_person else ()
    sc.add_model(player, pm, hide=hide)
    sc.add_model(item, im, hide=extra_hide)
    return mk.glow(sc.render(cam, size, bg=bg), radius=4, strength=0.5)


def label(img, text):
    d = ImageDraw.Draw(img)
    d.rectangle([0, img.height - 22, img.width, img.height], fill=(0, 0, 0, 150))
    d.text((8, img.height - 18), text, fill=(235, 235, 235, 255))
    return img


def sheet(images, cols, path):
    w, h = images[0].size
    rows = (len(images) + cols - 1) // cols
    out = Image.new("RGBA", (w * cols, h * rows), BG)
    for i, im in enumerate(images):
        out.paste(im, ((i % cols) * w, (i // cols) * h))
    out.save(path)
    return out


def tp_cam(target=(0, 22, 0), yaw=-40, pitch=10, dist=60):
    return mk.orbit_camera(target=mk.rh(target), dist=dist, yaw=yaw, pitch=pitch, fov=32)


def render_all(out):
    os.makedirs(out, exist_ok=True)
    gp, hp, cp = anims.goggles_poses(), anims.handline_poses(), anims.cane_poses()
    G = lambda: emissive_model(models.goggles())
    H = lambda cast=False: emissive_model(models.handline(cast))
    C = lambda drawn=False: emissive_model(models.cane(drawn))

    # ---------------------------------------------------------------- isolated showcase
    shots = []
    g = G()
    shots.append(label(showcase(g, mk.rh((0, 28, -4.9)), 28, -28, 12, hide=("fp_root", "fp_mask", "tp_glow_full")),
                       "Solar Frost Goggles"))
    shots.append(label(showcase(G(), mk.rh((0, 28, -2)), 34, 150, 14, hide=("fp_root", "fp_mask", "tp_glow", "tp_glow_full")),
                       "Goggles - soot-black inside"))
    shots.append(label(showcase(H(), mk.rh((0, 25, -1)), 30, -35, 18), "Endless Handline"))
    shots.append(label(showcase(C(False), mk.rh((0, 17, 0)), 62, -30, 8), "Bamboo Sword Cane (sheathed)"))
    shots.append(label(showcase(C(True), mk.rh((0, 12, 0)), 66, -30, 8, hide=("hip_sheath",),
                                pose={"sheath": {"position": [0, -11, 0]}}), "Drawn: blade + sheath"))
    hook = emissive_model(models.handline_sinker())
    shots.append(label(showcase(hook, mk.rh((0, 1, 0)), 12, -30, 12), "Hook & lead sinker"))
    sheet(shots, 3, os.path.join(out, "items.png"))

    # ---------------------------------------------------------------- third person
    tp = []
    face = tp_cam((0, 27, 0), yaw=-32, pitch=6, dist=34)
    tp.append(label(held(G(), rig.THIRD_PERSON_HOLD, gp["tp_up"], face), "TP goggles: resting on forehead"))
    tp.append(label(held(G(), rig.THIRD_PERSON_HOLD, gp["tp_down"], face), "TP goggles: pulled down, charging"))
    tp.append(label(held(H(), rig.THIRD_PERSON_HOLD, hp["tp_idle"], tp_cam((0, 18, 0), -55, 8, 62)), "TP handline: carried"))
    whirl_pose = mk.Pose(rightArm={"rotation": [-158, 0, 0]})
    tp.append(label(held(H(), whirl_pose, hp["tp_whirl"], tp_cam((0, 26, 0), -55, 14, 78)), "TP handline: overhead whirl"))
    tp.append(label(held(C(False), rig.THIRD_PERSON_HOLD, cp["tp_cane"], tp_cam((0, 16, 0), -60, 8, 66)), "TP cane: walking stick"))
    tp.append(label(held(C(True), rig.THIRD_PERSON_HOLD, cp["tp_drawn"], tp_cam((0, 18, 0), -60, 8, 66)), "TP cane: blade drawn"))
    sheet(tp, 3, os.path.join(out, "third_person.png"))

    # ---------------------------------------------------------------- first person
    fp = []
    cam = rig.fp_camera()
    size = (480, 270)
    fp.append(label(held(G(), rig.FIRST_PERSON, gp["fp_held"], cam, size, True, SKY), "FP goggles held"))
    fp.append(label(held(G(), rig.FIRST_PERSON, gp["fp_raised"], cam, size, True, SKY), "FP goggles raised: slit view"))
    fp.append(label(held(H(), rig.FIRST_PERSON, hp["fp_idle"], cam, size, True, SKY), "FP handline"))
    fp.append(label(held(H(), rig.FIRST_PERSON, hp["fp_whirl"], cam, size, True, SKY), "FP handline whirl"))
    fp.append(label(held(C(False), rig.FIRST_PERSON, cp["fp_guard"], cam, size, True, SKY), "FP cane"))
    fp.append(label(held(C(False), rig.FIRST_PERSON, cp["fp_grip"], cam, size, True, SKY), "FP iai grip"))
    fp.append(label(held(C(True), rig.FIRST_PERSON, cp["fp_drawn"], cam, size, True, SKY), "FP blade drawn"))
    fp.append(label(held(C(True), rig.FIRST_PERSON, cp["fp_deflect"], cam, size, True, SKY), "FP deflect"))
    sheet(fp, 2, os.path.join(out, "first_person.png"))


if __name__ == "__main__":
    render_all(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "docs", "previews"))
