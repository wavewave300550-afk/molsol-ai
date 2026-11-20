"""
molang.py - a small Molang expression DSL.

Expressions are built in Python with operator overloading, serialised to
Molang text for the resource pack, and evaluated numerically so the software
renderer can pose a model exactly the way the game would.

Only the subset of Molang that this project uses is supported; `parse()` is a
recursive-descent checker used by the validator on every Molang string that
ends up in the packs.

Molang trig works in DEGREES; so does everything here.
"""
from __future__ import annotations

import math
import re
from typing import Callable, Dict, Union

Num = Union[int, float]


def fmt(x: Num) -> str:
    """Compact, stable number formatting for JSON/Molang output."""
    if isinstance(x, bool):
        return "1" if x else "0"
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


class E:
    """A Molang expression: text + evaluator + precedence (for bracketing)."""

    __slots__ = ("s", "fn", "prec")

    def __init__(self, s: str, fn: Callable[[dict], float], prec: int = 9):
        self.s, self.fn, self.prec = s, fn, prec

    # ------------------------------------------------------------ helpers
    def __str__(self) -> str:
        return self.s

    def __repr__(self) -> str:
        return f"E({self.s})"

    def ev(self, env: dict) -> float:
        return float(self.fn(env))

    def _w(self, prec: int) -> str:
        return self.s if self.prec >= prec else f"({self.s})"

    @staticmethod
    def of(x) -> "E":
        if isinstance(x, E):
            return x
        v = float(x)
        return E(fmt(v), lambda env, v=v: v, 9 if v >= 0 else 6)

    # ------------------------------------------------------------ arithmetic
    def __add__(self, o):
        o = E.of(o)
        return E(f"{self._w(4)} + {o._w(4)}", lambda e, a=self.fn, b=o.fn: a(e) + b(e), 4)

    def __radd__(self, o):
        return E.of(o) + self

    def __sub__(self, o):
        o = E.of(o)
        return E(f"{self._w(4)} - {o._w(5)}", lambda e, a=self.fn, b=o.fn: a(e) - b(e), 4)

    def __rsub__(self, o):
        return E.of(o) - self

    def __mul__(self, o):
        o = E.of(o)
        return E(f"{self._w(5)} * {o._w(5)}", lambda e, a=self.fn, b=o.fn: a(e) * b(e), 5)

    def __rmul__(self, o):
        return E.of(o) * self

    def __truediv__(self, o):
        o = E.of(o)

        def div(e, a=self.fn, b=o.fn):
            d = b(e)
            return a(e) / d if d else 0.0
        return E(f"{self._w(5)} / {o._w(6)}", div, 5)

    def __rtruediv__(self, o):
        return E.of(o) / self

    def __neg__(self):
        return E(f"-{self._w(6)}", lambda e, a=self.fn: -a(e), 6)

    # ------------------------------------------------------------ comparisons (return 1/0)
    def _cmp(self, o, op, f):
        o = E.of(o)
        return E(f"{self._w(3)} {op} {o._w(3)}", lambda e, a=self.fn, b=o.fn: 1.0 if f(a(e), b(e)) else 0.0, 2)

    def lt(self, o):
        return self._cmp(o, "<", lambda a, b: a < b)

    def le(self, o):
        return self._cmp(o, "<=", lambda a, b: a <= b)

    def gt(self, o):
        return self._cmp(o, ">", lambda a, b: a > b)

    def ge(self, o):
        return self._cmp(o, ">=", lambda a, b: a >= b)

    def eq(self, o):
        return self._cmp(o, "==", lambda a, b: abs(a - b) < 1e-6)

    def ne(self, o):
        return self._cmp(o, "!=", lambda a, b: abs(a - b) >= 1e-6)

    def and_(self, o):
        o = E.of(o)
        return E(f"{self._w(2)} && {o._w(2)}", lambda e, a=self.fn, b=o.fn: 1.0 if (a(e) and b(e)) else 0.0, 1)

    def or_(self, o):
        o = E.of(o)
        return E(f"{self._w(1)} || {o._w(1)}", lambda e, a=self.fn, b=o.fn: 1.0 if (a(e) or b(e)) else 0.0, 0)


