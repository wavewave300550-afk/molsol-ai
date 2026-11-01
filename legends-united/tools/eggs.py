"""
Spawn-egg icons and names for Clash of Legends, plus the pack icon.

Each egg carries a portrait of its boss (cut out of the boss's own preview render), the boss's
colours and a rim in its add-on colour, so every egg can be told apart at a glance.
"""
import math
import os
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
TEAM_RIM = {"dim11": (176, 92, 255), "fb": (255, 196, 64), "legends": (255, 255, 255)}
TEAM_TAG = {"dim11": "§d11th Dimension", "fb": "§6Final Boss", "legends": "§bLegendary"}

# id: (preview sheet, panels, panel index, top crop, bottom crop, base colour, accent, display name)
BOSSES = {
    "dim11:archon": ("eleventh-addon/docs/images/archon.png", 3, 0, 40, 4, (26, 11, 51), (196, 91, 255), "AEON-7, the Archon"),
    "dim11:sovereign": ("eleventh-addon/docs/images/sovereign.png", 3, 0, 40, 4, (8, 28, 52), (90, 200, 255), "The M5 Sovereign"),
    "dim11:observer": ("eleventh-addon/docs/images/observer.png", 3, 0, 40, 4, (40, 30, 6), (255, 210, 90), "The Ophanim of the 11th Axis"),
    "fb:void_emperor": ("final-bosses/docs/images/void_emperor.png", 3, 0, 52, 4, (22, 8, 40), (170, 80, 255), "The Void Emperor"),
    "fb:titan": ("final-bosses/docs/images/titan.png", 3, 0, 52, 4, (60, 40, 18), (240, 190, 110), "The Titan of Creation"),
    "fb:devouring_star": ("final-bosses/docs/images/devouring_star.png", 3, 0, 52, 4, (50, 14, 4), (255, 140, 30), "The Devouring Star"),
    "fb:world_parasite": ("final-bosses/docs/images/world_parasite.png", 3, 0, 52, 4, (20, 36, 12), (130, 210, 70), "The World Parasite"),
    "fb:choir": ("final-bosses/docs/images/choir.png", 3, 0, 52, 4, (40, 40, 52), (235, 235, 255), "The Choir of Mirrors"),
    "legends:taotie": ("legendary-remaster/docs/preview_taotie.png", 2, 0, 44, 30, (59, 38, 19), (255, 122, 32), "Taotie, the Devouring Maw"),
    "legends:nidhogg": ("legendary-remaster/docs/preview_nidhogg.png", 2, 0, 44, 30, (29, 38, 25), (69, 232, 58), "Níðhöggr, the World-Tree Gnawer"),
    "legends:hanuman": ("legendary-remaster/docs/preview_hanuman.png", 2, 0, 44, 30, (120, 20, 30), (255, 210, 80), "Hanuman, Son of the Wind"),
    "legends:alicorn": ("legendary-remaster/docs/preview_alicorn.png", 2, 0, 44, 30, (60, 40, 110), (210, 180, 255), "The Alicorn of Dawn"),
    "legends:tenko": ("legendary-remaster/docs/preview_tenko.png", 2, 0, 44, 30, (20, 50, 100), (90, 180, 255), "Tenko, the Ten-Tailed Fox"),
    "legends:logos": ("legendary-remaster/docs/preview_logos.png", 2, 0, 44, 30, (90, 70, 20), (255, 210, 90), "The Word of God"),
}


def key(eid):
    return eid.replace(":", "_")


