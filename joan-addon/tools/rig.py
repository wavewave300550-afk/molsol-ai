"""
Rigging helpers on top of modelkit's forward kinematics:

  * banner solver  - give the war banner a WORLD orientation (pole axis + the
                     side the cloth flies to) and get the local bone rotation
  * arm IK         - put a hand on a world point (e.g. the left hand on the pole)
  * chain physics  - Verlet cloth/cape chains driven by the animated skeleton,
                     baked into per-frame bone rotations (secondary motion that
                     really follows the banner's swings, with weight and lag)
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

from modelkit import (IDENT, Mat, Model, Vec, bedrock_euler_from_matrix, bedrock_rot, bone_transforms, m_apply,
                      m_mul, m_transpose, v_add, v_cross, v_dot, v_len, v_mul, v_norm, v_sub)

Pose = Dict[str, dict]


def copy_pose(p: Pose) -> Pose:
    return {k: {kk: tuple(vv) if isinstance(vv, (list, tuple)) else vv for kk, vv in v.items()} for k, v in p.items()}


def rot_of(p: Pose, bone: str) -> Tuple[float, float, float]:
    return tuple(p.get(bone, {}).get("rotation", (0.0, 0.0, 0.0)))  # type: ignore


def set_rot(p: Pose, bone: str, r: Sequence[float]):
    p.setdefault(bone, {})["rotation"] = (float(r[0]), float(r[1]), float(r[2]))


def frame_from_dirs(y_axis: Vec, z_axis: Vec) -> Mat:
    """Rotation whose local +Y maps to y_axis and local +Z (orthogonalised) to z_axis."""
    y = v_norm(y_axis)
    z = v_sub(z_axis, v_mul(y, v_dot(z_axis, y)))
    if v_len(z) < 1e-6:
        z = v_sub((0, 0, 1), v_mul(y, y[2]))
        if v_len(z) < 1e-6:
            z = (1, 0, 0)
    z = v_norm(z)
    x = v_cross(y, z)
    return ((x[0], y[0], z[0]), (x[1], y[1], z[1]), (x[2], y[2], z[2]))


class Rig:
    def __init__(self, model: Model):
        self.m = model
        self.bones = {b.name: b for b in model.bones}
        self.children: Dict[str, List[str]] = {}
        for b in model.bones:
            if b.parent:
                self.children.setdefault(b.parent, []).append(b.name)

    def fk(self, pose: Pose):
        return bone_transforms(self.m, pose)

    def world_R(self, pose: Pose, bone: str) -> Mat:
        return self.fk(pose)[bone].R

    def point(self, pose: Pose, bone: str, p: Vec) -> Vec:
        return self.fk(pose)[bone].apply(p)

    # ------------------------------------------------------------------ banner
    def solve_banner(self, pose: Pose, pole_dir: Vec, cloth_dir: Vec, bone: str = "banner") -> Pose:
        """Set pose[bone] rotation so the banner's +Y = pole_dir and +Z ~ cloth_dir (model space)."""
        parent = self.bones[bone].parent
        p2 = dict(pose)
        p2.pop(bone, None)
        Rp = self.fk(p2)[parent].R if parent else IDENT
        W = frame_from_dirs(pole_dir, cloth_dir)
        local = m_mul(m_transpose(Rp), W)
        e = bedrock_euler_from_matrix(local)
        set_rot(pose, bone, e)
        return pose

    def grip_point(self, pose: Pose) -> Vec:
        return self.point(pose, "banner", (-5.9, 10.9, 0.0))

    def pole_point(self, pose: Pose, along: float) -> Vec:
        """World point on the pole `along` units above the right-hand grip."""
        return self.point(pose, "banner", (-5.9, 10.9 + along, 0.0))

    # ------------------------------------------------------------------ arm IK (numeric, 4 DOF)
    def solve_arm(self, pose: Pose, side: str, target: Vec, iters: int = 60) -> Pose:
        arm, fore = f"arm_{side}", f"forearm_{side}"
        loc = (5.9 if side == "l" else -5.9, 10.5, -0.5)
        hand = f"hand_{side}"
        x = list(rot_of(pose, arm)) + [rot_of(pose, fore)[0]]

        def apply(v):
            set_rot(pose, arm, (v[0], v[1], v[2]))
            fr = rot_of(pose, fore)
            set_rot(pose, fore, (v[3], fr[1], fr[2]))

        def cost(v):
            apply(v)
            d = v_sub(self.point(pose, hand, loc), target)
            reg = 0.0004 * (v[1] ** 2 + v[2] ** 2) + 0.0002 * max(0, v[3]) ** 2
            return v_dot(d, d) + reg
        best = cost(x)
        step = 24.0
        for _ in range(iters):
            improved = False
            for i in range(4):
                for sgn in (1, -1):
                    y = list(x)
                    y[i] += sgn * step
                    if i == 3:
                        y[3] = max(-150.0, min(0.0, y[3]))    # elbow only bends one way
                    c = cost(y)
                    if c < best:
                        best, x, improved = c, y, True
            if not improved:
                step *= 0.5
                if step < 0.05:
                    break
        apply(x)
        return pose