def num(x: Num) -> E:
    return E.of(x)


def _call(name: str, pyfn, *args) -> E:
    args = [E.of(a) for a in args]
    return E(f"math.{name}({', '.join(a.s for a in args)})",
             lambda e, fs=[a.fn for a in args]: pyfn(*[f(e) for f in fs]), 9)


def sin(x):
    return _call("sin", lambda a: math.sin(math.radians(a)), x)


def cos(x):
    return _call("cos", lambda a: math.cos(math.radians(a)), x)


def mabs(x):
    return _call("abs", abs, x)


def mmin(a, b):
    return _call("min", min, a, b)


def mmax(a, b):
    return _call("max", max, a, b)


def clamp(x, lo, hi):
    return _call("clamp", lambda v, a, b: max(a, min(b, v)), x, lo, hi)


def lerp(a, b, t):
    return _call("lerp", lambda p, q_, k: p + (q_ - p) * k, a, b, t)


def lerprotate(a, b, t):
    """Lerp from a to b (degrees) the short way round the circle."""
    def f(p, q_, k):
        d = math.fmod(q_ - p + 540.0, 360.0) - 180.0
        return p + d * k
    return _call("lerprotate", f, a, b, t)


def mod(a, b):
    return _call("mod", lambda p, q_: math.fmod(p, q_) if q_ else 0.0, a, b)


def floor(x):
    return _call("floor", math.floor, x)


def mpow(a, b):
    return _call("pow", lambda p, q_: math.pow(abs(p), q_) if q_ != int(q_) else math.pow(p, q_), a, b)


def sqrt(x):
    return _call("sqrt", lambda p: math.sqrt(max(0.0, p)), x)


def cond(c, a, b) -> E:
    """Molang ternary `c ? a : b`."""
    c, a, b = E.of(c), E.of(a), E.of(b)
    return E(f"({c._w(1)} ? {a._w(1)} : {b._w(1)})",
             lambda e, cf=c.fn, af=a.fn, bf=b.fn: af(e) if cf(e) else bf(e), 9)


def q(name: str) -> E:
    """A query, e.g. q('anim_time') -> q.anim_time (read from env['q.anim_time'])."""
    key = f"q.{name}"
    return E(key, lambda e, k=key: e.get(k, 0.0), 9)


def v(name: str) -> E:
    key = f"v.{name}"
    return E(key, lambda e, k=key: e.get(k, 0.0), 9)


def prop(name: str) -> E:
    """Synced entity property (q.property)."""
    key = f"p.{name}"
    return E(f"q.property('{name}')", lambda e, k=key: e.get(k, 0.0), 9)


def raw(text: str, fn: Callable[[dict], float] = lambda e: 0.0) -> E:
    """Escape hatch for an expression the DSL cannot express."""
    return E(f"({text})", fn, 9)


ANIM_TIME = q("anim_time")
LIFE_TIME = q("life_time")
# q.modified_distance_moved is NOT metres: it is the game's limb-swing accumulator, which advances by
# min(1, 4 * blocks moved this tick) every tick - four units per block at boss walking speeds. (Seen in
# the game: walk cycles authored per block ran four times too fast.) BLOCKS_MOVED is the distance in blocks.
DIST = q("modified_distance_moved")
BLOCKS_MOVED = q("modified_distance_moved") * 0.25
MOVE_SPEED = q("modified_move_speed")


def out(x) -> Union[float, str]:
    """Value for a JSON animation channel: plain number, or Molang string."""
    if isinstance(x, E):
        try:
            # constant-fold pure numbers
            return float(x.s) if re.fullmatch(r"-?\d+(\.\d+)?", x.s) else x.s
        except ValueError:
            return x.s
    return round(float(x), 3)


def ev(x, env: dict) -> float:
    return x.ev(env) if isinstance(x, E) else float(x)


# --------------------------------------------------------------------------- checker

