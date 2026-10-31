"""Close-up render of one bone subtree: python3 tools/closeup.py <creature> <bone> <out.png> [phase]"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from creatures import registry  # noqa: E402
from creatures.common import descendants  # noqa: E402
from mk.render import render_views  # noqa: E402
from preview import pose_for  # noqa: E402

name, bone, out = sys.argv[1:4]
phase = int(sys.argv[4]) if len(sys.argv) > 4 else 1
c = registry.ALL[name]()
c.model.paint()
keep = set(descendants(c.model, bone))
pose, vis = pose_for(c, props={"legends:phase": phase})
img = render_views([(c.model, pose, vis, keep)], [(0, 5), (-40, 12), (90, 5), (180, 10)], size=340,
                   labels=["front", "3/4", "left", "back"])
img.save(out)
