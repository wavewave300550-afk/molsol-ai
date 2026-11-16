"""
molang.py - a small Molang parser + evaluator.

Used for two things:
  * static validation: every Molang string shipped in the packs is parsed, and every
    query / math function / variable it references is checked against an allow-list;
  * previews: animations are evaluated with the same expressions the game will run.

Supported: numbers, strings ('x'), identifiers (query./q., variable./v., temp./t.,
context./c., math.), calls, unary - and !, * / + -, comparisons, && ||, ?: , ??,
parentheses, assignments and ';'-separated statements with 'return'.
Angles in math.sin/cos/... are degrees, as in Minecraft.
"""
from __future__ import annotations

import math
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

TOKEN_RE = re.compile(r"""
    (?P<ws>\s+)|
    (?P<num>\d+\.\d*(?:[eE][-+]?\d+)?f?|\.\d+f?|\d+(?:[eE][-+]?\d+)?f?)|
    (?P<str>'[^']*')|
    (?P<id>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)|
    (?P<op>\?\?|&&|\|\||==|!=|<=|>=|->|[-+*/()<>!?:;,=\[\]{}])
""", re.X)

MATH_FUNCS: Dict[str, Callable[..., float]] = {
    "math.abs": abs,
    "math.acos": lambda x: math.degrees(math.acos(max(-1.0, min(1.0, x)))),
    "math.asin": lambda x: math.degrees(math.asin(max(-1.0, min(1.0, x)))),
    "math.atan": lambda x: math.degrees(math.atan(x)),
    "math.atan2": lambda y, x: math.degrees(math.atan2(y, x)),
    "math.ceil": math.ceil,
    "math.clamp": lambda v, lo, hi: max(lo, min(hi, v)),
    "math.cos": lambda x: math.cos(math.radians(x)),
    "math.die_roll": lambda n, lo, hi: n * (lo + hi) / 2,
    "math.die_roll_integer": lambda n, lo, hi: int(n * (lo + hi) / 2),
    "math.exp": math.exp,
    "math.floor": math.floor,
    "math.hermite_blend": lambda t: 3 * t * t - 2 * t * t * t,
    "math.lerp": lambda a, b, t: a + (b - a) * t,
    "math.lerprotate": lambda a, b, t: a + (((b - a + 180) % 360) - 180) * t,
    "math.ln": lambda x: math.log(x) if x > 0 else 0.0,
    "math.max": max,
    "math.min": min,
    "math.min_angle": lambda a: ((a + 180.0) % 360.0) - 180.0,
    "math.mod": lambda a, b: math.fmod(a, b) if b else 0.0,
    "math.pi": None,  # constant, handled separately
    "math.pow": lambda a, b: math.pow(a, b) if a >= 0 or float(b).is_integer() else 0.0,
    "math.random": lambda lo, hi: (lo + hi) / 2.0,
    "math.random_integer": lambda lo, hi: int((lo + hi) / 2),
    "math.round": lambda x: math.floor(x + 0.5),
    "math.sin": lambda x: math.sin(math.radians(x)),
    "math.sqrt": lambda x: math.sqrt(max(0.0, x)),
    "math.trunc": math.trunc,
    "math.sign": lambda x: (x > 0) - (x < 0),
    "math.copy_sign": lambda a, b: math.copysign(a, b),
    "math.inverse_lerp": lambda a, b, v: 0.0 if b == a else (v - a) / (b - a),
}

# queries used by this add-on must appear here (checked by the validator)
KNOWN_QUERIES = {
    "query.anim_time", "query.life_time", "query.delta_time", "query.property", "query.has_property",
    "query.is_alive", "query.health", "query.max_health", "query.hurt_time", "query.frame_alpha",
    "query.time_stamp", "query.ground_speed", "query.vertical_speed", "query.is_on_ground",
    "query.body_y_rotation", "query.modified_move_speed", "query.all_animations_finished",
    "query.any_animation_finished", "query.is_moving", "query.time_of_day", "query.variant",
    "query.distance_from_camera", "query.camera_distance_range_lerp", "query.yaw_speed",
}

PARTICLE_VARS = {
    "variable.particle_age", "variable.particle_lifetime", "variable.particle_random_1",
    "variable.particle_random_2", "variable.particle_random_3", "variable.particle_random_4",
    "variable.emitter_age", "variable.emitter_lifetime", "variable.emitter_random_1",
    "variable.emitter_random_2", "variable.emitter_random_3", "variable.emitter_random_4",
}


class MolangError(Exception):
    pass


