"""
client_sim.py - emulates the client side of an entity for previews.

Runs `initialize` / `pre_animation` molang, steps animation controllers (first matching
transition wins, `blend_transition` cross-fades the previous state's pose into the new
one) and merges every active animation additively like Bedrock does.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import molang
from anim import Anim, Controller, merge_poses


class _CtrlRuntime:
    def __init__(self, ctrl: Controller):
        self.ctrl = ctrl
        self.state = ctrl.initial
        self.time = 0.0
        self.prev_state: Optional[str] = None
        self.prev_time = 0.0
        self.blend_left = 0.0
        self.blend_total = 0.0


class ClientSim:
    def __init__(self, animations: Dict[str, Anim], controllers: Dict[str, Controller], animate: List[str],
                 pre_animation: List[str], initialize: List[str]):
        self.animations = animations
        self.controllers = {k: _CtrlRuntime(c) for k, c in controllers.items()}
        self.animate = animate
        self.pre = pre_animation
        self.variables: Dict[str, float] = {}
        self.t = 0.0
        self.anim_times = {k: 0.0 for k in animate}
        self.ctx = molang.Context(variables=self.variables)
        self._init = initialize
        self._initialized = False
        self.transitions_log: List[tuple] = []

    def _state_pose(self, rt: _CtrlRuntime, state: str, t: float) -> dict:
        st = rt.ctrl.states.get(state, {})
        poses = []
        weights = []
        for a in st.get("animations", []):
            if isinstance(a, dict):
                (name, w), = a.items()
                wv = molang.evaluate(w, self.ctx)
            else:
                name, wv = a, 1.0
            poses.append(self.animations[name].evaluate(t, self.ctx))
            weights.append(wv)
        return merge_poses(*poses, weights=weights) if poses else {}

    def step(self, dt: float, properties: Dict[str, object], queries: Optional[Dict[str, float]] = None) -> dict:
        self.ctx.properties = properties
        q = {"query.life_time": self.t, "query.delta_time": dt, "query.body_y_rotation": 0.0,
             "query.ground_speed": 0.0, "query.hurt_time": 0.0, "query.anim_time": 0.0}
        q.update(queries or {})
        self.ctx.queries = q
        if not self._initialized:
            for s in self._init:
                molang.evaluate(s, self.ctx)
            self._initialized = True
        for s in self.pre:
            molang.evaluate(s, self.ctx)
        poses = []
        for key in self.animate:
            if key in self.controllers:
                rt = self.controllers[key]
                st = rt.ctrl.states[rt.state]
                for tr in st.get("transitions", []):
                    (to, cond), = tr.items()
                    if molang.evaluate(cond, self.ctx):
                        self.transitions_log.append((round(self.t, 2), key, rt.state, to))
                        rt.prev_state, rt.prev_time = rt.state, rt.time
                        rt.blend_total = rt.blend_left = float(st.get("blend_transition", 0.0))
                        rt.state, rt.time = to, 0.0
                        break
                pose = self._state_pose(rt, rt.state, rt.time)
                if rt.blend_left > 0 and rt.prev_state is not None:
                    w = 1.0 - rt.blend_left / rt.blend_total
                    prev = self._state_pose(rt, rt.prev_state, rt.prev_time)
                    pose = _lerp_pose(prev, pose, w)
                    rt.blend_left -= dt
                    rt.prev_time += dt
                rt.time += dt
                poses.append(pose)
            else:
                anim = self.animations[key]
                poses.append(anim.evaluate(self.anim_times[key], self.ctx))
                self.anim_times[key] += dt
        self.t += dt
        return merge_poses(*poses)


def _lerp_pose(a: dict, b: dict, w: float) -> dict:
    out = {}
    for bone in set(a) | set(b):
        pa, pb = a.get(bone, {}), b.get(bone, {})
        ob = {}
        for kind in set(pa) | set(pb):
            default = (1.0, 1.0, 1.0) if kind == "scale" else (0.0, 0.0, 0.0)
            va, vb = pa.get(kind, default), pb.get(kind, default)
            ob[kind] = tuple(va[i] + (vb[i] - va[i]) * w for i in range(3))
        out[bone] = ob
    return out
