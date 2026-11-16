"""
Posing helpers: build rotations from target directions, decompose them into
Bedrock (file-convention) Euler angles, and solve simple arm IK.

Bedrock: display rotation M = Rz(z) * Ry(-y) * Rx(-x) for file Euler (x, y, z).
"""
from __future__ import annotations

import math
from typing import Sequence, Tuple

import numpy as np

from .bedrock import euler_file_to_matrix


def basis_from(y_dir, z_dir) -> np.ndarray:
    """3x3 rotation whose columns are images of the model x, y, z axes (display space).
    y_dir: where model +y must point; z_dir: approximate direction for model +z."""
    y = np.array(y_dir, float)
    y /= np.linalg.norm(y)
    z = np.array(z_dir, float)
    z = z - y * np.dot(z, y)
    z /= np.linalg.norm(z)
    x = np.cross(y, z)
    return np.column_stack([x, y, z])


def euler_zyx_from_matrix(R: np.ndarray) -> Tuple[float, float, float]:
    """Display Euler (ax, ay, az) with R = Rz(az) Ry(ay) Rx(ax)."""
    sy = -R[2, 0]
    sy = max(-1.0, min(1.0, sy))
    ay = math.asin(sy)
    if abs(math.cos(ay)) > 1e-6:
        ax = math.atan2(R[2, 1], R[2, 2])
        az = math.atan2(R[1, 0], R[0, 0])
    else:
        ax = math.atan2(-R[1, 2], R[1, 1])
        az = 0.0
    return math.degrees(ax), math.degrees(ay), math.degrees(az)


def file_euler_from_matrix(R: np.ndarray) -> Tuple[float, float, float]:
    ax, ay, az = euler_zyx_from_matrix(R)
    return (-ax, -ay, az)


def check_file_euler(e, R, tol=1e-6) -> bool:
    return np.allclose(euler_file_to_matrix(e)[:3, :3], R, atol=tol)


def disp_dir(v) -> np.ndarray:
    """file-space direction -> display-space direction"""
    return np.array([-v[0], v[1], v[2]], float)


def file_dir(v) -> np.ndarray:
    return np.array([-v[0], v[1], v[2]], float)


# ----------------------------------------------------------------------------- stiff-arm IK
# Display-space body frame (body bone unrotated): player's right side is +x, front is -z.
SHOULDER = {"right": np.array([5.0, 22.0, 0.0]), "left": np.array([-5.0, 22.0, 0.0])}
ITEM_OFF = {"right": np.array([1.0, -7.0, 1.0]), "left": np.array([-1.0, -7.0, 1.0])}   # item pivot - shoulder
ARM_LEN = float(np.linalg.norm(ITEM_OFF["right"]))
FIST_FWD = np.array([0.0, 0.0, -1.0])      # direction a held item points, arm at rest
R_TP = None                                 # attachable third-person grip rotation (set below)


def unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def axis_angle(axis, ang_rad) -> np.ndarray:
    a = unit(axis)
    x, y, z = a
    c, s = math.cos(ang_rad), math.sin(ang_rad)
    C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])


def rot_align(a, b) -> np.ndarray:
    a, b = unit(a), unit(b)
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if np.linalg.norm(v) < 1e-9:
        if c > 0:
            return np.eye(3)
        perp = unit(np.cross(a, [1, 0, 0] if abs(a[0]) < 0.9 else [0, 1, 0]))
        return axis_angle(perp, math.pi)
    return axis_angle(v, math.atan2(np.linalg.norm(v), c))


def solve_arm(side: str, hand, fwd_hint):
    """Rotation R (display) + position offset p (display) so the arm's item pivot reaches `hand`,
    twisting the arm so the fist's forward axis points as close as possible to fwd_hint."""
    S, o = SHOULDER[side], ITEM_OFF[side]
    v = np.asarray(hand, float) - S
    a = unit(v)
    R0 = rot_align(o, v)
    f = R0 @ FIST_FWD
    fp = f - a * np.dot(a, f)
    gp = np.asarray(fwd_hint, float) - a * np.dot(a, fwd_hint)
    if np.linalg.norm(fp) > 1e-6 and np.linalg.norm(gp) > 1e-6:
        fp, gp = unit(fp), unit(gp)
        phi = math.atan2(float(np.dot(a, np.cross(fp, gp))), float(np.dot(fp, gp)))
        R0 = axis_angle(a, phi) @ R0
    p = v - R0 @ o
    return R0, p


