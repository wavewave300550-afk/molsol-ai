"""Pose preview: python3 tools/preview_anim.py <boss> <out.png> <phase> <anim[+anim..]@t,t,t> ...
Renders each requested animation time with the always-on base layer applied."""
import importlib, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import render
from kit.anim import combine

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
key, out, phase = sys.argv[1], sys.argv[2], int(sys.argv[3])
model = importlib.import_module(f"bosses.{key}.model").build()
model.paint()
A = importlib.import_module(f"bosses.{key}.anims")
T = json.load(open(os.path.join(ROOT, "shared", f"{key}.timings.json")))
anims, ctrls, ce = A.build_all(T)
by = {a.name.split(".")[-1]: a for a in anims}
hidden = [h for h in os.environ.get("HIDE", "").split(",") if h]
yaw = float(os.environ.get("YAW", "35"))
pitch = float(os.environ.get("PITCH", "14"))
dist = float(os.environ.get("DIST", "0"))
base_names = os.environ.get("BASE", "idle,walk,turn" + (",p2_pose,p2_flutter" if phase == 2 else "")).split(",")
bounds = model.extent()
bounds = (bounds[0] - 24, bounds[1] + 24)
ims = []
for spec in sys.argv[4:]:
    names, times = spec.split("@")
    for t in [float(x) for x in times.split(",")]:
        env = ce.env({"q.life_time": 1.3 + t, "q.anim_time": t, "q.modified_distance_moved": 4 * (dist + t * float(os.environ.get("SPEED", "0"))),
                      "q.modified_move_speed": 1.0 if float(os.environ.get("SPEED", "0")) > 0 else 0.0,
                      "q.body_y_rotation": float(os.environ.get("BODYYAW", "0")) + t * float(os.environ.get("TURN", "0")),
                      "p.abm:phase": phase, "p.abm:variant": float(os.environ.get("VARIANT", "0"))})
        poses = [by[n].sample(1.3 + t, env) for n in base_names if n and n in by]
        poses += [by[n].sample(t, env) for n in names.split("+") if n and n != "none"]
        pose = combine(*poses)
        ims.append(render.label(render.render(model, pose, yaw=yaw, pitch=pitch, size=(430, 430), bounds=bounds,
                                              hidden=hidden, scale_figure=False), f"{names} t={t:.2f}s"))
cols = int(os.environ.get("COLS", "5"))
render.sheet(ims, min(cols, len(ims))).save(out)
print("saved", out, len(ims))
