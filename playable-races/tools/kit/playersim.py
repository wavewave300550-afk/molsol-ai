"""Player state as the client exposes it to Molang, plus the player's own
skeleton animation (Mojang's player.animation.json: walk swing, arm bob, head
look, attack swing, sneak) - used by the offline animation previews and by the
build's gait ground-fitting."""
from __future__ import annotations

import math

from . import animrt, molang

FPS = 20
DT = 1.0 / FPS


class Sim:
    """Player state the way the client exposes it to Molang."""

    def __init__(self, life0: float = 300.0, jump_boost: int = 0):
        self.life = life0
        self.dist = 0.0
        self.mspeed = 0.0
        self.y = 0.0
        self.vy = 0.0
        self.ground = True
        self.sprint = False
        self.sneak = False
        self.attack_ticks = -1
        self.hurt = 0
        self.look_x = 0.0
        self.look_y = 0.0
        self.yaw_rate = 0.0
        self.jump_boost = jump_boost
        self.in_water = False
        self.swimming = False
        self.holding = False

    def tick(self, inp: dict) -> None:
        self.life += DT
        target = inp.get("move", 0.0)
        self.sprint = bool(inp.get("sprint", False)) and target > 0
        self.sneak = bool(inp.get("sneak", False))
        self.holding = bool(inp.get("holding", False))
        # limb swing amount (Java walkAnimation.update(f, 0.4)); airborne: keeps horizontal speed
        self.mspeed += (target - self.mspeed) * 0.4
        if self.mspeed < 1e-3:
            self.mspeed = 0.0
        self.dist += self.mspeed
        if inp.get("jump") and self.ground:
            self.vy = 0.42 + 0.1 * self.jump_boost
            self.ground = False
        if not self.ground:
            self.y += self.vy
            self.vy = (self.vy - 0.08) * 0.98
            if self.y <= 0:
                self.y, self.vy, self.ground = 0.0, 0.0, True
        if inp.get("attack") and self.attack_ticks < 0:
            self.attack_ticks = 0
        elif self.attack_ticks >= 0:
            self.attack_ticks += 1
            if self.attack_ticks > 6:
                self.attack_ticks = -1
        if inp.get("hurt") and self.hurt <= 0:
            self.hurt = 10
        elif self.hurt > 0:
            self.hurt -= 1
        self.look_x = inp.get("look_x", 0.0)
        self.look_y = inp.get("look_y", 0.0)
        self.yaw_rate = inp.get("yaw_rate", 0.0)

    @property
    def attack_time(self) -> float:
        return 0.0 if self.attack_ticks < 0 else min(1.0, self.attack_ticks / 6.0)

    def env(self, time_of_day: float = 0.3, first_person: bool = False) -> molang.Env:
        speed_ms = self.mspeed * 5.0
        q = {
            "life_time": self.life, "modified_distance_moved": self.dist, "modified_move_speed": self.mspeed,
            "ground_speed": speed_ms, "walk_distance": self.dist / 4.0, "is_moving": 1.0 if speed_ms > 0.05 else 0.0,
            "is_on_ground": 1.0 if self.ground else 0.0, "is_jumping": 0.0 if self.ground else 1.0,
            "vertical_speed": self.vy * 20.0, "is_sprinting": 1.0 if self.sprint else 0.0,
            "is_sneaking": 1.0 if self.sneak else 0.0, "is_swimming": 1.0 if self.swimming else 0.0,
            "is_in_water": 1.0 if self.in_water else 0.0, "is_in_water_or_rain": 1.0 if self.in_water else 0.0,
            "hurt_time": float(self.hurt), "time_of_day": time_of_day, "target_x_rotation": self.look_x,
            "target_y_rotation": self.look_y, "yaw_speed": self.yaw_rate, "delta_time": DT,
            "is_alive": 1.0, "is_riding": 0.0, "is_sleeping": 0.0, "is_gliding": 0.0, "swim_amount": 0.0,
            "head_x_rotation": lambda *a: self.look_x, "head_y_rotation": lambda *a: self.look_y,
            "body_y_rotation": 0.0, "frame_alpha": 0.0, "moon_phase": 0.0, "is_using_item": 0.0,
            "main_hand_item_use_duration": 0.0, "main_hand_item_max_duration": 0.0,
            "is_item_name_any": lambda *a: 0.0, "has_head_gear": 0.0, "is_first_person": 1.0 if first_person else 0.0,
            "has_rider": 0.0, "is_on_fire": 0.0, "is_in_lava": 0.0, "is_wall_climbing": 0.0,
            "position_delta": lambda *a: 0.0, "cardinal_facing_2d": 0.0,
            "is_item_equipped": lambda *a: 1.0 if (self.holding and (not a or a[0] == 0)) else 0.0,
        }
        return molang.Env(q=q, c={"is_first_person": 1.0 if first_person else 0.0})


def vanilla_skeleton(sim: Sim) -> animrt.Pose:
    """The player's own animations on the bound bones (Mojang player.animation.json)."""
    p = animrt.Pose()
    tcos0 = math.cos(math.radians(sim.dist * 38.17)) * sim.mspeed * 57.3
    p.add("rightleg", "rotation", [tcos0 * 1.4, 0.1, 0.1])
    p.add("leftleg", "rotation", [-tcos0 * 1.4, -0.1, -0.1])
    p.add("rightarm", "rotation", [-tcos0, 0, 0])
    p.add("leftarm", "rotation", [tcos0, 0, 0])
    bob = math.cos(math.radians(sim.life * 103.2)) * 2.865 + 2.865
    p.add("rightarm", "rotation", [0, 0, bob])
    p.add("leftarm", "rotation", [0, 0, -bob])
    p.add("head", "rotation", [sim.look_x, sim.look_y, 0])
    a = sim.attack_time
    if a > 0:
        s1 = math.sin(math.radians((1 - (1 - a) ** 4) * 180))
        p.add("body", "rotation", [0, math.sin(math.radians(360 * math.sqrt(a))) * 5.0, 0])
        p.add("rightarm", "rotation", [-(s1 * 1.2 + math.sin(math.radians(a * 180))) * 30.0,
                                       (-90.0 * s1 + 30.0) if s1 else 0.0, 0])
        p.add("leftarm", "rotation", [-(s1 * 1.2 + math.sin(math.radians(a * 180))) * 10.0, 0, 0])
    if sim.holding:
        r = p.get("rightarm", "rotation")
        p.add("rightarm", "rotation", [-r[0] * 0.5 - 18.0, 0, 0])
    if sim.sneak:
        p.add("body", "position", [0, -2, 0])
        p.add("head", "position", [0, -1, 0])
        p.add("rightarm", "rotation", [-5.7, 0, 0])
        p.add("leftarm", "rotation", [-5.7, 0, 0])
        p.add("rightleg", "rotation", [-28, 0, 0])
        p.add("leftleg", "rotation", [-28, 0, 0])
        p.add("root", "position", [0, 1.25, 9.0])
        p.add("root", "rotation", [28, 0, 0])
    p.add("root", "position", [0, sim.y * 16.0, 0])
    return p
