"""Render multi-angle previews + run geometry QA for every boss model.
    python3 tools/preview.py <out_dir> [boss ...]"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from modelkit import deflicker, island_report, render_preview, zfight_report  # noqa: E402
import registry  # noqa: E402

VIEWS = (("front", 0, 8), ("front34", 35, 18), ("side", 90, 6), ("back34", 215, 22), ("back", 180, 10), ("top", 20, 62))


def main(out, names):
    os.makedirs(out, exist_ok=True)
    for name in names or registry.MODELS:
        t0 = time.time()
        m = registry.MODELS[name]()
        fixed_left = deflicker(m)
        m.paint()
        for tag, yaw, pitch in VIEWS:
            render_preview([m], os.path.join(out, f"{name}_{tag}.png"), yaw=yaw, pitch=pitch, size=560, title=f"{name} - {tag}", step=int(os.environ.get("PREVIEW_STEP", "2")))
        z = zfight_report(m)
        isl = island_report(m)
        print(name, m.stats(), f"zfight={len(z)} islands={len(isl)} ({time.time() - t0:.1f}s)")
        for line in (z + isl)[:12]:
            print("   ", line)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "previews", sys.argv[2:])
