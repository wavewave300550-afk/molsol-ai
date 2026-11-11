"""Bedrock animation / animation controller builders."""


def num(v):
    if isinstance(v, (int, float)):
        return round(float(v), 4)
    return v


def vec(v):
    if isinstance(v, (list, tuple)):
        return [num(x) for x in v]
    return num(v)


class Anim:
    def __init__(self, ident, loop=False, length=None):
        self.ident = ident
        self.loop = loop
        self.length = length
        self.bones = {}
        self.timeline = {}
        self.events = {}

    def _ch(self, bone, ch, value):
        b = self.bones.setdefault(bone, {})
        if isinstance(value, dict):
            kf = {}
            for t, val in sorted(value.items(), key=lambda kv: float(kv[0])):
                key = f"{float(t):.4f}".rstrip('0').rstrip('.') if float(t) != 0 else "0.0"
                if '.' not in key:
                    key += '.0'
                if isinstance(val, dict):
                    entry = {k: vec(x) if k in ('pre', 'post') else x for k, x in val.items()}
                    kf[key] = entry
                else:
                    kf[key] = vec(val)
            b[ch] = kf
        else:
            b[ch] = vec(value)
        return self

    def rot(self, bone, value):
        return self._ch(bone, 'rotation', value)

    def pos(self, bone, value):
        return self._ch(bone, 'position', value)

    def scale(self, bone, value):
        return self._ch(bone, 'scale', value)

    def at(self, t, expr):
        self.timeline[f"{float(t):.2f}"] = expr
        return self

    def to_json(self):
        d = {}
        if self.loop:
            d['loop'] = True if self.loop is True else self.loop
        if self.length is not None:
            d['animation_length'] = round(float(self.length), 4)
        if self.timeline:
            d['timeline'] = self.timeline
        d['bones'] = self.bones
        return d


def smooth(keys):
    """Catmull-rom keyframes helper: {t: value} -> {t: {post: value, lerp_mode: catmullrom}}."""
    return {t: {'post': v, 'lerp_mode': 'catmullrom'} for t, v in keys.items()}


def anim_file(anims):
    return {"format_version": "1.10.0", "animations": {a.ident: a.to_json() for a in anims}}


def phase_controller(ident, phases, initial=0, prop="grimoire:phase", blend=0.12):
    """phases: {phase_number: [animation short names]}. Every state can reach every other."""
    states = {}
    keys = sorted(phases)
    if initial not in phases:
        phases = {initial: [], **phases}
        keys = sorted(phases)
    for k in keys:
        trans = [{f"p{o}": f"q.property('{prop}') == {o}"} for o in keys if o != k]
        st = {"transitions": trans, "blend_transition": blend}
        if phases[k]:
            st["animations"] = list(phases[k])
        states[f"p{k}"] = st
    return {"initial_state": f"p{initial}", "states": states}


def pulse_controller(anim_name, prop="grimoire:aux"):
    return {
        "initial_state": "idle",
        "states": {
            "idle": {
                "on_entry": [f"v.last_aux = q.property('{prop}');"],
                "transitions": [{"pulse": f"q.property('{prop}') != v.last_aux"}],
            },
            "pulse": {
                "animations": [anim_name],
                "on_entry": [f"v.last_aux = q.property('{prop}');"],
                "transitions": [{"idle": "q.all_animations_finished"}, {"pulse_again": f"q.property('{prop}') != v.last_aux"}],
                "blend_transition": 0.05,
            },
            "pulse_again": {
                "animations": [anim_name],
                "on_entry": [f"v.last_aux = q.property('{prop}');"],
                "transitions": [{"idle": "q.all_animations_finished"}, {"pulse": f"q.property('{prop}') != v.last_aux"}],
                "blend_transition": 0.05,
            },
        },
    }


def controller_file(ctrls):
    return {"format_version": "1.10.0", "animation_controllers": ctrls}


# Molang snippets ---------------------------------------------------------------------------
def spin(deg_per_s, t="q.life_time", offset=0):
    return f"{t} * {deg_per_s}" + (f" + {offset}" if offset else "")


def wave(amp, hz, t="q.life_time", phase=0.0, base=0.0):
    return f"{base} + math.sin({t} * {round(360 * hz, 3)} + {phase}) * {amp}"


def ease_in(t_len, t="q.anim_time"):
    return f"math.clamp({t} / {t_len}, 0, 1)"