def cutout(eid):
    """Boss portrait with the dark preview background flood-filled away, cropped to the model."""
    path, panels, idx, top, bot, *_ = BOSSES[eid]
    im = Image.open(os.path.join(REPO, path)).convert("RGBA")
    pw = im.width // panels
    im = im.crop((idx * pw, top, (idx + 1) * pw, im.height - bot))
    small = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
    a = np.asarray(small).astype(np.int32)
    h, w = a.shape[:2]
    bg = np.median(np.concatenate([a[0, :, :3], a[-1, :, :3], a[:, 0, :3], a[:, -1, :3]]), axis=0)
    near = (np.abs(a[:, :, :3] - bg).sum(axis=2) < 46) | (a[:, :, :3].max(axis=2) < 34)
    seen = np.zeros((h, w), bool)
    q = deque([(y, x) for y in range(h) for x in (0, w - 1)] + [(y, x) for x in range(w) for y in (0, h - 1)])
    while q:
        y, x = q.popleft()
        if y < 0 or x < 0 or y >= h or x >= w or seen[y, x] or not near[y, x]:
            continue
        seen[y, x] = True
        q.extend(((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)))
    out = a.copy()
    out[seen, 3] = 0
    # thin leftovers (ground line, labels): drop rows/cols with very few solid pixels at the edges
    img = Image.fromarray(out.astype(np.uint8), "RGBA")
    al = np.asarray(img)[:, :, 3] > 0
    ys, xs = np.nonzero(al)
    if len(xs):
        # trim stray specks, labels and ground lines: keep the core 97% of the model's pixels
        x0, x1 = np.percentile(xs, [1.5, 98.5])
        y0, y1 = np.percentile(ys, [1.0, 99.5])
        img = img.crop((int(x0), int(y0), int(x1) + 1, int(y1) + 1))
    return img


def egg_mask(n):
    m = np.zeros((n, n), np.float32)
    for yy in range(n):
        y = (yy + 0.5) / n * 2 - 1                      # -1 top .. 1 bottom
        hw = 0.80 * math.sqrt(max(0.0, 1 - y * y)) * (1 + 0.16 * y)
        for xx in range(n):
            x = (xx + 0.5) / n * 2 - 1
            m[yy, xx] = 1.0 if abs(x) <= hw * 0.98 else 0.0
    return m


def egg_icon(eid, n=64, portrait=None):
    *_, base, accent, _name = BOSSES[eid]
    team = eid.split(":")[0]
    S = n * 4                                          # supersample then downscale
    mask = egg_mask(S)
    yy = np.linspace(0, 1, S)[:, None]
    col = np.zeros((S, S, 4), np.float32)
    for c in range(3):
        col[:, :, c] = base[c] * (1 - yy * 0.35) + accent[c] * (yy ** 2) * 0.55
    rng = np.random.default_rng(abs(hash(eid)) % 2 ** 32)
    spots = rng.random((S // 32, S // 32)) > 0.93
    spots = np.kron(spots, np.ones((32, 32)))
    for c in range(3):
        col[:, :, c] = np.where(spots > 0, col[:, :, c] * 0.8 + accent[c] * 0.2, col[:, :, c])
    col[:, :, 3] = mask * 255
    egg = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), "RGBA")
    portrait = portrait or cutout(eid)
    box = int(S * 0.86)
    k = min(box / portrait.width, box * 0.82 / portrait.height)
    pr = portrait.resize((max(1, int(portrait.width * k)), max(1, int(portrait.height * k))), Image.LANCZOS)
    layer = Image.new("RGBA", (S, S))
    layer.alpha_composite(pr, ((S - pr.width) // 2, int(S * 0.56 - pr.height / 2)))
    la = np.asarray(layer).copy()
    la[:, :, 3] = (la[:, :, 3] * mask).astype(np.uint8)
    egg.alpha_composite(Image.fromarray(la, "RGBA"))
    # rim in the add-on colour, then a shine
    edge = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(13))
    inner = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(13))
    ring = np.clip(np.asarray(edge).astype(np.int32) - np.asarray(inner).astype(np.int32), 0, 255).astype(np.uint8)
    rim = Image.new("RGBA", (S, S), TEAM_RIM[team] + (255,))
    rim.putalpha(Image.fromarray(ring))
    egg.alpha_composite(rim)
    return egg.resize((n, n), Image.LANCZOS)


def lang_lines():
    return [f"item.spawn_egg.entity.{eid}.name=§l{BOSSES[eid][7]}§r §7· {TEAM_TAG[eid.split(':')[0]]}" for eid in BOSSES]


