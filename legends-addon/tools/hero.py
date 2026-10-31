"""Large hero render(s): python3 tools/hero.py <out.png> <creature> [prop=val ...] [@act:t] [yaw,pitch ...] [v1]"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from creatures import registry  # noqa: E402
from mk.render import render_views  # noqa: E402
from preview import pose_for  # noqa: E402

out, name, *rest = sys.argv[1:]
props, act, t, views, variant = {"legends:phase": 1}, None, 0.0, [], 0
for r in rest:
    if r.startswith("@"):
        act, t = r[1:].split(":")
        t = float(t)
    elif "=" in r:
        k, v = r.split("=")
        props[k if ":" in k else "legends:" + k] = float(v)
    elif r == "v1":
        variant = 1
    else:
        y, p = r.split(",")
        views.append((float(y), float(p)))
views = views or [(-35, 14), (140, 18)]
c = registry.ALL[name]()
c.model.paint()
if variant:
    c.model.texture = c.model.paint(variant=1)
pose, vis = pose_for(c, act, t, props)
render_views([(c.model, pose, vis)], views, size=640, bg=(24, 26, 36)).save(out)
