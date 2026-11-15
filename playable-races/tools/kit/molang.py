"""A small Molang interpreter (the subset this add-on uses) for offline previews.

Supports numbers, q./query., v./variable., c./context., t./temp. names, math.*
functions (angles in degrees), unary - and !, * / + -, comparisons, == !=, && ||,
?: ternaries, ?? null-coalescing, parentheses, and statement lists with
assignments ("v.x = 1; v.y = v.x * 2;").
"""
from __future__ import annotations

import math
import random
import re
from typing import Any, Callable, Dict, List, Tuple

TOKEN = re.compile(r"\s*(?:(\d+\.\d*|\.\d+|\d+)f?|([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)|('[^']*')|(\?\?|&&|\|\||==|!=|<=|>=|->|[-+*/()<>!?:,;=]))")


def _tokens(src: str) -> List[Tuple[str, Any]]:
    out = []
    pos = 0
    src = src.strip()
    while pos < len(src):
        m = TOKEN.match(src, pos)
        if not m or m.end() == pos:
            raise SyntaxError(f"molang: cannot parse at {src[pos:pos + 20]!r} in {src!r}")
        pos = m.end()
        num, name, string, op = m.groups()
        if num is not None:
            out.append(("num", float(num)))
        elif name is not None:
            out.append(("name", name.lower()))
        elif string is not None:
            out.append(("str", string[1:-1]))
        elif op is not None:
            out.append(("op", op))
    out.append(("end", None))
    return out


class _P:
    def __init__(self, src: str):
        self.t = _tokens(src)
        self.i = 0

    def peek(self):
        return self.t[self.i]

    def take(self, kind=None, val=None):
        k, v = self.t[self.i]
        if kind and k != kind or (val is not None and v != val):
            raise SyntaxError(f"molang: expected {val or kind}, got {v!r}")
        self.i += 1
        return v

    def statements(self):
        out = []
        while self.peek()[0] != "end":
            if self.peek() == ("op", ";"):
                self.take()
                continue
            out.append(self.statement())
        return ("seq", out)

    def statement(self):
        k, v = self.peek()
        if k == "name" and self.t[self.i + 1] == ("op", "=") and v.split(".")[0] in ("v", "variable", "t", "temp"):
            self.take()
            self.take("op", "=")
            return ("assign", v, self.expr())
        return self.expr()

    def expr(self):
        return self.ternary()

    def ternary(self):
        cond = self.coalesce()
        if self.peek() == ("op", "?"):
            self.take()
            a = self.ternary()
            if self.peek() == ("op", ":"):
                self.take()
                b = self.ternary()
            else:
                b = ("num", 0.0)
            return ("if", cond, a, b)
        return cond

    def coalesce(self):
        a = self.orr()
        while self.peek() == ("op", "??"):
            self.take()
            a = ("??", a, self.orr())
        return a

    def orr(self):
        a = self.andd()
        while self.peek() == ("op", "||"):
            self.take()
            a = ("||", a, self.andd())
        return a

    def andd(self):
        a = self.eq()
        while self.peek() == ("op", "&&"):
            self.take()
            a = ("&&", a, self.eq())
        return a

    def eq(self):
        a = self.cmp()
        while self.peek()[1] in ("==", "!=") and self.peek()[0] == "op":
            op = self.take()
            a = (op, a, self.cmp())
        return a

    def cmp(self):
        a = self.add()
        while self.peek()[0] == "op" and self.peek()[1] in ("<", ">", "<=", ">="):
            op = self.take()
            a = (op, a, self.add())
        return a

    def add(self):
        a = self.mul()
        while self.peek()[0] == "op" and self.peek()[1] in ("+", "-"):
            op = self.take()
            a = (op, a, self.mul())
        return a

    def mul(self):
        a = self.unary()
        while self.peek()[0] == "op" and self.peek()[1] in ("*", "/"):
            op = self.take()
            a = (op, a, self.unary())
        return a

    def unary(self):
        if self.peek() == ("op", "-"):
            self.take()
            return ("neg", self.unary())
        if self.peek() == ("op", "!"):
            self.take()
            return ("not", self.unary())
        return self.atom()

    def atom(self):
        k, v = self.peek()
        if k == "num":
            self.take()
            return ("num", v)
        if k == "str":
            self.take()
            return ("str", v)
        if (k, v) == ("op", "("):
            self.take()
            e = self.expr()
            self.take("op", ")")
            return e
        if k == "name":
            self.take()
            if self.peek() == ("op", "("):
                self.take()
                args = []
                if self.peek() != ("op", ")"):
                    args.append(self.expr())
                    while self.peek() == ("op", ","):
                        self.take()
                        args.append(self.expr())
                self.take("op", ")")
                return ("call", v, args)
            if v in ("true", "false"):
                return ("num", 1.0 if v == "true" else 0.0)
            return ("var", v)
        raise SyntaxError(f"molang: unexpected {v!r}")