KNOWN_QUERIES = {
    "anim_time", "life_time", "modified_distance_moved", "modified_move_speed", "ground_speed",
    "property", "is_alive", "is_on_ground", "body_y_rotation", "target_x_rotation",
    "target_y_rotation", "health", "max_health", "delta_time", "is_moving", "variant",
    "all_animations_finished", "any_animation_finished", "distance_from_camera", "has_target",
    "yaw_speed", "vertical_speed", "time_stamp", "hurt_time", "is_invisible",
}
KNOWN_MATH = {
    "sin", "cos", "abs", "min", "max", "clamp", "lerp", "mod", "floor", "ceil", "round", "pow",
    "sqrt", "random", "random_integer", "atan2", "exp", "ln", "trunc", "lerprotate", "hermite_blend",
    "die_roll", "die_roll_integer", "asin", "acos", "atan", "pi",
}

_TOKEN = re.compile(r"\s*(?:(\d+\.\d*|\.\d+|\d+)|('[^']*')|([A-Za-z_][A-Za-z0-9_\.]*)|(==|!=|<=|>=|&&|\|\||\?\?|->|[-+*/()<>!?:,;=\[\]{}]))")


class MolangError(ValueError):
    pass


def parse(text: str) -> None:
    """Raise MolangError if `text` is not syntactically valid (for our subset of) Molang."""
    toks = []
    pos = 0
    text_s = text.strip()
    while pos < len(text_s):
        m = _TOKEN.match(text_s, pos)
        if not m or m.end() == pos:
            raise MolangError(f"bad token at {pos}: {text_s[pos:pos + 12]!r} in {text!r}")
        pos = m.end()
        if m.group(1):
            toks.append(("num", m.group(1)))
        elif m.group(2):
            toks.append(("str", m.group(2)))
        elif m.group(3):
            toks.append(("id", m.group(3)))
        else:
            toks.append(("op", m.group(4)))
    i = 0

    def peek(k=0):
        return toks[i + k] if i + k < len(toks) else ("eof", "")

    def take(kind=None, val=None):
        nonlocal i
        t = peek()
        if (kind and t[0] != kind) or (val and t[1] != val):
            raise MolangError(f"expected {val or kind}, got {t[1]!r} in {text!r}")
        i += 1
        return t

    def primary():
        t = peek()
        if t[0] == "num" or t[0] == "str":
            take()
            return
        if t == ("op", "("):
            take()
            expr()
            take("op", ")")
            return
        if t == ("op", "-") or t == ("op", "!") or t == ("op", "+"):
            take()
            primary()
            return
        if t[0] == "id":
            take()
            name = t[1].lower()
            head, _, rest = name.partition(".")
            if head in ("q", "query"):
                if rest not in KNOWN_QUERIES:
                    raise MolangError(f"unknown query {t[1]!r} in {text!r}")
            elif head == "math":
                if rest not in KNOWN_MATH:
                    raise MolangError(f"unknown math function {t[1]!r} in {text!r}")
            elif head in ("v", "variable", "t", "temp", "c", "context", "geometry", "material",
                          "texture", "array"):
                if not rest:
                    raise MolangError(f"incomplete identifier {t[1]!r} in {text!r}")
            elif name not in ("this", "return", "true", "false"):
                raise MolangError(f"unknown identifier {t[1]!r} in {text!r}")
            if name == "return":
                expr()
                return
            if peek() == ("op", "("):
                take()
                if peek() != ("op", ")"):
                    expr()
                    while peek() == ("op", ","):
                        take()
                        expr()
                take("op", ")")
            if peek() == ("op", "["):
                take()
                expr()
                take("op", "]")
            return
        raise MolangError(f"unexpected {t[1]!r} in {text!r}")

    def binary(level=0):
        ops = [("||",), ("&&",), ("==", "!=", "<", ">", "<=", ">="), ("+", "-"), ("*", "/")]
        if level == len(ops):
            primary()
            return
        binary(level + 1)
        while peek()[0] == "op" and peek()[1] in ops[level]:
            take()
            binary(level + 1)

    def expr():
        binary()
        if peek() == ("op", "?"):
            take()
            expr()
            if peek() == ("op", ":"):
                take()
                expr()
        if peek() == ("op", "="):
            take()
            expr()

    expr()
    while peek() == ("op", ";"):
        take()
        if peek()[0] != "eof":
            expr()
    if peek()[0] != "eof":
        raise MolangError(f"trailing {peek()[1]!r} in {text!r}")
