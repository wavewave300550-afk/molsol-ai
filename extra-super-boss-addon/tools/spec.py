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
    # ULTIMATE - Opus Magnum
    "ultimate": {"length": 9.0, "moments": {"rise": 0.2, "sigil": 1.0, "barrage": 1.6, "barrage_end": 5.4, "gather": 5.6,
                                            "slam": 7.0, "land": 7.3}},
}
ACTION_VALUES = ["none"] + list(ACTIONS)

# vanilla delayed melee (compass slash) - minecraft:behavior.delayed_attack
SLASH = {"length": 0.9, "hit_pct": 0.5}

# ------------------------------------------------------------------------------ Boss 2: Thomas Edison
SUN_BULB_ID = "esb:sun_bulb"
MARKER_ID = "esb:volt_marker"
ARC_BOLT_ID = "esb:arc_bolt"
EDISON_ID = "esb:edison"
DYNAMO_ID = "esb:dynamo"
CHAIR_ID = "esb:electric_chair"
VOLT_BULB_ID = "esb:volt_bulb"
SHIV_ID = "esb:volt_shiv"
PATENT_ID = "esb:edison_patent"

EDISON_ACTIONS = {
    "intro": {"length": 4.4, "moments": {"light": 0.5, "hop": 3.0, "land": 3.4}},
    "bulb_toss": {"length": 1.8, "moments": {"throw1": 0.5, "throw2": 0.8, "throw3": 1.1}},
    "vanish": {"length": 0.9, "moments": {"crush": 0.35, "fade": 0.5}},
    "backstab": {"length": 1.0, "moments": {"stab": 0.25}},
    "overload": {"length": 2.6, "moments": {"grab": 0.4, "pull": 1.0, "discharge": 1.4}},
    "chair": {"length": 2.2, "moments": {"snap": 0.6, "lock": 1.4}},
    "transform": {"length": 3.6, "moments": {"burst": 2.0}},
    "stunned": {"length": 3.0, "moments": {}},
    "flourish": {"length": 2.4, "moments": {"catch": 1.25}},
    "death": {"length": 4.0, "moments": {"kneel": 1.0, "fade": 3.0}},
    # ULTIMATE - Let There Be Light
    "ultimate": {"length": 10.0, "moments": {"snap": 0.3, "rise": 0.6, "bulbs": 1.0, "strikes": 1.8, "strikes_end": 6.8,
                                             "charge": 7.0, "flash": 8.5, "land": 9.2}},
}
EDISON_ACTION_VALUES = ["none"] + list(EDISON_ACTIONS)
SHANK = {"length": 0.6, "hit_pct": 0.5}
