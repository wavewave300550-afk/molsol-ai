"""
vanilla.py - the vanilla block / item / entity catalogue for the target version,
read from the pinned @minecraft/vanilla-data package. Used to validate every
block placed by an arena structure and every vanilla id referenced by the packs.
"""
from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Dict, Set

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = os.path.join(ROOT, "node_modules", "@minecraft", "vanilla-data", "lib")


@lru_cache(maxsize=None)
def _index() -> str:
    with open(os.path.join(LIB, "index.js"), encoding="utf-8") as f:
        return f.read()


@lru_cache(maxsize=None)
def ids(kind: str) -> Dict[str, str]:
    """kind: Block | Item | Entity | Effect | Enchantment ... -> {EnumName: 'minecraft:id'}"""
    pat = re.compile(r'Minecraft%sTypes\d*\["(\w+)"\]\s*=\s*"([a-z0-9_:.]+)"' % kind)
    return dict(pat.findall(_index()))


@lru_cache(maxsize=None)
def block_states() -> Dict[str, Set[str]]:
    """'minecraft:id' -> set of valid state names."""
    with open(os.path.join(LIB, "mojang-block.d.ts"), encoding="utf-8") as f:
        src = f.read()
    names = ids("Block")
    out: Dict[str, Set[str]] = {bid: set() for bid in names.values()}
    for m in re.finditer(r"export type (\w+)States = Pick<\s*BlockStateSuperset,\s*([^>]+)>", src):
        bid = names.get(m.group(1))
        if bid:
            out[bid] = set(re.findall(r"'([^']+)'", m.group(2)))
    return out


@lru_cache(maxsize=None)
def state_values() -> Dict[str, str]:
    """state name -> declared TypeScript type text (e.g. "'x' | 'y' | 'z'" or 'boolean' or 'number')."""
    with open(os.path.join(LIB, "mojang-block.d.ts"), encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"export type BlockStateSuperset = \{(.*?)\n\};", src, re.S)
    out: Dict[str, str] = {}
    if m:
        for sm in re.finditer(r"\[?'([^']+)'\]?\??:\s*([^;]+);", m.group(1)):
            out[sm.group(1)] = " ".join(sm.group(2).split())
    return out


def check_block(name: str, states: dict) -> str:
    """Return '' when the block and its states exist in the target version, else a reason."""
    if ":" not in name:
        name = "minecraft:" + name
    cat = block_states()
    if name not in cat:
        return f"unknown block {name}"
    vals = state_values()
    for k, v in (states or {}).items():
        if k not in cat[name]:
            return f"{name}: unknown state {k} (has {sorted(cat[name])})"
        t = vals.get(k, "")
        if isinstance(v, bool):
            if "boolean" not in t:
                return f"{name}: state {k} is not boolean ({t})"
        elif isinstance(v, int):
            if "number" not in t and not re.search(r"\b%d\b" % v, t):
                return f"{name}: state {k}={v} not allowed ({t})"
        elif isinstance(v, str):
            if f"'{v}'" not in t and "string" not in t:
                return f"{name}: state {k}='{v}' not allowed ({t})"
    return ""