def tokenize(src: str) -> List[Tuple[str, str]]:
    out = []
    pos = 0
    while pos < len(src):
        m = TOKEN_RE.match(src, pos)
        if not m:
            raise MolangError(f"bad character {src[pos]!r} at {pos} in {src!r}")
        pos = m.end()
        kind = m.lastgroup
        if kind == "ws":
            continue
        out.append((kind, m.group(kind)))
    out.append(("eof", ""))
    return out


def canon(name: str) -> str:
    low = name.lower()
    for short, full in (("q.", "query."), ("v.", "variable."), ("t.", "temp."), ("c.", "context.")):
        if low.startswith(short):
            return full + low[len(short):]
    return low


class Parser:
    def __init__(self, src: str):
        self.src = src
        self.toks = tokenize(src)
        self.i = 0

    def peek(self, k=0):
        return self.toks[self.i + k]

    def take(self, value=None):
        tok = self.toks[self.i]
        if value is not None and tok[1] != value:
            raise MolangError(f"expected {value!r} got {tok[1]!r} in {self.src!r}")
        self.i += 1
        return tok

    # program := statement (';' statement)* [';']
    def program(self):
        stmts = []
        while self.peek()[0] != "eof":
            if self.peek()[1] == ";":
                self.take()
                continue
            stmts.append(self.statement())
            if self.peek()[1] == ";":
                self.take()
            elif self.peek()[0] != "eof":
                raise MolangError(f"unexpected {self.peek()[1]!r} in {self.src!r}")
        return ("prog", stmts)

    def statement(self):
        tok = self.peek()
        if tok[0] == "id" and tok[1].lower() == "return":
            self.take()
            return ("return", self.expr())
        # assignment?
        if tok[0] == "id" and self.peek(1)[1] == "=":
            name = canon(self.take()[1])
            self.take("=")
            return ("assign", name, self.expr())
        return ("expr", self.expr())

    def expr(self):
        return self.ternary()

    def ternary(self):
        cond = self.coalesce()
        if self.peek()[1] == "?":
            self.take()
            a = self.ternary()
            if self.peek()[1] == ":":
                self.take()
                b = self.ternary()
                return ("tern", cond, a, b)
            return ("tern", cond, a, ("num", 0.0))
        return cond

    def coalesce(self):
        left = self.logic_or()
        while self.peek()[1] == "??":
            self.take()
            left = ("??", left, self.logic_or())
        return left

    def logic_or(self):
        left = self.logic_and()
        while self.peek()[1] == "||":
            self.take()
            left = ("||", left, self.logic_and())
        return left

    def logic_and(self):
        left = self.compare()
        while self.peek()[1] == "&&":
            self.take()
            left = ("&&", left, self.compare())
        return left

    def compare(self):
        left = self.additive()
        while self.peek()[1] in ("<", ">", "<=", ">=", "==", "!="):
            op = self.take()[1]
            left = (op, left, self.additive())
        return left

    def additive(self):
        left = self.mult()
        while self.peek()[1] in ("+", "-"):
            op = self.take()[1]
            left = (op, left, self.mult())
        return left

    def mult(self):
        left = self.unary()
        while self.peek()[1] in ("*", "/"):
            op = self.take()[1]
            left = (op, left, self.unary())
        return left

    def unary(self):
        if self.peek()[1] == "-":
            self.take()
            return ("neg", self.unary())
        if self.peek()[1] == "!":
            self.take()
            return ("not", self.unary())
        if self.peek()[1] == "+":
            self.take()
            return self.unary()
        return self.primary()

    def primary(self):
        kind, val = self.peek()
        if kind == "num":
            self.take()
            return ("num", float(val.rstrip("f")))
        if kind == "str":
            self.take()
            return ("str", val[1:-1])
        if val == "(":
            self.take()
            e = self.expr()
            self.take(")")
            return e
        if kind == "id":
            self.take()
            name = canon(val)
            if name in ("true", "false"):
                return ("num", 1.0 if name == "true" else 0.0)
            if self.peek()[1] == "(":
                self.take()
                args = []
                if self.peek()[1] != ")":
                    args.append(self.expr())
                    while self.peek()[1] == ",":
                        self.take()
                        args.append(self.expr())
                self.take(")")
                return ("call", name, args)
            return ("ref", name)
        raise MolangError(f"unexpected token {val!r} in {self.src!r}")


def parse(src) -> tuple:
    if isinstance(src, (int, float)):
        return ("prog", [("expr", ("num", float(src)))])
    if not isinstance(src, str):
        raise MolangError(f"not a molang string: {src!r}")
    return Parser(src).program()