def write_eggs(rp):
    """Egg textures into the RP; returns {item_texture key: path} and the portraits."""
    out = {}
    portraits = {}
    d = os.path.join(rp, "textures", "items", "clash")
    os.makedirs(d, exist_ok=True)
    for eid in BOSSES:
        portraits[eid] = cutout(eid)
        egg_icon(eid, 64, portraits[eid]).save(os.path.join(d, f"egg_{key(eid)}.png"))
        out[f"clash_egg_{key(eid)}"] = {"textures": f"textures/items/clash/egg_{key(eid)}"}
    return out, portraits


def font(size):
    for f in ("/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def pack_icon(portraits, path, size=256):
    """Clash of Legends icon: three champions charging at each other over a burst of light."""
    S = size * 2
    y = np.linspace(0, 1, S)[:, None]
    x = np.linspace(-1, 1, S)[None, :]
    r = np.sqrt(x ** 2 + ((y - 0.5) * 2) ** 2)
    bg = np.zeros((S, S, 4), np.float32)
    bg[:, :, 0] = 30 + 120 * np.exp(-r * 2.4)
    bg[:, :, 1] = 10 + 70 * np.exp(-r * 2.8)
    bg[:, :, 2] = 40 + 40 * np.exp(-r * 2.0)
    bg[:, :, 3] = 255
    ang = np.arctan2((y - 0.5) * 2, x)
    rays = (np.cos(ang * 12) * 0.5 + 0.5) ** 6 * np.exp(-r * 1.5) * 120
    for c, k in zip(range(3), (1.0, 0.8, 0.5)):
        bg[:, :, c] += rays * k
    img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGBA")
    picks = [("dim11:archon", (0.03, 0.16), 0.62, True), ("fb:titan", (0.52, 0.20), 0.58, False), ("legends:taotie", (0.21, 0.40), 0.66, False)]
    for eid, (px, py), sc, flip in picks:
        p = portraits[eid].copy()
        if flip:
            p = p.transpose(Image.FLIP_LEFT_RIGHT)
        k = S * sc / max(p.width, p.height)
        p = p.resize((int(p.width * k), int(p.height * k)), Image.LANCZOS)
        glow = Image.new("RGBA", p.size, BOSSES[eid][6] + (0,))
        glow.putalpha(p.split()[3].filter(ImageFilter.GaussianBlur(10)))
        pos = (int(S * px), int(S * py))
        img.alpha_composite(glow, pos)
        img.alpha_composite(p, pos)
    d = ImageDraw.Draw(img)
    f1 = font(int(S * 0.13))
    for txt, yy, f in (("CLASH OF", 0.025, font(int(S * 0.085))), ("LEGENDS", 0.835, f1)):
        w = d.textlength(txt, font=f)
        xx = (S - w) / 2
        for ox, oy in ((-4, 0), (4, 0), (0, -4), (0, 4), (3, 3), (-3, 3)):
            d.text((xx + ox, S * yy + oy), txt, font=f, fill=(20, 6, 10, 255))
        d.text((xx, S * yy), txt, font=f, fill=(255, 214, 90, 255))
    img.resize((size, size), Image.LANCZOS).save(path)


def showcase(portraits, path):
    """docs image: every egg with its name and add-on."""
    cols, cell = 7, 170
    rows = math.ceil(len(BOSSES) / cols)
    img = Image.new("RGBA", (cols * cell, rows * (cell + 30) + 10), (16, 12, 24, 255))
    d = ImageDraw.Draw(img)
    f = font(13)
    for i, eid in enumerate(BOSSES):
        cx, cy = (i % cols) * cell, (i // cols) * (cell + 30)
        egg = egg_icon(eid, 128, portraits[eid])
        img.alpha_composite(egg, (cx + (cell - 128) // 2, cy + 8))
        name = BOSSES[eid][7]
        for k, line in enumerate(_wrap(d, name, f, cell - 8)[:2]):
            w = d.textlength(line, font=f)
            d.text((cx + (cell - w) / 2, cy + 140 + k * 15), line, font=f, fill=(235, 230, 245, 255))
        tag = {"dim11": "11th Dimension", "fb": "Final Boss", "legends": "Legendary"}[eid.split(":")[0]]
        w = d.textlength(tag, font=f)
        d.text((cx + (cell - w) / 2, cy + 172), tag, font=f, fill=TEAM_RIM[eid.split(":")[0]] + (255,))
    img.save(path)


def _wrap(d, text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines
