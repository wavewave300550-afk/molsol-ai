"""Hero preview images of the remastered legends (two views/forms per boss) and a showcase grid."""
import importlib
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from animview import pose_from          # noqa: E402
from modelkit import render_preview     # noqa: E402
import lmat                             # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "docs")
BG = (16, 14, 24, 255)


def posed(mod, loops_w, t=0.6, hide=None, act=None, tick=0):
    loops = mod.loops()
    anims = {k: loops[k] for k in loops_w}
    w = dict(loops_w)
    if act:
        a = {x.name: x for x in mod.acts()}[act].to_json()
        anims[act] = a
        w[act] = 1.0
        t = tick / 20.0
    env = {"v_t": t, "v_dist": 0.0, "life_time": t, "v_open": 1.0, "v_size": 1.0}
    pose = pose_from(anims, t, env, w)
    for b, s in (hide or {}).items():
        pose.setdefault(b, {})["scale"] = s
    return pose


def pair(name, views, title, size=620):
    mod = importlib.import_module(name)
    m = mod.build()
    lmat.VARIANT["name"] = "default"
    m.paint()
    tiles = []
    for (label, pose, yaw, pitch, variant) in views:
        if variant:
            lmat.VARIANT["name"] = variant
            m.paint()
        p = os.path.join(OUT, "_tile.png")
        render_preview([m], p, yaw=yaw, pitch=pitch, size=size, pose=pose, step=1, bg=BG)
        im = Image.open(p).convert("RGBA")
        ImageDraw.Draw(im).text((12, size - 22), label, fill=(235, 225, 200, 255))
        tiles.append(im)
        if variant:
            lmat.VARIANT["name"] = "default"
            m.paint()
    out = Image.new("RGBA", (size * len(tiles), size + 34), BG)
    ImageDraw.Draw(out).text((12, 10), title, fill=(255, 236, 170, 255))
    for i, im in enumerate(tiles):
        out.paste(im, (i * size, 34))
    path = os.path.join(OUT, f"preview_{name.split('_', 1)[1]}.png")
    out.save(path)
    os.remove(os.path.join(OUT, "_tile.png"))
    print("wrote", path)
    return path


def main():
    import boss_taotie as ta, boss_nidhogg as ni, boss_hanuman as ha, boss_alicorn as al, boss_tenko as te, boss_logos as lo
    paths = []
    paths.append(pair("boss_taotie", [
        ("Phase I-II: the bronze glutton", posed(ta, {"idle": 1.0}, hide={"vortex": 0.001, "pitglow_r": 0.001, "pitglow_l": 0.001}), 35, 14, None),
        ("Phase III: the self-devoured head on its vortex", posed(ta, {"idle": 1.0, "form3": 1.0}, hide={"hull": 0.001, "neck_mesh": 0.001}), -35, 10, "heated"),
    ], "TAOTIE - The Devouring Maw"))
    paths.append(pair("boss_nidhogg", [
        ("On the roots: wings folded", posed(ni, {"idle": 1.0, "fold": 1.0}), 35, 14, None),
        ("Ragnarok: in flight, veins ablaze", posed(ni, {"idle": 1.0, "fly": 1.0, "rage": 1.0}), -140, 24, "ragnarok"),
    ], "NIDHOGG - Gnawer of the World-Root"))
    hx = {f"xarm_{n}": 0.001 for n in ha.XARMS}
    hx.update({k: 0.001 for k in ("face_r", "face_l", "face_b", "tailfire3", "tailfire4", "tailfire5", "tailfire_tip")})
    paths.append(pair("boss_hanuman", [
        ("Son of the Wind: khon stance", posed(ha, {"idle": 1.0}, hide=hx), 30, 8, None),
        ("Four Faces, Eight Arms, tail ablaze", posed(ha, {"idle": 1.0, "divine": 1.0}), -150, 8, None),
    ], "HANUMAN - Son of the Wind"))
    paths.append(pair("boss_alicorn", [
        ("Grounded: wings folded, horn reading GOLD", posed(al, {"idle": 1.0, "fold": 1.0}, hide={"crown": 0.001, "horn_hue0": 0.001, "horn_hue1": 0.001, "horn_hue2": 0.001}), 40, 12, None),
        ("Dawnstar Ascendant: wings spread, crown of stars", posed(al, {"idle": 1.0, "fly": 1.0}, hide={"horn_hue1": 0.001, "horn_hue2": 0.001, "horn_hue3": 0.001}), -140, 20, None),
    ], "ALICORN - Dawnstar Sovereign"))
    paths.append(pair("boss_tenko", [
        ("Nine tails, the tenth sealed", posed(te, {"idle": 1.0}, hide={"unseal": 0.001}), 40, 12, None),
        ("Tenfold Eclipse: the tenth tail unsealed", posed(te, {"idle": 1.0, "eclipse": 1.0}, hide={"seal": 0.001}), -150, 12, None),
    ], "TENKO - The Ten-Tailed Fox"))
    paths.append(pair("boss_logos", [
        ("In the Beginning: the Eye closed, pages folded", posed(lo, {"idle": 1.0, "fold": 1.0}), 25, 8, None),
        ("Alpha and Omega: the Eye open, scripture-wings", posed(lo, {"idle": 1.0}, hide={"seal1": 0.001, "seal2": 0.001, "seal3": 0.001}), -20, 8, None),
    ], "THE WORD OF GOD"))
    # the Choir
    import choir_seraph as cs, choir_cherub as cc, choir_ophan as co
    tiles = []
    for mod, label, yaw in ((cs, "SERAPH - six fiery wings, the live coal", 25), (cc, "CHERUB - four faces, the flaming sword", 30), (co, "OPHAN - wheels within wheels, full of eyes", 35)):
        m = mod.build()
        m.paint()
        p = os.path.join(OUT, "_tile.png")
        hide = {"ward": {"scale": 0.001}} if mod is cc else None
        render_preview([m], p, yaw=yaw, pitch=8, size=520, pose=hide, step=1, bg=BG)
        im = Image.open(p).convert("RGBA")
        ImageDraw.Draw(im).text((12, 498), label, fill=(235, 225, 200, 255))
        tiles.append(im)
    out = Image.new("RGBA", (520 * 3, 554), BG)
    ImageDraw.Draw(out).text((12, 10), "THE CHOIR OF THE WORD", fill=(255, 236, 170, 255))
    for i, im in enumerate(tiles):
        out.paste(im, (i * 520, 34))
    cp = os.path.join(OUT, "preview_choir.png")
    out.save(cp)
    os.remove(os.path.join(OUT, "_tile.png"))
    print("wrote", cp)
    # showcase grid: first view of each boss
    thumbs = [Image.open(p).crop((0, 34, 620, 654)).resize((420, 420)) for p in paths]
    grid = Image.new("RGBA", (420 * 3, 420 * 2 + 40), BG)
    ImageDraw.Draw(grid).text((12, 12), "LEGENDARY & DIVINE BEINGS - REMASTERED", fill=(255, 236, 170, 255))
    for i, im in enumerate(thumbs):
        grid.paste(im, ((i % 3) * 420, 40 + (i // 3) * 420))
    grid.save(os.path.join(OUT, "showcase.png"))
    print("wrote showcase")


if __name__ == "__main__":
    main()