def references(tree) -> Tuple[set, set, set]:
    """Return (queries, math functions, variables) referenced by a parsed tree."""
    qs, fs, vs = set(), set(), set()

    def walk(n):
        if not isinstance(n, tuple):
            return
        tag = n[0]
        if tag == "ref":
            name = n[1]
            if name.startswith("query."):
                qs.add(name)
            elif name.startswith("variable."):
                vs.add(name)
            elif name == "math.pi":
                fs.add(name)
        elif tag == "call":
            name = n[1]
            if name.startswith("query."):
                qs.add(name)
            else:
                fs.add(name)
            for a in n[2]:
                walk(a)
            return
        elif tag == "assign":
            vs.add(n[1])
            walk(n[2])
            return
        for c in n[1:]:
            if isinstance(c, list):
                for x in c:
                    walk(x)
            else:
                walk(c)
    walk(tree)
    return qs, fs, vs


class Context:
    def __init__(self, queries: Optional[Dict[str, Any]] = None, variables: Optional[Dict[str, float]] = None,
                 properties: Optional[Dict[str, Any]] = None):
        self.queries = queries or {}
        self.variables = variables if variables is not None else {}
        self.properties = properties or {}


class _Return(Exception):
    def __init__(self, v):
        self.v = v


def _num(v):
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    return 0.0


def evaluate(src, ctx: Context) -> float:
    tree = parse(src)

    def ev(n):
        tag = n[0]
        if tag == "num":
            return n[1]
        if tag == "str":
            return n[1]
        if tag == "ref":
            name = n[1]
            if name == "math.pi":
                return math.pi
            if name.startswith("query."):
                q = ctx.queries.get(name, 0.0)
                return q() if callable(q) else q
            if name in ("this",):
                return 0.0
            return ctx.variables.get(name, 0.0)
        if tag == "call":
            name, args = n[1], [ev(a) for a in n[2]]
            if name == "query.property":
                return ctx.properties.get(args[0], 0.0)
            if name == "query.has_property":
                return 1.0 if args[0] in ctx.properties else 0.0
            if name.startswith("query."):
                q = ctx.queries.get(name, 0.0)
                return q(*args) if callable(q) else q
            fn = MATH_FUNCS.get(name)
            if fn is None:
                raise MolangError(f"unknown function {name}")
            return float(fn(*[_num(a) for a in args]))
        if tag == "neg":
            return -_num(ev(n[1]))
        if tag == "not":
            return 0.0 if _num(ev(n[1])) else 1.0
        if tag == "tern":
            return ev(n[2]) if _num(ev(n[1])) else ev(n[3])
        if tag == "??":
            a = ev(n[1])
            return a if a is not None else ev(n[2])
        if tag == "&&":
            return 1.0 if (_num(ev(n[1])) and _num(ev(n[2]))) else 0.0
        if tag == "||":
            return 1.0 if (_num(ev(n[1])) or _num(ev(n[2]))) else 0.0
        a, b = ev(n[1]), ev(n[2])
        if tag in ("==", "!="):
            eq = (a == b) if isinstance(a, str) or isinstance(b, str) else abs(_num(a) - _num(b)) < 1e-9
            return 1.0 if (eq if tag == "==" else not eq) else 0.0
        a, b = _num(a), _num(b)
        if tag == "+":
            return a + b
        if tag == "-":
            return a - b
        if tag == "*":
            return a * b
        if tag == "/":
            return a / b if b else 0.0
        if tag == "<":
            return 1.0 if a < b else 0.0
        if tag == ">":
            return 1.0 if a > b else 0.0
        if tag == "<=":
            return 1.0 if a <= b else 0.0
        if tag == ">=":
            return 1.0 if a >= b else 0.0
        raise MolangError(f"bad node {n}")

    last = 0.0
    try:
        for st in tree[1]:
            if st[0] == "return":
                raise _Return(ev(st[1]))
            if st[0] == "assign":
                ctx.variables[st[1]] = _num(ev(st[2]))
                last = 0.0
            else:
                last = ev(st[1])
    except _Return as r:
        return _num(r.v)
    return _num(last)


if __name__ == "__main__":
    c = Context(queries={"query.anim_time": 0.5}, properties={"sab:phase": 2})
    assert abs(evaluate("math.sin(query.anim_time * 180)", c) - 1.0) < 1e-9
    assert evaluate("query.property('sab:phase') >= 2 ? 3 : 1", c) == 3
    assert evaluate("v.a = 2; v.b = v.a * 3; return v.b + 1;", c) == 7
    assert evaluate("-(2 + 3) * 2", c) == -10
    print("molang ok")
