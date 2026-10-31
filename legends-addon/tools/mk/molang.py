"""
A small Molang parser/evaluator.

Used for two things:
  * static validation: every expression written into the packs is parsed, and
    every query / variable it references is checked;
  * previews: animations are sampled at a given time so poses can be rendered.

Supported: numbers, 'strings', math.*, query./q., variable./v., temp./t.,
context./c., Array.x[...], the usual arithmetic / logic / comparison
operators, ?: and binary ?, ?? , assignments and ';'-separated statements,
`return`.
"""
from __future__ import annotations

import math
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

TOKEN = re.compile(r"\s*(?:(\d+\.\d*|\.\d+|\d+)f?|('[^']*')|([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)|(\?\?|&&|\|\||==|!=|<=|>=|->|[-+*/()<>!?:,;=\[\]{}]))")

ALIASES = {"q": "query", "v": "variable", "t": "temp", "c": "context"}

MATH = {
    "sin": lambda a: math.sin(math.radians(a)),
    "cos": lambda a: math.cos(math.radians(a)),
    "asin": lambda a: math.degrees(math.asin(max(-1, min(1, a)))),
    "acos": lambda a: math.degrees(math.acos(max(-1, min(1, a)))),
    "atan": lambda a: math.degrees(math.atan(a)),
    "atan2": lambda y, x: math.degrees(math.atan2(y, x)),
    "abs": abs, "sqrt": lambda a: math.sqrt(max(0, a)), "exp": math.exp,
    "ln": lambda a: math.log(a) if a > 0 else 0.0,
    "floor": math.floor, "ceil": math.ceil, "round": lambda a: math.floor(a + 0.5), "trunc": math.trunc,
    "pow": lambda a, b: a ** b if a >= 0 or float(b).is_integer() else 0.0,
    "min": min, "max": max, "clamp": lambda v, lo, hi: max(lo, min(hi, v)),
    "lerp": lambda a, b, t: a + (b - a) * t,
    "lerprotate": lambda a, b, t: a + (((b - a + 180) % 360) - 180) * t,
    "mod": lambda a, b: math.fmod(a, b) if b else 0.0,
    "sign": lambda a: (a > 0) - (a < 0),
    "hermite_blend": lambda t: 3 * t * t - 2 * t * t * t,
    "random": lambda a, b: (a + b) / 2, "random_integer": lambda a, b: round((a + b) / 2),
    "die_roll": lambda n, a, b: n * (a + b) / 2, "die_roll_integer": lambda n, a, b: n * round((a + b) / 2),
    "min_angle": lambda a: ((a + 180) % 360) - 180,
    "pi": None,
}
MATH_ARITY = {"pi": 0}

# Queries the packs are allowed to use (all documented, stable Molang queries).
KNOWN_QUERIES = {
    "life_time", "anim_time", "delta_time", "time_stamp", "modified_distance_moved", "modified_move_speed",
    "ground_speed", "vertical_speed", "is_on_ground", "is_moving", "is_alive", "property", "has_property",
    "target_x_rotation", "target_y_rotation", "body_y_rotation", "head_x_rotation", "head_y_rotation",
    "all_animations_finished", "any_animation_finished", "is_invisible", "health", "max_health",
    "has_target", "is_delayed_attacking", "is_in_water", "is_sneaking", "is_riding", "yaw_speed",
    "camera_distance_range_lerp", "distance_from_camera", "is_first_person", "time_of_day", "moon_phase",
    "last_hit_by_player",
}
BUILTIN_VARIABLES = {"variable.is_first_person", "variable.map_face_icon", "variable.particle_age",
                     "variable.particle_lifetime", "variable.particle_random_1", "variable.particle_random_2",
                     "variable.particle_random_3", "variable.particle_random_4", "variable.emitter_age",
                     "variable.emitter_lifetime", "variable.emitter_random_1", "variable.emitter_random_2",
                     "variable.emitter_random_3", "variable.emitter_random_4"}


class MolangError(Exception):
    pass


def tokenize(src: str) -> List[Tuple[str, Any]]:
    out, pos = [], 0
    src = src.strip()
    while pos < len(src):
        m = TOKEN.match(src, pos)
        if not m or m.end() == pos:
            raise MolangError(f"bad token at {pos} in {src!r}")
        num, s, name, op = m.groups()
        if num is not None:
            out.append(("num", float(num)))
        elif s is not None:
            out.append(("str", s[1:-1]))
        elif name is not None:
            out.append(("name", name))
        else:
            out.append(("op", op))
        pos = m.end()
        while pos < len(src) and src[pos].isspace():
            pos += 1
    return out


