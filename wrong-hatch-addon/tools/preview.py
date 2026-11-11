"""Render reference-style turnarounds of the models:  python3 tools/preview.py OUTDIR"""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import voxkit  # noqa: E402


def turnaround(model, tex, path, pose=None, size=480, views=((0, "front"), (180, "back"), (-90, "left side"), (90, "right side")), pitch=4, label=True):
    imgs = []
    # common scale for every view
    span = None
    for yaw, _ in views:
        mn, mx = model.extent(pose)
    ext = max(mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]) * 1.08
    for yaw, name in views:
        im = voxkit.render(model, tex, yaw=yaw, pitch=pitch, size=size, pose=pose, fixed_span=ext,
                           center=(0, (mn[1] + mx[1]) / 2))
        if label:
            ImageDraw.Draw(im).text((8, 8), name, fill=(90, 90, 90))
        imgs.append(im)
    out = Image.new("RGB", (size * len(imgs), size), (255, 255, 255))
    for i, im in enumerate(imgs):
        out.paste(im, (i * size, 0))
    out.save(path)
    return out


def sample_pose(anim: dict, t: float, scale: float = 2.0) -> dict:
    """Linear sample of numeric keyframes (molang strings count as 0) for previews."""
    pose = {}

    def val(x):
        return x if isinstance(x, (int, float)) else 0.0

    def samp(ch):
        if isinstance(ch, list):
            return [val(v) for v in ch]
        if isinstance(ch, (int, float)):
            return [ch] * 3
        if isinstance(ch, str):
            return [0, 0, 0]
        keys = sorted(ch, key=float)
        pts = [(float(k), ch[k]["post"] if isinstance(ch[k], dict) else ch[k]) for k in keys]
        pts = [(k, [val(x) for x in (v if isinstance(v, list) else [v] * 3)]) for k, v in pts]
        if t <= pts[0][0]:
            return pts[0][1]
        for (k0, v0), (k1, v1) in zip(pts, pts[1:]):
            if k0 <= t <= k1:
                f = (t - k0) / max(1e-6, k1 - k0)
                return [a + (b - a) * f for a, b in zip(v0, v1)]
        return pts[-1][1]
    for bone, chans in anim.get("bones", {}).items():
        p = {}
        if "rotation" in chans:
            p["rotation"] = tuple(samp(chans["rotation"]))
        if "position" in chans:
            p["position"] = tuple(v / scale for v in samp(chans["position"]))
        if "scale" in chans:
            s = chans["scale"]
            sv = samp(s) if not isinstance(s, str) else [1, 1, 1]
            p["scale"] = tuple(sv) if not isinstance(s, (int, float)) else s
        pose[bone] = p
    return pose


def docs(outdir):
    """Images for the README: reference comparison, phase textures, ability poses, minions."""
    import anims
    import boss_model
    import minion_models
    os.makedirs(outdir, exist_ok=True)
    m = boss_model.build()
    texs = [m.paint(v) for v in range(3)]
    # 1) turnaround next to the approved sheet
    views = turnaround(m, texs[0], os.path.join(outdir, "turnaround.png"), size=480)
    ref_path = os.environ.get("WH_REFERENCE")
    if ref_path and os.path.exists(ref_path):
        ref = Image.open(ref_path).convert("RGB")
        W = views.width
        ref = ref.resize((W, int(ref.height * W / ref.width)))
        out = Image.new("RGB", (W, ref.height + views.height + 40), (255, 255, 255))
        d = ImageDraw.Draw(out)
        out.paste(ref, (0, 20))
        out.paste(views, (0, ref.height + 40))
        d.text((8, 4), "approved reference sheet", fill=(80, 80, 80))
        d.text((8, ref.height + 24), "in-pack model (software render of the exported geometry + texture)", fill=(80, 80, 80))
        out.save(os.path.join(outdir, "model_vs_reference.png"))
    # 2) the three phase textures
    names = ["Phase I - The Shell", "Phase II - The Crack", "Phase III - The Hatching"]
    row = Image.new("RGB", (3 * 420, 440), (255, 255, 255))
    for i, t in enumerate(texs):
        im = voxkit.render(m, t, yaw=28, pitch=8, size=420)
        row.paste(im, (i * 420, 20))
        ImageDraw.Draw(row).text((i * 420 + 10, 4), names[i], fill=(60, 60, 60))
    row.save(os.path.join(outdir, "phases.png"))
    # 3) ability poses sampled from the real animation files
    A = anims.boss_animations()
    shots = [("intro", 2.1, "Hatching intro"), ("guillotine", 0.95, "Wing Guillotine wind-up"),
             ("broodquake", 0.85, "Broodquake hop"), ("egg_mortar", 0.7, "Egg Mortar"),
             ("fortress_hold", 0.0, "Shell Fortress"), ("rush_windup", 1.4, "Rooster Rush wind-up"),
             ("beam_charge", 1.4, "Yolk Beam charge"), ("dawn_flash", 2.4, "Dawn Flash"),
             ("sky_hover", 0.15, "Sky Drop"), ("molt_storm", 0.2, "Molt Storm"),
             ("final_hatch", 0.0, "Final Hatch"), ("death", 4.6, "Death sequence")]
    cell = 300
    sheet = Image.new("RGB", (cell * 4, (cell + 18) * 3), (255, 255, 255))
    for i, (n, t, label) in enumerate(shots):
        pose = sample_pose(A["animation.wrong_hatch." + n], t)
        tex = texs[2] if n in ("final_hatch", "death", "dawn_flash", "beam_charge") else texs[1 if i > 4 else 0]
        im = voxkit.render(m, tex, yaw=32, pitch=10, size=cell, pose=pose, fixed_span=100, center=(0, 22))
        x, y = (i % 4) * cell, (i // 4) * (cell + 18)
        sheet.paste(im, (x, y + 18))
        ImageDraw.Draw(sheet).text((x + 8, y + 3), label, fill=(60, 60, 60))
    sheet.save(os.path.join(outdir, "abilities.png"))
    # 4) minions
    items = [("chick", 0, "Wrong Chick"), ("chick", 1, "Yolkling"), ("egg", 0, "Hatch Egg"), ("egg", 1, "Rotten Egg"),
             ("egg", 2, "Gilded Egg"), ("brood_shell", 0, "Brood Shell")]
    cell = 220
    row = Image.new("RGB", (cell * len(items), cell + 18), (255, 255, 255))
    for i, (n, v, label) in enumerate(items):
        mm = minion_models.ALL[n]()
        im = voxkit.render(mm, mm.paint(v), yaw=30, pitch=12, size=cell)
        row.paste(im, (i * cell, 18))
        ImageDraw.Draw(row).text((i * cell + 8, 3), label, fill=(60, 60, 60))
    row.save(os.path.join(outdir, "minions.png"))


if __name__ == "__main__":
    import boss_model
    outdir = sys.argv[1] if len(sys.argv) > 1 else "."
    if "--docs" in sys.argv:
        docs(outdir)
        sys.exit(0)
    os.makedirs(outdir, exist_ok=True)
    m = boss_model.build()
    print(m.stats())
    for v in range(3):
        tex = m.paint(v)
        tex.save(os.path.join(outdir, f"boss_tex_{v}.png"))
        turnaround(m, tex, os.path.join(outdir, f"boss_views_{v}.png"))