def sword_basis(blade_dir, edge_dir) -> np.ndarray:
    """World orientation of the sword model: model +y -> blade_dir, model -z (true edge) -> edge_dir."""
    return basis_from(blade_dir, -np.asarray(edge_dir, float))


def wrist_for(R_arm, blade_dir, edge_dir, r_tp) -> np.ndarray:
    return R_arm.T @ sword_basis(blade_dir, edge_dir) @ r_tp.T


def two_hand_center(c_hint, blade_dir, spacing, lam=0.25, iters=400):
    """Grip centre close to c_hint such that both hands (spaced along the grip) are within arm reach."""
    g = unit(blade_dir)
    C = np.array(c_hint, float)
    for _ in range(iters):
        hR = C + g * spacing / 2
        hL = C - g * spacing / 2
        rR = (np.linalg.norm(hR - SHOULDER["right"]) - ARM_LEN) * unit(hR - SHOULDER["right"])
        rL = (np.linalg.norm(hL - SHOULDER["left"]) - ARM_LEN) * unit(hL - SHOULDER["left"])
        C = C - 0.25 * (rR + rL + lam * (C - np.asarray(c_hint, float)))
    return C


def aim_arm(direction_disp: Sequence[float], roll: float = 0.0) -> Tuple[float, float, float]:
    """File Euler for an arm (rest pointing -y) so that it points along direction (display space).
    roll rotates about the arm's own axis (degrees)."""
    d = np.array(direction_disp, float)
    d /= np.linalg.norm(d)
    # arm axis is -y in rest pose: we need R * (0,-1,0) = d  ->  R * (0,1,0) = -d
    up_hint = np.array([0.0, 0.0, -1.0])   # rest arm front (-z) stays roughly forward
    if abs(np.dot(up_hint, -d)) > 0.95:
        up_hint = np.array([0.0, 1.0, 0.0])
    B = basis_from(-d, -up_hint)            # model +z ~ backward
    if roll:
        a = math.radians(roll)
        c, s = math.cos(a), math.sin(a)
        Rr = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])   # about local y
        B = B @ Rr
    return file_euler_from_matrix(B)


# ----------------------------------------------------------------------------- quaternions

def mat_to_quat(R) -> np.ndarray:
    R = np.asarray(R, float)
    tr = R[0, 0] + R[1, 1] + R[2, 2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        q = [0.25 * s, (R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s]
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        q = [(R[2, 1] - R[1, 2]) / s, 0.25 * s, (R[0, 1] + R[1, 0]) / s, (R[0, 2] + R[2, 0]) / s]
    elif R[1, 1] > R[2, 2]:
        s = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        q = [(R[0, 2] - R[2, 0]) / s, (R[0, 1] + R[1, 0]) / s, 0.25 * s, (R[1, 2] + R[2, 1]) / s]
    else:
        s = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        q = [(R[1, 0] - R[0, 1]) / s, (R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s, 0.25 * s]
    q = np.array(q)
    return q / np.linalg.norm(q)


def quat_to_mat(q) -> np.ndarray:
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def slerp(qa, qb, f) -> np.ndarray:
    qa, qb = np.asarray(qa, float), np.asarray(qb, float)
    d = float(np.dot(qa, qb))
    if d < 0:
        qb, d = -qb, -d
    if d > 0.9995:
        q = qa + (qb - qa) * f
        return q / np.linalg.norm(q)
    th = math.acos(d)
    return (math.sin((1 - f) * th) * qa + math.sin(f * th) * qb) / math.sin(th)
