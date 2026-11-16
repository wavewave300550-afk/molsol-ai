"""Quick static preview of VESPER-0 (development helper)."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import render, vesper_model as vm

out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/vesper_preview"
os.makedirs(out, exist_ok=True)
t0 = time.time()
m, main, glow, shield = vm.build()
print("stats", m.stats(), "atlas used height", main.used_height(), "build", round(time.time() - t0, 2))
tex_p1 = main.render("p1"); tex_p2 = main.render("p2"); tex_glow = glow.render("p1")
from tex import save_png
save_png(tex_p1, f"{out}/atlas_p1.png"); save_png(tex_p2, f"{out}/atlas_p2.png"); save_png(tex_glow, f"{out}/glow.png")
views = {"front34": ((26, 10, 30), (0, 4.5, 0)), "side": ((40, 6, 0.01), (0, 4.5, 0)), "below": ((18, -8, 22), (0, 4, 0)), "top": ((0.01, 40, 6), (0, 4, 0))}
hidden_p1 = vm.LIMB_BONES + ["shield"]
for name, (eye, tgt) in views.items():
    t0 = time.time()
    sc = render.Scene(900, 600)
    sc.set_camera(eye, tgt, 40)
    sc.add_model(m, {"main": tex_p1, "glow": tex_glow}, hidden=hidden_p1, glow_tint=(1.0, 0.85, 0.5, 0.9))
    sc.image().save(f"{out}/p1_{name}.png")
    print(name, round(time.time() - t0, 2))
