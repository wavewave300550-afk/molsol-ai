"""
Shared timing spec: the animation generator builds each action to these lengths and moments, and
gen_entity.py writes the same numbers to scripts-src/spec.ts so the server deals damage on the
exact frame the client shows the hit.  Times are seconds.
"""

NAMESPACE = "esb"
BOSS_ID = "esb:da_vinci"
GEAR_ID = "esb:brass_gear"
SIGIL_ID = "esb:vitruvian_sigil"
BLUEPRINT_ID = "esb:da_vinci_blueprint"
CODEX_ID = "esb:leonardo_codex"

# action -> length and named moments (seconds from the start of the action)
ACTIONS = {
    "intro": {"length": 4.0, "moments": {"burst": 0.25, "rise": 1.1, "flex": 2.6}},
    "gear_volley": {"length": 2.8, "moments": {"shot1": 1.0, "shot2": 1.45, "shot3": 1.9}},
    "quake": {"length": 1.9, "moments": {"impact": 0.95}},
    "vitruvian": {"length": 3.6, "moments": {"sigil": 0.35, "detonate": 2.75}},
    "transform": {"length": 3.6, "moments": {"burst": 2.2}},
    "dive_rise": {"length": 0.9, "moments": {"leap": 0.35}},
    "dive_hover": {"length": 1.0, "moments": {}},  # looping; the script decides how long it hovers
    "dive_strike": {"length": 1.4, "moments": {"impact": 0.3}},
    "flourish": {"length": 2.6, "moments": {}},
    "death": {"length": 4.2, "moments": {"kneel": 1.0, "pages": 3.4}},
}
ACTION_VALUES = ["none"] + list(ACTIONS)

# vanilla delayed melee (compass slash) - minecraft:behavior.delayed_attack
SLASH = {"length": 0.9, "hit_pct": 0.5}
