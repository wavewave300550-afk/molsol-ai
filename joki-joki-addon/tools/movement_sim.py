"""
Movement tuning for Pressure Dash, Boiler Jump and Jet Kick.

Integrates vanilla player physics after one script impulse (Entity.applyKnockback):
  gravity 0.08 b/t^2, vertical drag 0.98, horizontal drag 0.91 in air and 0.91*0.6 on ground.
Player input (sprint/air control) is ignored, so real distances are a little longer when
holding forward. Values must match TUNING in src/config.ts (checked by the smoke test).

    python3 tools/movement_sim.py
"""
import json
import math


def simulate(h, vy, start_air=0.0, ticks=80):
    x, y, vx = 0.0, start_air, h
    on_ground = start_air <= 0 and vy <= 0
    peak = y
    for t in range(ticks):
        x += vx
        y += vy
        if y <= 0:
            y, vy, on_ground = 0.0, 0.0, True
        else:
            on_ground = False
        peak = max(peak, y)
        vx *= 0.546 if on_ground else 0.91
        if not on_ground:
            vy = (vy - 0.08) * 0.98
        if on_ground and abs(vx) < 0.003:
            return {"distance": round(x, 2), "peak": round(peak, 2), "ticks": t + 1}
    return {"distance": round(x, 2), "peak": round(peak, 2), "ticks": ticks}


POWER = {"HEAT": 1.15, "PRESSURE": 1.4, "REDLINE": 1.75}
DASH = {"speed": 0.92, "lift": 0.3, "airLift": 0.12}
JUMP = {"lift": 1.0}
KICK = {"speed": 0.68, "lift": 0.18}

if __name__ == "__main__":
    out = {}
    for mode, power in POWER.items():
        pf = math.sqrt(power)
        out[mode] = {
            "dash_ground": simulate(DASH["speed"] * pf, DASH["lift"]),
            "dash_air": simulate(DASH["speed"] * pf, DASH["airLift"], start_air=2.0),
            "jump": simulate(0.0, JUMP["lift"] * pf),
            "kick": simulate(KICK["speed"] * pf, KICK["lift"]),
        }
    out["vanilla_jump"] = simulate(0.0, 0.42)
    print(json.dumps(out, indent=1))
