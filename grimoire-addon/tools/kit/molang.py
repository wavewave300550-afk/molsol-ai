"""Tiny Molang evaluator for build-time checks (numbers, variables, math.*, ternaries, logic).

    ev = Molang({"c.is_first_person": 1.0, "v.open": 0.0})
    ev("c.is_first_person ? -2.0 : 9.5")      # -> -2.0
Unknown names evaluate to 0, unknown functions to 0.
"""
from __future__ import annotations

import math
import re

_TOK = re.compile(r"\s*(\d+\.\d*|\.\d+|\d+|[A-Za-z_][\w.]*|\?\?|&&|\|\||[<>=!]=|[-+*/()?:,<>!])")


class _Undef(float):
    """Value of a name the environment does not define (so `??` can fall back)."""


class Molang:
    def __init__(self, env):
        self.env = env

    def __call__(self, expr):
        if isinstance(expr, (int, float)):
            return float(expr)
        self.t = [m for m in _TOK.findall(expr)]
        self.i = 0
        v = self.ternary()
        return float(v)

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def eat(self, tok=None):
        v = self.t[self.i]
        if tok is not None and v != tok:
            raise ValueError(f"expected {tok}, got {v}")
        self.i += 1
        return v

    def ternary(self):
        c = self.coalesce()
        if self.peek() == "?":
            self.eat("?")
            a = self.ternary()
            self.eat(":")
            b = self.ternary()
            return a if c else b
        return c

    def coalesce(self):
        v = self.orr()
        while self.peek() == "??":
            self.eat()
            w = self.orr()
            v = w if isinstance(v, _Undef) else v
        return v

    def orr(self):
        v = self.andd()
        while self.peek() == "||":
            self.eat()
            w = self.andd()
            v = 1.0 if (v or w) else 0.0
        return v

    def andd(self):
        v = self.cmp()
        while self.peek() == "&&":
            self.eat()
            w = self.cmp()
            v = 1.0 if (v and w) else 0.0
        return v

    def cmp(self):
        v = self.add()
        while self.peek() in ("<", ">", "<=", ">=", "==", "!="):
            op = self.eat()
            w = self.add()
            v = float({"<": v < w, ">": v > w, "<=": v <= w, ">=": v >= w, "==": v == w, "!=": v != w}[op])
        return v

    def add(self):
        v = self.mul()
        while self.peek() in ("+", "-"):
            op = self.eat()
            w = self.mul()
            v = v + w if op == "+" else v - w
        return v

    def mul(self):
        v = self.unary()
        while self.peek() in ("*", "/"):
            op = self.eat()
            w = self.unary()
            v = v * w if op == "*" else (v / w if w else 0.0)
        return v

    def unary(self):
        if self.peek() == "-":
            self.eat()
            return -self.unary()
        if self.peek() == "!":
            self.eat()
            return 0.0 if self.unary() else 1.0
        return self.primary()

    def primary(self):
        tok = self.eat()
        if tok == "(":
            v = self.ternary()
            self.eat(")")
            return v
        if re.match(r"[\d.]", tok):
            return float(tok)
        name = tok.lower()
        if self.peek() == "(":
            self.eat("(")
            args = []
            if self.peek() != ")":
                args.append(self.ternary())
                while self.peek() == ",":
                    self.eat()
                    args.append(self.ternary())
            self.eat(")")
            fn = {
                "math.sin": lambda a: math.sin(math.radians(a)), "math.cos": lambda a: math.cos(math.radians(a)),
                "math.clamp": lambda a, lo, hi: min(max(a, lo), hi), "math.lerp": lambda a, b, t: a + (b - a) * t,
                "math.max": max, "math.min": min, "math.abs": abs, "math.sqrt": math.sqrt,
                "math.floor": math.floor, "math.mod": math.fmod, "math.pow": math.pow,
            }.get(name)
            return float(fn(*args)) if fn else 0.0
        if name in self.env:
            return float(self.env[name])
        return _Undef(0.0)