# =========================================================================== chain physics

class Chain:
    """
    A chain of bones simulated as Verlet points.

    bones      : bone names, parent-first (each a child of the previous)
    rest_dir   : direction of a segment in its parent's local frame at rest
    seg_len    : segment length (units)
    hinge_axis : for the first segment, the parent-local axis it must stay
                 perpendicular to (pole axis for the banner) - None = free
    """

    def __init__(self, rig: Rig, bones: List[str], rest_dir: Vec, seg_len: float, tip_len: Optional[float] = None,
                 hinge_axis: Optional[Vec] = None, gravity: float = 60.0, drag: float = 6.0, stiffness: float = 0.2,
                 flutter: float = 0.0, limits: Tuple[float, float] = (70.0, 50.0), angle_mode: str = "yaw_pitch"):
        self.rig = rig
        self.bones = bones
        self.rest = v_norm(rest_dir)
        self.L = seg_len
        self.tipL = tip_len or seg_len
        self.hinge = hinge_axis
        self.g = gravity
        self.k = drag
        self.stiff = stiffness
        self.flutter = flutter
        self.limits = limits
        self.mode = angle_mode

    def _anchor_frame(self, pose: Pose):
        b0 = self.rig.bones[self.bones[0]]
        parent = b0.parent
        xfs = self.rig.fk(pose)
        pxf = xfs[parent]
        return pxf.apply(b0.pivot), pxf.R

    def simulate(self, poses: List[Pose], dt: float, root_vel: Sequence[Vec], breeze: Vec = (0, 0, 0),
                 gust: float = 0.0, loops: int = 1, phase: float = 0.0) -> List[Pose]:
        """Return a list of per-frame {bone: rotation} for the chain."""
        n = len(self.bones)
        frames = len(poses)
        out: List[Pose] = [dict() for _ in range(frames)]
        anchor, R = self._anchor_frame(poses[0])
        d0 = m_apply(R, self.rest)
        pts = [v_add(anchor, v_mul(d0, self.L * i)) for i in range(n + 1)]
        prev = [p for p in pts]
        sub = 6
        h = dt / sub
        total = frames * loops
        t_global = 0.0
        for step in range(total):
            fi = step % frames
            pose = poses[fi]
            anchor, R = self._anchor_frame(pose)
            vel = root_vel[fi] if len(root_vel) > 1 else root_vel[0]
            for s in range(sub):
                t_global += h
                wind = v_sub(breeze, vel)
                gw = 1.0 + gust * (math.sin(t_global * 2.3 + phase) * 0.6 + math.sin(t_global * 5.1 + 1.3) * 0.4)
                wind = v_mul(wind, gw)
                pts[0] = anchor
                for i in range(1, n + 1):
                    p, q = pts[i], prev[i]
                    v = v_mul(v_sub(p, q), 1.0 / h)
                    acc = (0.0, -self.g, 0.0)
                    acc = v_add(acc, v_mul(v_sub(wind, v), self.k))
                    if self.flutter:
                        seg = v_norm(v_sub(pts[i], pts[i - 1]))
                        axis = m_apply(R, self.hinge) if self.hinge else (0.0, 1.0, 0.0)
                        nrm = v_norm(v_cross(axis, seg))
                        ws = v_len(wind)
                        amp = self.flutter * min(1.0, ws / 60.0) * (0.3 + 0.7 * i / n)
                        acc = v_add(acc, v_mul(nrm, amp * math.sin(t_global * (9.0 + ws * 0.04) - i * 1.1 + phase)))
                    nxt = v_add(p, v_add(v_mul(v_sub(p, q), 0.995), v_mul(acc, h * h)))
                    prev[i] = p
                    pts[i] = nxt
                # constraints
                for _ in range(4):
                    pts[0] = anchor
                    for i in range(n):
                        a, b = pts[i], pts[i + 1]
                        d = v_sub(b, a)
                        ln = v_len(d) or 1e-6
                        L = self.L if i < n - 1 else self.tipL
                        corr = v_mul(d, (ln - L) / ln)
                        if i == 0:
                            pts[i + 1] = v_sub(b, corr)
                        else:
                            pts[i] = v_add(a, v_mul(corr, 0.5))
                            pts[i + 1] = v_sub(b, v_mul(corr, 0.5))
                    if self.hinge is not None:
                        axis = v_norm(m_apply(R, self.hinge))
                        d = v_sub(pts[1], pts[0])
                        along = v_dot(d, axis)
                        # cloth hangs off the staff: allow only a little sag along the pole
                        lim = math.sin(math.radians(12)) * v_len(d)
                        along_c = max(-lim, min(lim * 0.3, along))
                        d = v_add(v_sub(d, v_mul(axis, along)), v_mul(axis, along_c))
                        pts[1] = v_add(pts[0], v_mul(v_norm(d), self.L))
                    # bending stiffness
                    for i in range(1, n):
                        a, b, c = pts[i - 1], pts[i], pts[i + 1]
                        want = v_add(b, v_mul(v_norm(v_sub(b, a)), self.L if i < n - 1 else self.tipL))
                        pts[i + 1] = v_add(c, v_mul(v_sub(want, c), self.stiff))
            if step >= total - frames:
                out[fi] = self._angles(pose, pts)
        return out

    def _angles(self, pose: Pose, pts: List[Vec]) -> Pose:
        res: Pose = {}
        b0 = self.rig.bones[self.bones[0]]
        Rparent = self.rig.fk(pose)[b0.parent].R
        max_yaw, max_pitch = self.limits
        for i, name in enumerate(self.bones):
            d_world = v_norm(v_sub(pts[i + 1], pts[i]))
            d = m_apply(m_transpose(Rparent), d_world)
            if self.mode == "yaw_pitch":
                # rest along +Z: rotation = Ry(yaw) Rx(-pitch)  ->  d = (cos p sin y, sin p, cos p cos y)
                pitch = math.degrees(math.asin(max(-1.0, min(1.0, d[1]))))
                yaw = math.degrees(math.atan2(d[0], d[2]))
                lim_y = max_yaw if i else max_yaw * 1.6
                yaw = max(-lim_y, min(lim_y, yaw))
                pitch = max(-max_pitch, min(max_pitch, pitch))
                rot = (pitch, yaw, 0.0)
            else:
                # hanging chain, rest along -Y: rotation about X (swing fwd/back) and Z (sideways)
                # Rz(-rz) Rx(-rx) (0,-1,0) = ...  solve small-angle style
                rx = math.degrees(math.atan2(d[2], -d[1]))       # +rx swings the tip backwards (+Z)
                rz = math.degrees(math.atan2(-d[0], -d[1]))
                rx = max(-max_pitch, min(max_yaw, rx))
                rz = max(-35.0, min(35.0, rz))
                rot = (rx, 0.0, rz)
            res[name] = {"rotation": rot}
            Rparent = m_mul(Rparent, bedrock_rot(rot))
        return res