def _norm(name: str) -> Tuple[str, str]:
    head, _, rest = name.partition(".")
    head = {"query": "q", "variable": "v", "context": "c", "temp": "t"}.get(head, head)
    return head, rest


MATH: Dict[str, Callable] = {
    "sin": lambda x: math.sin(math.radians(x)), "cos": lambda x: math.cos(math.radians(x)),
    "abs": abs, "clamp": lambda x, a, b: max(a, min(b, x)), "mod": lambda a, b: math.fmod(a, b) if b else 0.0,
    "max": max, "min": min, "floor": math.floor, "ceil": math.ceil, "round": round, "trunc": math.trunc,
    "pow": lambda a, b: math.pow(a, b) if a >= 0 or float(b).is_integer() else 0.0,
    "sqrt": lambda x: math.sqrt(max(0.0, x)), "lerp": lambda a, b, t: a + (b - a) * t,
    "hermite_blend": lambda t: 3 * t * t - 2 * t * t * t, "exp": math.exp, "ln": lambda x: math.log(max(1e-9, x)),
    "random": lambda a, b: random.uniform(a, b), "atan2": lambda y, x: math.degrees(math.atan2(y, x)),
    "pi": lambda: math.pi,
}


class Env:
    def __init__(self, q: Dict[str, Any] = None, v: Dict[str, float] = None, c: Dict[str, Any] = None):
        self.q = q or {}
        self.v = v if v is not None else {}
        self.c = c or {}
        self.t: Dict[str, float] = {}
        self.this = 0.0
        self.missing: set = set()


def _val(node, env: Env):
    k = node[0]
    if k == "num":
        return node[1]
    if k == "str":
        return node[1]
    if k == "var":
        if node[1] == "this":
            return env.this
        head, rest = _norm(node[1])
        if head == "q":
            if rest not in env.q:
                env.missing.add("q." + rest)
            return env.q.get(rest, 0.0)
        if head == "v":
            return env.v.get(rest, 0.0)
        if head == "c":
            return env.c.get(rest, 0.0)
        if head == "t":
            return env.t.get(rest, 0.0)
        if head == "math" and rest == "pi":
            return math.pi
        env.missing.add(node[1])
        return 0.0
    if k == "call":
        head, rest = _norm(node[1])
        args = [_val(a, env) for a in node[2]]
        if head == "math":
            return float(MATH[rest](*args))
        if head == "q":
            fn = env.q.get(rest)
            if callable(fn):
                return float(fn(*args))
            env.missing.add("q." + rest + "()")
            return 0.0
        env.missing.add(node[1] + "()")
        return 0.0
    if k == "neg":
        return -_val(node[1], env)
    if k == "not":
        return 0.0 if _val(node[1], env) else 1.0
    if k == "if":
        return _val(node[2], env) if _val(node[1], env) else _val(node[3], env)
    if k == "??":
        a = _val(node[1], env)
        return a if a is not None else _val(node[2], env)
    if k == "assign":
        head, rest = _norm(node[1])
        val = _val(node[2], env)
        (env.v if head == "v" else env.t)[rest] = val
        return val
    if k == "seq":
        r = 0.0
        for s in node[1]:
            r = _val(s, env)
        return r
    a = _val(node[1], env)
    if k == "&&":
        return 1.0 if a and _val(node[2], env) else 0.0
    if k == "||":
        return 1.0 if a or _val(node[2], env) else 0.0
    b = _val(node[2], env)
    if k == "+":
        return a + b
    if k == "-":
        return a - b
    if k == "*":
        return a * b
    if k == "/":
        return a / b if b else 0.0
    if k == "<":
        return float(a < b)
    if k == ">":
        return float(a > b)
    if k == "<=":
        return float(a <= b)
    if k == ">=":
        return float(a >= b)
    if k == "==":
        return float(a == b)
    if k == "!=":
        return float(a != b)
    raise ValueError(k)


_cache: Dict[str, Any] = {}


def evaluate(expr, env: Env) -> float:
    if isinstance(expr, (int, float)):
        return float(expr)
    tree = _cache.get(expr)
    if tree is None:
        tree = _P(expr).statements()
        _cache[expr] = tree
    r = _val(tree, env)
    return float(r) if not isinstance(r, str) else r


def check(expr: str) -> None:
    """Raise SyntaxError if the expression does not parse."""
    _P(expr).statements()