def norm_name(name: str) -> str:
    parts = name.split(".")
    head = parts[0].lower()
    head = ALIASES.get(head, head)
    return ".".join([head] + [p.lower() for p in parts[1:]])


class Parser:
    def __init__(self, src):
        self.src = src
        self.toks = tokenize(src)
        self.i = 0

    def peek(self, k=0):
        j = self.i + k
        return self.toks[j] if j < len(self.toks) else ("eof", None)

    def eat(self, op=None):
        t = self.peek()
        if op is not None and not (t[0] == "op" and t[1] == op):
            raise MolangError(f"expected {op!r} got {t[1]!r} in {self.src!r}")
        self.i += 1
        return t

    def is_op(self, *ops):
        t = self.peek()
        return t[0] == "op" and t[1] in ops

    # program := statement (';' statement)* ';'?
    def program(self):
        stmts = []
        while self.peek()[0] != "eof":
            if self.is_op(";"):
                self.eat(";")
                continue
            stmts.append(self.statement())
            if self.peek()[0] != "eof":
                self.eat(";")
        return ("prog", stmts)

    def statement(self):
        t = self.peek()
        if t[0] == "name" and t[1].lower() == "return":
            self.eat()
            return ("return", self.expr())
        if t[0] == "name" and self.peek(1) == ("op", "="):
            name = norm_name(t[1])
            if not name.split(".")[0] in ("variable", "temp"):
                raise MolangError(f"cannot assign to {t[1]} in {self.src!r}")
            self.eat()
            self.eat("=")
            return ("assign", name, self.expr())
        return self.expr()

    def expr(self):
        cond = self.coalesce()
        if self.is_op("?"):
            self.eat("?")
            a = self.expr()
            if self.is_op(":"):
                self.eat(":")
                b = self.expr()
            else:
                b = ("num", 0.0)
            return ("tern", cond, a, b)
        return cond

    def _bin(self, sub, ops):
        left = sub()
        while self.is_op(*ops):
            op = self.eat()[1]
            left = ("bin", op, left, sub())
        return left

    def coalesce(self):
        return self._bin(self.or_, ("??",))

    def or_(self):
        return self._bin(self.and_, ("||",))

    def and_(self):
        return self._bin(self.eq, ("&&",))

    def eq(self):
        return self._bin(self.cmp, ("==", "!="))

    def cmp(self):
        return self._bin(self.add, ("<", "<=", ">", ">="))

    def add(self):
        return self._bin(self.mul, ("+", "-"))

    def mul(self):
        return self._bin(self.unary, ("*", "/"))

    def unary(self):
        if self.is_op("-", "!", "+"):
            op = self.eat()[1]
            return ("un", op, self.unary())
        return self.postfix()

    def postfix(self):
        node = self.primary()
        while self.is_op("["):
            self.eat("[")
            idx = self.expr()
            self.eat("]")
            node = ("index", node, idx)
        return node

    def primary(self):
        t = self.eat()
        if t[0] == "num":
            return ("num", t[1])
        if t[0] == "str":
            return ("str", t[1])
        if t[0] == "op" and t[1] == "(":
            e = self.expr()
            self.eat(")")
            return e
        if t[0] == "name":
            name = norm_name(t[1])
            if self.is_op("("):
                self.eat("(")
                args = []
                if not self.is_op(")"):
                    args.append(self.expr())
                    while self.is_op(","):
                        self.eat(",")
                        args.append(self.expr())
                self.eat(")")
                return ("call", name, args)
            return ("name", name)
        raise MolangError(f"unexpected {t[1]!r} in {self.src!r}")


_cache: Dict[str, Any] = {}


def parse(src) -> Any:
    if isinstance(src, (int, float)):
        return ("prog", [("num", float(src))])
    if src not in _cache:
        p = Parser(src)
        _cache[src] = p.program()
    return _cache[src]


