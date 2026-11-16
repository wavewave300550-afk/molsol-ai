"""
A small but strict Molang implementation (parser + evaluator).

Used by the build to validate every expression we generate, and by the
preview renderer to evaluate animations frame by frame.

Supported: numbers (optional 'f' suffix), 'strings', true/false, this,
query./q., variable./v., temp./t., context./c., math.*, the '->' arrow
operator (context.owning_entity->query.x), unary ! -, * /, + -, comparisons,
== !=, && ||, ?? (null coalescing), ternary a ? b : c, binary conditional
a ? b, assignment, ';' statements, return, { } blocks.

Semantics follow the Bedrock documentation: booleans are 1.0 / 0.0,
trigonometry works in degrees, unknown variables read as 0.0 (or null for ??),
a complex expression without 'return' evaluates to 0.0.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

# ----------------------------------------------------------------------------- tokens

_TOKEN_RE = re.compile(r"""
    (?P<ws>\s+)
  | (?P<num>(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?f?)
  | (?P<str>'[^']*')
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)
  | (?P<op>->|&&|\|\||==|!=|<=|>=|\?\?|[-+*/!<>?:=(),;{}\[\]])
""", re.VERBOSE)


@dataclass
class Tok:
    kind: str
    value: str
    pos: int


class MolangError(Exception):
    pass


def tokenize(src: str) -> List[Tok]:
    out: List[Tok] = []
    i = 0
    while i < len(src):
        m = _TOKEN_RE.match(src, i)
        if not m:
            raise MolangError(f"unexpected character {src[i]!r} at {i} in: {src}")
        kind = m.lastgroup
        if kind != "ws":
            out.append(Tok(kind, m.group(kind), i))
        i = m.end()
    out.append(Tok("eof", "", len(src)))
    return out


# ----------------------------------------------------------------------------- AST

@dataclass
class Node:
    pass


@dataclass
class Num(Node):
    v: float


@dataclass
class Str(Node):
    v: str


@dataclass
class Name(Node):
    """A dotted name: kind in {query, variable, temp, context, math, this, geometry, material, texture, array}."""
    kind: str
    path: str


@dataclass
class Call(Node):
    fn: Name
    args: List[Node]


@dataclass
class Arrow(Node):
    left: Node
    right: Node


@dataclass
class Unary(Node):
    op: str
    a: Node


@dataclass
class Bin(Node):
    op: str
    a: Node
    b: Node


@dataclass
class Ternary(Node):
    c: Node
    a: Node
    b: Optional[Node]


@dataclass
class Assign(Node):
    target: Name
    value: Node


@dataclass
class Block(Node):
    stmts: List[Node]


@dataclass
class Return(Node):
    value: Node


@dataclass
class Program(Node):
    stmts: List[Node]
    complex: bool


_KIND_ALIASES = {
    "q": "query", "query": "query",
    "v": "variable", "variable": "variable",
    "t": "temp", "temp": "temp",
    "c": "context", "context": "context",
    "math": "math", "geometry": "geometry", "material": "material", "texture": "texture",
    "array": "array",
}

KNOWN_MATH = {
    "abs", "acos", "asin", "atan", "atan2", "ceil", "clamp", "copy_sign", "cos", "die_roll", "die_roll_integer",
    "exp", "floor", "hermite_blend", "inverse_lerp", "lerp", "lerprotate", "ln", "max", "min", "min_angle", "mod",
    "pi", "pow", "random", "random_integer", "round", "sign", "sin", "sqrt", "trunc",
} | {f"ease_{a}_{b}" for a in ("in", "out", "in_out") for b in
     ("back", "bounce", "circ", "cubic", "elastic", "expo", "quad", "quart", "quint", "sine")}


class Parser:
    # binding powers (higher binds tighter)
    BIN = {
        "||": 3, "&&": 4,
        "==": 5, "!=": 5,
        "<": 6, "<=": 6, ">": 6, ">=": 6,
        "+": 7, "-": 7,
        "*": 8, "/": 8,
    }

    def __init__(self, src: str):
        self.src = src
        self.toks = tokenize(src)
        self.i = 0

    # -- helpers
    def peek(self, k=0) -> Tok:
        return self.toks[min(self.i + k, len(self.toks) - 1)]

    def next(self) -> Tok:
        t = self.toks[self.i]
        self.i += 1
        return t

    def expect(self, value: str) -> Tok:
        t = self.next()
        if t.value != value:
            raise MolangError(f"expected {value!r} at {t.pos}, found {t.value!r} in: {self.src}")
        return t

    # -- grammar
    def parse_program(self) -> Program:
        stmts: List[Node] = []
        complex_ = False
        while self.peek().kind != "eof":
            stmts.append(self.parse_statement())
            if self.peek().value == ";":
                self.next()
                complex_ = True
            elif self.peek().kind != "eof":
                raise MolangError(f"expected ';' at {self.peek().pos} in: {self.src}")
        if not stmts:
            raise MolangError("empty expression")
        return Program(stmts, complex_)

    def parse_statement(self) -> Node:
        if self.peek().kind == "name" and self.peek().value == "return":
            self.next()
            return Return(self.parse_expr(0))
        return self.parse_expr(0)

    def parse_block(self) -> Block:
        self.expect("{")
        stmts = []
        while self.peek().value != "}":
            stmts.append(self.parse_statement())
            if self.peek().value == ";":
                self.next()
            elif self.peek().value != "}":
                raise MolangError(f"expected ';' or '}}' at {self.peek().pos} in: {self.src}")
        self.expect("}")
        return Block(stmts)

    def parse_expr(self, rbp: int) -> Node:
        left = self.parse_unary()
        while True:
            t = self.peek()
            op = t.value if t.kind == "op" else None
            if op == "=" and rbp <= 0:
                if not isinstance(left, Name) or left.kind not in ("variable", "temp", "context"):
                    raise MolangError(f"invalid assignment target at {t.pos} in: {self.src}")
                self.next()
                left = Assign(left, self.parse_expr(0))
                continue
            if op == "?" and rbp <= 1:
                self.next()
                a = self.parse_block() if self.peek().value == "{" else self.parse_expr(1)
                b = None
                if self.peek().value == ":":
                    self.next()
                    b = self.parse_block() if self.peek().value == "{" else self.parse_expr(1)
                left = Ternary(left, a, b)
                continue
            if op == "??" and rbp <= 2:
                self.next()
                left = Bin("??", left, self.parse_expr(3))
                continue
            if op in self.BIN and self.BIN[op] > rbp:
                self.next()
                left = Bin(op, left, self.parse_expr(self.BIN[op]))
                continue
            return left

    def parse_unary(self) -> Node:
        t = self.peek()
        if t.value in ("!", "-") and t.kind == "op":
            self.next()
            return Unary(t.value, self.parse_unary())
        return self.parse_postfix(self.parse_primary())

    def parse_postfix(self, node: Node) -> Node:
        while True:
            t = self.peek()
            if t.value == "->":
                self.next()
                right = self.parse_postfix(self.parse_primary())
                node = Arrow(node, right)
                continue
            if t.value == "[":
                self.next()
                idx = self.parse_expr(0)
                self.expect("]")
                node = Call(Name("index", "[]"), [node, idx])
                continue
            return node

    def parse_primary(self) -> Node:
        t = self.next()
        if t.kind == "num":
            return Num(float(t.value.rstrip("f")))
        if t.kind == "str":
            return Str(t.value[1:-1])
        if t.value == "(":
            e = self.parse_expr(0)
            self.expect(")")
            return e
        if t.value == "{":
            self.i -= 1
            return self.parse_block()
        if t.kind == "name":
            low = t.value.lower()
            if low == "true":
                return Num(1.0)
            if low == "false":
                return Num(0.0)
            if low == "this":
                return Name("this", "this")
            if low in ("loop", "for_each", "break", "continue"):
                raise MolangError(f"{low} is not supported by this validator: {self.src}")
            head, _, rest = low.partition(".")
            kind = _KIND_ALIASES.get(head)
            if kind is None or not rest:
                raise MolangError(f"unknown identifier {t.value!r} at {t.pos} in: {self.src}")
            name = Name(kind, rest)
            if kind == "math" and rest not in KNOWN_MATH:
                raise MolangError(f"unknown math function math.{rest} in: {self.src}")
            if self.peek().value == "(":
                self.next()
                args: List[Node] = []
                if self.peek().value != ")":
                    while True:
                        args.append(self.parse_expr(0))
                        if self.peek().value == ",":
                            self.next()
                            continue
                        break
                self.expect(")")
                return Call(name, args)
            if kind == "math" and rest != "pi":
                raise MolangError(f"math.{rest} needs arguments in: {self.src}")
            return name
        raise MolangError(f"unexpected token {t.value!r} at {t.pos} in: {self.src}")


_cache: Dict[str, Program] = {}


def parse(src: str) -> Program:
    p = _cache.get(src)
    if p is None:
        p = Parser(src).parse_program()
        _cache[src] = p
    return p


# ----------------------------------------------------------------------------- evaluation

class _ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


def _ease(kind: str, mode: str, t: float) -> float:
    t = max(0.0, min(1.0, t))
    if kind == "sine":
        fin = lambda x: 1 - math.cos(x * math.pi / 2)
    elif kind == "quad":
        fin = lambda x: x * x
    elif kind == "cubic":
        fin = lambda x: x ** 3
    elif kind == "quart":
        fin = lambda x: x ** 4
    elif kind == "quint":
        fin = lambda x: x ** 5
    elif kind == "expo":
        fin = lambda x: 0.0 if x == 0 else 2 ** (10 * x - 10)
    elif kind == "circ":
        fin = lambda x: 1 - math.sqrt(max(0.0, 1 - x * x))
    elif kind == "back":
        c1 = 1.70158
        fin = lambda x: (c1 + 1) * x ** 3 - c1 * x * x
    elif kind == "elastic":
        fin = lambda x: 0.0 if x in (0.0, 1.0) else -(2 ** (10 * x - 10)) * math.sin((x * 10 - 10.75) * (2 * math.pi / 3))
    else:  # bounce
        def bout(x):
            n1, d1 = 7.5625, 2.75
            if x < 1 / d1:
                return n1 * x * x
            if x < 2 / d1:
                x -= 1.5 / d1
                return n1 * x * x + 0.75
            if x < 2.5 / d1:
                x -= 2.25 / d1
                return n1 * x * x + 0.9375
            x -= 2.625 / d1
            return n1 * x * x + 0.984375
        fin = lambda x: 1 - bout(1 - x)
    if mode == "in":
        return fin(t)
    if mode == "out":
        return 1 - fin(1 - t)
    return fin(2 * t) / 2 if t < 0.5 else 1 - fin(2 - 2 * t) / 2


@dataclass
class Context:
    """Evaluation context of one entity / attachable."""
    queries: Dict[str, Any] = field(default_factory=dict)
    query_fn: Optional[Callable[[str, list], Any]] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    temps: Dict[str, Any] = field(default_factory=dict)
    this: float = 0.0
    used_queries: set = field(default_factory=set)
    used_variables: set = field(default_factory=set)

    def query(self, name: str, args: list):
        self.used_queries.add(name)
        if self.query_fn is not None:
            r = self.query_fn(name, args)
            if r is not None:
                return r
        if name in self.queries:
            v = self.queries[name]
            return v(*args) if callable(v) else v
        raise MolangError(f"query.{name} has no value in this evaluation context")


def _num(x) -> float:
    if x is None:
        return 0.0
    if isinstance(x, bool):
        return 1.0 if x else 0.0
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        return 0.0
    raise MolangError(f"cannot use {x!r} as a number")


def _eval(n: Node, ctx: Context):
    if isinstance(n, Num):
        return n.v
    if isinstance(n, Str):
        return n.v
    if isinstance(n, Name):
        if n.kind == "this":
            return ctx.this
        if n.kind == "variable":
            ctx.used_variables.add(n.path)
            return ctx.variables.get(n.path)
        if n.kind == "temp":
            return ctx.temps.get(n.path)
        if n.kind == "context":
            v = ctx.context.get(n.path)
            return v
        if n.kind == "query":
            return ctx.query(n.path, [])
        if n.kind == "math" and n.path == "pi":
            return math.pi
        raise MolangError(f"cannot evaluate {n.kind}.{n.path}")
    if isinstance(n, Call):
        if n.fn.kind == "index":
            raise MolangError("array indexing is not supported")
        args = [_eval(a, ctx) for a in n.args]
        if n.fn.kind == "query":
            return ctx.query(n.fn.path, args)
        if n.fn.kind == "math":
            return _math(n.fn.path, [_num(a) for a in args])
        raise MolangError(f"cannot call {n.fn.kind}.{n.fn.path}")
    if isinstance(n, Arrow):
        target = _eval(n.left, ctx)
        if not isinstance(target, Context):
            return None
        return _eval(n.right, target)
    if isinstance(n, Unary):
        a = _num(_eval(n.a, ctx))
        return (1.0 if a == 0 else 0.0) if n.op == "!" else -a
    if isinstance(n, Bin):
        if n.op == "??":
            a = _eval(n.a, ctx)
            return _eval(n.b, ctx) if a is None else a
        if n.op == "&&":
            return 1.0 if (_num(_eval(n.a, ctx)) != 0 and _num(_eval(n.b, ctx)) != 0) else 0.0
        if n.op == "||":
            return 1.0 if (_num(_eval(n.a, ctx)) != 0 or _num(_eval(n.b, ctx)) != 0) else 0.0
        a, b = _eval(n.a, ctx), _eval(n.b, ctx)
        if n.op in ("==", "!=") and (isinstance(a, str) or isinstance(b, str)):
            eq = a == b
            return 1.0 if (eq if n.op == "==" else not eq) else 0.0
        a, b = _num(a), _num(b)
        if n.op == "+":
            return a + b
        if n.op == "-":
            return a - b
        if n.op == "*":
            return a * b
        if n.op == "/":
            return 0.0 if b == 0 else a / b
        if n.op == "<":
            return 1.0 if a < b else 0.0
        if n.op == "<=":
            return 1.0 if a <= b else 0.0
        if n.op == ">":
            return 1.0 if a > b else 0.0
        if n.op == ">=":
            return 1.0 if a >= b else 0.0
        if n.op == "==":
            return 1.0 if a == b else 0.0
        if n.op == "!=":
            return 1.0 if a != b else 0.0
    if isinstance(n, Ternary):
        c = _num(_eval(n.c, ctx)) != 0
        if c:
            return _eval(n.a, ctx)
        return _eval(n.b, ctx) if n.b is not None else 0.0
    if isinstance(n, Assign):
        v = _eval(n.value, ctx)
        if n.target.kind == "variable":
            ctx.variables[n.target.path] = v
            ctx.used_variables.add(n.target.path)
        elif n.target.kind == "temp":
            ctx.temps[n.target.path] = v
        else:
            ctx.context[n.target.path] = v
        return v
    if isinstance(n, Block):
        for s in n.stmts:
            _eval(s, ctx)
        return 0.0
    if isinstance(n, Return):
        raise _ReturnSignal(_eval(n.value, ctx))
    raise MolangError(f"cannot evaluate node {n}")


def _math(fn: str, a: List[float]) -> float:
    d = math.radians
    if fn == "abs":
        return abs(a[0])
    if fn == "sin":
        return math.sin(d(a[0]))
    if fn == "cos":
        return math.cos(d(a[0]))
    if fn == "asin":
        return math.degrees(math.asin(max(-1, min(1, a[0]))))
    if fn == "acos":
        return math.degrees(math.acos(max(-1, min(1, a[0]))))
    if fn == "atan":
        return math.degrees(math.atan(a[0]))
    if fn == "atan2":
        return math.degrees(math.atan2(a[0], a[1]))
    if fn == "clamp":
        return max(a[1], min(a[2], a[0]))
    if fn == "lerp":
        return a[0] + (a[1] - a[0]) * a[2]
    if fn == "inverse_lerp":
        return 0.0 if a[1] == a[0] else (a[2] - a[0]) / (a[1] - a[0])
    if fn == "lerprotate":
        diff = (a[1] - a[0] + 180) % 360 - 180
        return a[0] + diff * a[2]
    if fn == "min":
        return min(a[0], a[1])
    if fn == "max":
        return max(a[0], a[1])
    if fn == "mod":
        return math.fmod(a[0], a[1]) if a[1] != 0 else 0.0
    if fn == "pow":
        try:
            return math.pow(a[0], a[1])
        except (ValueError, OverflowError):
            return 0.0
    if fn == "sqrt":
        return math.sqrt(a[0]) if a[0] >= 0 else 0.0
    if fn == "exp":
        return math.exp(min(a[0], 700))
    if fn == "ln":
        return math.log(a[0]) if a[0] > 0 else 0.0
    if fn == "floor":
        return float(math.floor(a[0]))
    if fn == "ceil":
        return float(math.ceil(a[0]))
    if fn == "round":
        return float(math.floor(a[0] + 0.5))
    if fn == "trunc":
        return float(math.trunc(a[0]))
    if fn == "sign":
        return 1.0 if a[0] > 0 else (-1.0 if a[0] < 0 else 0.0)
    if fn == "copy_sign":
        return math.copysign(a[0], a[1])
    if fn == "hermite_blend":
        x = a[0]
        return 3 * x * x - 2 * x * x * x
    if fn == "min_angle":
        return (a[0] + 180) % 360 - 180
    if fn.startswith("ease_"):
        mode, _, kind = fn[5:].rpartition("_")
        return a[0] + (a[1] - a[0]) * _ease(kind, mode, a[2])
    if fn in ("random", "die_roll", "die_roll_integer", "random_integer"):
        raise MolangError(f"math.{fn} is non-deterministic; not used in this add-on")
    raise MolangError(f"unknown math function {fn}")


_ARG_COUNT = {
    "abs": 1, "sin": 1, "cos": 1, "asin": 1, "acos": 1, "atan": 1, "atan2": 2, "clamp": 3, "lerp": 3,
    "inverse_lerp": 3, "lerprotate": 3, "min": 2, "max": 2, "mod": 2, "pow": 2, "sqrt": 1, "exp": 1, "ln": 1,
    "floor": 1, "ceil": 1, "round": 1, "trunc": 1, "sign": 1, "copy_sign": 2, "hermite_blend": 1, "min_angle": 1,
}


def check_arity(prog: Node) -> List[str]:
    """Static checks on a parsed program (math arity)."""
    problems: List[str] = []

    def walk(n):
        if isinstance(n, Call) and n.fn.kind == "math":
            want = 3 if n.fn.path.startswith("ease_") else _ARG_COUNT.get(n.fn.path)
            if want is not None and len(n.args) != want:
                problems.append(f"math.{n.fn.path} takes {want} arguments, got {len(n.args)}")
        for v in vars(n).values() if isinstance(n, Node) else []:
            if isinstance(v, Node):
                walk(v)
            elif isinstance(v, list):
                for x in v:
                    if isinstance(x, Node):
                        walk(x)
    walk(prog)
    return problems


def names_used(prog: Node, kind: str) -> set:
    out = set()

    def walk(n):
        if isinstance(n, Name) and n.kind == kind:
            out.add(n.path)
        if isinstance(n, Call) and n.fn.kind == kind:
            out.add(n.fn.path)
        if isinstance(n, Node):
            for v in vars(n).values():
                if isinstance(v, Node):
                    walk(v)
                elif isinstance(v, list):
                    for x in v:
                        if isinstance(x, Node):
                            walk(x)
    walk(prog)
    return out


def evaluate(src, ctx: Context, this: float = 0.0) -> float:
    """Evaluate a number or a Molang string."""
    if isinstance(src, (int, float)):
        return float(src)
    prog = parse(src)
    ctx.this = this
    ctx.temps = {}
    try:
        last = 0.0
        for s in prog.stmts:
            last = _eval(s, ctx)
        if prog.complex:
            return 0.0
        return _num(last)
    except _ReturnSignal as r:
        return _num(r.value)
