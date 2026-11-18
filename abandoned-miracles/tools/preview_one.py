"""Quick look at a boss model: python3 tools/preview_one.py vesperra [out.png]"""
import importlib, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import render
key = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else f"/tmp/{key}.png"
mod = importlib.import_module(f"bosses.{key}.model")
t = time.time()
m = mod.build()
m.paint()
print(m.stats(), "extent", [list(map(lambda v: round(float(v), 1), e)) for e in m.extent()], f"{time.time()-t:.1f}s")
hidden = sys.argv[3].split(",") if len(sys.argv) > 3 else []
render.turnaround(m, key, hidden=hidden, size=(520, 560)).save(out)
m.texture.save(out.replace(".png", "_tex.png"))
print("saved", out, f"{time.time()-t:.1f}s")
