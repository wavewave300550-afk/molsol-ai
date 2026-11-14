"""ED06 The World Before Names -- the primordial atmosphere: per-player distance fog in stages.

The script pushes one tagged fog at a time onto the caster's fog stack (src/lib/atmos.ts) and swaps
it on the heartbeats; the stages warm from a pale dawn haze to the golden haze of the ancient world
that hides the real far world behind the horizon ring.  Distances are fixed (blocks), so a phone
with a short render distance sees the same world as a PC; the dragons (within ~40 blocks) stay
clear.  The colours sit close to the sunset sky the spell sets, so the far haze melts into it.
"""

# id, fog start, fog end (blocks), colour
FOGS = [
    ("grimoire:ed6_fog_1", 48, 190, "#e9d6ac"),     # heartbeat 1: pale dawn haze
    ("grimoire:ed6_fog_2", 40, 165, "#e8c58c"),     # heartbeat 2: warmer, the volcano wakes
    ("grimoire:ed6_fog_3", 34, 145, "#e3b278"),     # heartbeat 3: water haze, gold
    ("grimoire:ed6_fog_4", 28, 128, "#dc9e68"),     # heartbeat 4 to the end: the golden primordial haze
    ("grimoire:ed6_fog_ash", 18, 96, "#b98a6c"),    # the concord's detonation: ash in the air
]


def build(pack):
    for ident, start, end, col in FOGS:
        pack.fog(ident, start=start, end=end, color=col)
