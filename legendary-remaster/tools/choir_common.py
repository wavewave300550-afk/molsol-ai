"""Shared bits for the Choir (Seraph, Cherub, Ophan): entity config helper and death/spawn acts."""
from animkit import A, Act


def spawn_act(ticks=40, mark=24):
    a = Act("spawn", ticks, [mark])
    a.at(0, {"root": {"s": 0.1, "p": (0, 10, 0)}})
    a.at(mark, {"root": {"s": 1.12, "p": (0, 0, 0)}}, "out")
    a.at(ticks, {"root": {"s": 1.0}})
    return a


def death_act(ticks=40, mark=32, extra=None):
    a = Act("death", ticks, [mark])
    a.at(mark - 14, dict(extra or {}), "io")
    a.at(mark, {"root": {"s": 1.15}}, "out")
    a.at(ticks, {"root": {"s": 0.02, "p": (0, 14, 0)}}, "in")
    return a.overlay("root", "p", [f"math.sin({A} * 2600) * 0.5", 0, 0])


def cfg(key, scale, animate_extra=None, visibility=None, bounds=(5, 6, 2.0)):
    return {
        "scale": scale,
        "textures": {"default": f"textures/entity/legends/{key}"},
        "pre": [],
        "animate": [{"idle": "variable.calm + 0.2"}, *(animate_extra or []), "ctrl_act"],
        "visibility": visibility or [],
        "bounds": bounds,
    }
