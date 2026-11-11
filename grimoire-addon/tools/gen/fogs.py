"""Custom fog settings pushed per player with /fog during atmospheric spells (popped afterwards)."""
from .fxdefs import dump

FOGS = {
    # id: (air fog_start, fog_end, colour, render distance type)
    "grimoire:whiteout": (0.0, 9.0, "#E8F4FF", "fixed"),          # enemies inside Whiteout Dominion
    "grimoire:whiteout_caster": (0.35, 1.0, "#DCEEFF", "render"),  # caster keeps playable visibility
    "grimoire:last_winter": (0.25, 0.9, "#BFD8F2", "render"),
    "grimoire:crimson_moon": (0.12, 0.75, "#5A0610", "render"),
    "grimoire:scarlet_sea": (0.3, 0.95, "#3A0610", "render"),
    "grimoire:atmosphere": (0.4, 1.0, "#FFB060", "render"),
}


def write_fogs(rp):
    for ident, (start, end, color, rdt) in FOGS.items():
        dump(f"{rp}/fogs/{ident.split(':')[1]}.json", {
            "format_version": "1.16.100",
            "minecraft:fog_settings": {
                "description": {"identifier": ident},
                "distance": {
                    "air": {"fog_start": start, "fog_end": end, "fog_color": color, "render_distance_type": rdt},
                    "weather": {"fog_start": start * 0.8, "fog_end": end, "fog_color": color, "render_distance_type": rdt},
                },
            },
        })
