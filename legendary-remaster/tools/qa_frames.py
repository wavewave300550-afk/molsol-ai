"""Animation QA: render key frames of each boss's acts (strike marks, ultimate peaks, deaths) into contact sheets."""
import importlib
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from animview import pose_from          # noqa: E402
from modelkit import render_preview     # noqa: E402

PLAN = {
    "boss_taotie": [("idle", None, 0.5, {}), ("claw", 10, None, {}), ("quake", 14, None, {}), ("devour", 52, None, {}),
                    ("maw", 160, None, {"form3": 1.0}), ("death", 40, None, {"form3": 1.0})],
    "boss_nidhogg": [("idle", None, 0.5, {"fold": 1.0}), ("bite", 9, None, {"fold": 1.0}), ("breath", 30, None, {"fly": 1.0}),
                     ("gale", 8, None, {"fly": 1.0}), ("ragnarok", 60, None, {"fly": 1.0}), ("death", 60, None, {"fold": 1.0})],
    "boss_hanuman": [("idle", None, 0.5, {}), ("combo", 28, None, {}), ("guard", 30, None, {}), ("barrage", 16, None, {"divine": 1.0}),
                     ("yawn", 106, None, {"divine": 1.0}), ("death", 56, None, {"divine": 1.0})],
    "boss_alicorn": [("idle", None, 0.5, {"fold": 1.0}), ("stomp", 13, None, {"fold": 1.0}), ("charge", 5, None, {"fold": 1.0}),
                     ("curtain", 16, None, {"fly": 1.0}), ("nova", 214, None, {"fly": 1.0}), ("death", 44, None, {"fold": 1.0})],
    "boss_tenko": [("idle", None, 0.5, {}), ("pounce", 10, None, {}), ("tail_spikes", 22, None, {}), ("kagura", 22, None, {"eclipse": 1.0}),
                   ("eclipse", 100, None, {"eclipse": 1.0}), ("death", 50, None, {})],
    "boss_logos": [("idle", None, 0.5, {"fold": 1.0}), ("fiat", 20, None, {"fold": 1.0}), ("trumpet", 12, None, {}), ("babel", 30, None, {}),
                   ("apocalypse", 245, None, {}), ("death", 80, None, {})],
}
HIDE = {
    "boss_taotie": {"vortex": 0.001},
    "boss_alicorn": {"crown": 0.001, "horn_hue1": 0.001, "horn_hue2": 0.001, "horn_hue3": 0.001},
    "boss_hanuman": {},
    "boss_tenko": {"unseal": 0.001},
    "boss_nidhogg": {}, "boss_logos": {},
}


def main(out_dir, names):
    sheets = []
    for name in names:
        mod = importlib.import_module(name)
        m = mod.build()
        m.paint()
        loops = mod.loops()
        acts = {a.name: a.to_json() for a in mod.acts()}
        frames = []
        for act, tick, t_idle, extra in PLAN[name]:
            anims = {"idle": loops["idle"]}
            weights = {"idle": 0.15 if act != "idle" else 1.0}
            for k, w in extra.items():
                anims[k] = loops[k]
                weights[k] = w
            if act == "idle":
                t = t_idle
            else:
                anims[act] = acts[act]
                t = tick / 20.0
            env = {"v_t": t, "v_dist": t * 6.0, "life_time": t, "v_open": 1.0, "v_size": 1.0}
            pose = pose_from(anims, t, env, weights)
            hide = dict(HIDE[name])
            if name == "boss_taotie" and extra.get("form3"):
                hide = {"hull": 0.001, "neck_mesh": 0.001}
            for b, s in hide.items():
                pose.setdefault(b, {})["scale"] = s
            tmp = os.path.join(out_dir, f"_f.png")
            render_preview([m], tmp, yaw=35, pitch=12, size=300, pose=pose, step=2, title=f"{name[5:]} {act}{'' if tick is None else '@' + str(tick)}")
            frames.append(Image.open(tmp).copy())
        sheet = Image.new("RGBA", (300 * len(frames), 300))
        for i, f in enumerate(frames):
            sheet.paste(f, (300 * i, 0))
        p = os.path.join(out_dir, f"qa_{name[5:]}.png")
        sheet.save(p)
        sheets.append(p)
        print("wrote", p)
    os.remove(os.path.join(out_dir, "_f.png"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2].split(","))