def refs(src) -> Tuple[Set[str], Set[str], Set[str]]:
    """(queries, variables read, variables assigned) referenced by an expression."""
    q, rd, wr = set(), set(), set()

    def walk(n):
        k = n[0]
        if k == "prog":
            for s in n[1]:
                walk(s)
        elif k == "assign":
            wr.add(n[1])
            walk(n[2])
        elif k == "return":
            walk(n[1])
        elif k == "call":
            if n[1].startswith("query."):
                q.add(n[1][6:])
            elif n[1].startswith("math."):
                fn = n[1][5:]
                if fn not in MATH:
                    raise MolangError(f"unknown math function {n[1]}")
            else:
                raise MolangError(f"unknown function {n[1]}")
            for a in n[2]:
                walk(a)
        elif k == "name":
            if n[1].startswith("query."):
                q.add(n[1][6:])
            elif n[1].startswith(("variable.", "temp.")):
                rd.add(n[1])
            elif n[1] == "math.pi":
                pass
            elif n[1].split(".")[0] in ("array", "geometry", "texture", "material", "context"):
                pass
            elif n[1] in ("true", "false", "this"):
                pass
            else:
                raise MolangError(f"unknown identifier {n[1]}")
        elif k in ("bin",):
            walk(n[2])
            walk(n[3])
        elif k == "un":
            walk(n[2])
        elif k == "tern":
            walk(n[1])
            walk(n[2])
            walk(n[3])
        elif k == "index":
            walk(n[1])
            walk(n[2])
    walk(parse(src))
    return q, rd, wr


class Env:
    def __init__(self, queries: Optional[Dict[str, Any]] = None, variables: Optional[Dict[str, float]] = None):
        self.queries = queries or {}
        self.vars: Dict[str, float] = dict(variables or {})

    def q(self, name, args):
        v = self.queries.get(name)
        if callable(v):
            return v(*args)
        if v is None:
            return 0.0
        return v


def evaluate(src, env: Env):
    if isinstance(src, (int, float)):
        return float(src)
    tree = parse(src)
    result = 0.0
    for st in tree[1]:
        k = st[0]
        if k == "assign":
            env.vars[st[1]] = _ev(st[2], env)
        elif k == "return":
            return _ev(st[1], env)
        else:
            result = _ev(st, env)
    return result


def _num(v):
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    return 0.0


def _ev(n, env: Env):
    k = n[0]
    if k == "num":
        return n[1]
    if k == "str":
        return n[1]
    if k == "name":
        nm = n[1]
        if nm.startswith("query."):
            return _num(env.q(nm[6:], []))
        if nm == "math.pi":
            return math.pi
        if nm in ("true",):
            return 1.0
        if nm in ("false",):
            return 0.0
        return env.vars.get(nm, None) if nm in env.vars else 0.0
    if k == "call":
        nm = n[1]
        args = [_ev(a, env) for a in n[2]]
        if nm.startswith("query."):
            return _num(env.q(nm[6:], args))
        fn = MATH[nm[5:]]
        return float(fn(*[_num(a) for a in args]))
    if k == "un":
        v = _ev(n[2], env)
        if n[1] == "-":
            return -_num(v)
        if n[1] == "!":
            return 0.0 if _num(v) else 1.0
        return _num(v)
    if k == "bin":
        op = n[1]
        if op == "??":
            a = n[2]
            if a[0] == "name" and a[1].startswith(("variable.", "temp.")) and a[1] not in env.vars:
                return _ev(n[3], env)
            return _ev(a, env)
        a, b = _num(_ev(n[2], env)), _num(_ev(n[3], env))
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            return a / b if b else 0.0
        if op == "&&":
            return 1.0 if (a and b) else 0.0
        if op == "||":
            return 1.0 if (a or b) else 0.0
        if op == "==":
            return 1.0 if abs(a - b) < 1e-9 else 0.0
        if op == "!=":
            return 0.0 if abs(a - b) < 1e-9 else 1.0
        if op == "<":
            return 1.0 if a < b else 0.0
        if op == "<=":
            return 1.0 if a <= b else 0.0
        if op == ">":
            return 1.0 if a > b else 0.0
        if op == ">=":
            return 1.0 if a >= b else 0.0
    if k == "tern":
        return _ev(n[2], env) if _num(_ev(n[1], env)) else _ev(n[3], env)
    if k == "index":
        return 0.0
    raise MolangError(f"cannot evaluate node {n}")
