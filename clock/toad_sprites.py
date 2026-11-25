"""Toad sprites for the tank floor, drawn the way pixel artists build them: in layers.

Body and head form the base silhouette; belly, gland ridge, haunch, feet, arm, ear disc
and eye are painted on top as their own shapes. Every layer gets an outline where it
meets empty space and a dark crease where it overlaps the layer beneath, a highlight
band along its top edge and a shade band along its bottom edge. Raised warts, separated
toes, a nostril, chin crease and belly speckles are added last.

Shapes are described on a base grid and sampled at DETAIL× resolution.

Keys: o outline · d crease · h highlight · b body · s shade · p spot · c belly · q belly
      shade · k pupil · w eye shine · e eye rim
"""
import math
from random import Random

DETAIL = 1.22


def _ell(cx, cy, rx, ry, rot=0.0):
    c, s = math.cos(rot), math.sin(rot)

    def inside(x, y):
        dx, dy = x - cx, y - cy
        dx, dy = dx * c + dy * s, -dx * s + dy * c
        return (dx / rx) ** 2 + (dy / ry) ** 2 <= 1
    return inside


def _cap(ax, ay, bx, by, r):
    def inside(x, y):
        vx, vy = bx - ax, by - ay
        t = max(0, min(1, ((x - ax) * vx + (y - ay) * vy) / (vx * vx + vy * vy)))
        return (x - ax - t * vx) ** 2 + (y - ay - t * vy) ** 2 <= r * r
    return inside


def _union(*fs):
    return lambda x, y: any(f(x, y) for f in fs)


def _shapes(pose):
    """Shapes for one pose on the base grid (y grows down, ground at the bottom)."""
    if pose == "sit":
        W, H = 33, 25
        r = 0.0
        body = _union(_ell(13.5, 15.2, 11.2, 8.6), _ell(22.5, 12.2, 7.2, 6.1))
        belly = _ell(21.6, 19.2, 7.6, 5.2)
        gland = _ell(16.2, 9.0, 4.2, 1.7, -0.12)
        haunch = _ell(8.6, 18.0, 6.0, 5.0)
        feet = [_union(_ell(11.4, 23.0, 5.6, 1.5), _ell(16.4, 23.2, 1.3, .9)),
                _union(_cap(24.6, 17.4, 25.2, 21.6, 1.45), _ell(26.6, 23.0, 2.5, 1.1))]
        toes = [((15.6, 23.4), (16.9, 23.4)), ((26.4, 23.5), (27.7, 23.5))]   # separator lines at the tips
        eye = (21.8, 6.6, 3.7)
        ear = (18.6, 10.6, 1.5)
        mouth = [(23.6, 13.3), (29.6, 12.2)]
        chin = [(22.0, 14.6), (26.5, 14.2)]
        nostril = (28.6, 8.6)
    else:
        W, H = 42, 27
        r = -0.32
        body = _union(_ell(18.5, 13.6, 11.2, 8.4, r), _ell(27.6, 8.4, 7.0, 5.9, r))
        belly = _ell(26.2, 14.4, 7.4, 5.0, r)
        gland = _ell(21.0, 6.6, 4.0, 1.6, r - .12)
        haunch = _ell(12.6, 15.0, 5.4, 4.6, r)
        feet = [_union(_cap(11.5, 17.0, 5.0, 21.0, 2.6), _cap(5.0, 21.0, 2.2, 24.2, 1.8), _ell(1.9, 25.0, 3.0, 1.2)),
                _union(_cap(29.5, 13.8, 34.0, 18.5, 1.4), _ell(35.2, 19.2, 2.0, 1.0))]
        toes = [((0.0, 25.2), (1.4, 25.2)), ((35.0, 19.6), (36.3, 19.6))]
        eye = (26.4, 4.9, 3.6)
        ear = (23.4, 8.6, 1.4)
        mouth = [(28.4, 10.4), (33.8, 7.8)]
        chin = [(30.4, 10.6), (32.2, 9.8)]      # short: the leaping belly is in the way
        nostril = (33.2, 4.6)
    return W, H, r, body, belly, gland, haunch, feet, toes, eye, ear, mouth, chin, nostril


def _line(a, b):
    (ax, ay), (bx, by) = a, b
    n = int(max(abs(bx - ax), abs(by - ay)) * DETAIL) + 1
    return {(int((ax + (bx - ax) * i / n) * DETAIL), int((ay + (by - ay) * i / n) * DETAIL)) for i in range(n + 1)}


def build(pose: str, spots: bool) -> list[str]:
    W0, H0, rot, body, belly, gland, haunch, feet, toes, eye, ear, mouth, chin, nostril = _shapes(pose)
    S = DETAIL
    W, H = int(W0 * S) + 2, int(H0 * S) + 2
    ex, ey, er = eye
    eye_in = lambda x, y: (x - ex) ** 2 + (y - ey) ** 2 <= er * er
    grid = [["." for _ in range(W)] for _ in range(H)]
    layer = [[None] * W for _ in range(H)]
    c = lambda x, y: ((x + .5) / S, (y + .5) / S)       # pixel centre → base coordinates
    band = 2 * S / S                                   # band thickness in base units

    def paint(name, inside, tone):
        for y in range(H):
            for x in range(W):
                if inside(*c(x, y)):
                    grid[y][x] = tone(x, y, inside)
                    layer[y][x] = name

    def banded(base="b", top="h", bottom="s"):
        def tone(x, y, inside):
            bx, by = c(x, y)
            if not inside(bx, by - band) or not inside(bx - .6, by - band):
                return top
            if not inside(bx, by + band) or not inside(bx + .6, by + band):
                return bottom
            return base
        return tone

    paint("body", body, banded())
    for y in range(H):                                 # darker underside on the back half
        for x in range(W):
            bx, by = c(x, y)
            if layer[y][x] == "body" and grid[y][x] == "b" and by > H0 * .6 and bx < W0 * .45:
                grid[y][x] = "s"

    # raised warts across the back: a dark bump with a lit pixel above it
    rng = Random(778 + (1 if pose == "leap" else 0))
    for _ in range(26):
        bx, by = rng.uniform(3, W0 * .72), rng.uniform(4, H0 * .62)
        x, y = int(bx * S), int(by * S)
        if 1 <= y < H and 0 <= x < W and layer[y][x] == "body" and grid[y][x] in "bh" and not eye_in(bx, by):
            grid[y][x] = "p" if spots and rng.random() < .45 else "s"
            if grid[y - 1][x] in "b":
                grid[y - 1][x] = "h"
    if spots:                                          # a few larger dark blotches
        for _ in range(6):
            bx, by = rng.uniform(4, W0 * .7), rng.uniform(6, H0 * .6)
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                x, y = int(bx * S) + dx, int(by * S) + dy
                if 0 <= y < H and 0 <= x < W and layer[y][x] == "body" and grid[y][x] in "bhs":
                    grid[y][x] = "p"

    paint("gland", lambda x, y: gland(x, y) and body(x, y), banded("b", "h", "s"))
    paint("belly", lambda x, y: belly(x, y) and body(x, y),
          lambda x, y, inside: "q" if not inside(*c(x, y + 2)) or not inside(*c(x - 2, y)) else "c")
    for y in range(H):                                 # speckles where the belly meets the flank
        for x in range(W):
            if layer[y][x] == "belly" and grid[y][x] == "c" and (x + y) % 4 == 0:
                bx, by = c(x, y)
                if not belly(bx - 3, by) or not belly(bx, by + 3):
                    grid[y][x] = "q"
    paint("haunch", haunch, banded())
    for i, f in enumerate(feet):
        paint(f"foot{i}", f, banded("s"))

    # ear disc (tympanum) behind the eye
    tx, ty, tr = ear
    for y in range(H):
        for x in range(W):
            bx, by = c(x, y)
            d = math.hypot(bx - tx, by - ty)
            if d <= tr and layer[y][x] in ("body", "gland"):
                grid[y][x] = "d" if d > tr - .75 else "s"

    for a, b in (mouth, chin):
        for x, y in _line(a, b):
            if 0 <= y < H and 0 <= x < W and grid[y][x] != ".":
                grid[y][x] = "d"
    nx, ny = int(nostril[0] * S), int(nostril[1] * S)
    if grid[ny][nx] != ".":
        grid[ny][nx] = "d"

    # eye: rim, big pupil, shine, a brow line above
    for y in range(H):
        for x in range(W):
            bx, by = c(x, y)
            if eye_in(bx, by):
                d = math.hypot(bx - ex - .35, by - ey - .2)
                grid[y][x] = "k" if d <= er - 1.75 else "e"
                layer[y][x] = "eye"
    for sx, sy in ((1.1, -.9), (1.9, -.1)):
        x, y = int((ex + sx) * S), int((ey + sy) * S)
        if 0 <= y < H and 0 <= x < W and grid[y][x] == "k":
            grid[y][x] = "w"
            break

    # outlines and creases
    out = [row[:] for row in grid]
    for y in range(H):
        for x in range(W):
            if grid[y][x] == ".":
                continue
            me = layer[y][x]
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx_, ny_ = x + dx, y + dy
                if not (0 <= nx_ < W and 0 <= ny_ < H) or grid[ny_][nx_] == ".":
                    out[y][x] = "o"
                    break
                other = layer[ny_][nx_]
                if me == "eye" and other != "eye":
                    out[y][x] = "o"
                elif me in ("haunch", "foot0", "foot1") and other not in (me, "eye") and dy >= 0:
                    out[y][x] = "d"
                elif me == "gland" and other == "body" and dy == 1:
                    out[y][x] = "d"
    # toes: dark separators across the tips of the feet and hands
    for a, b in toes:
        for x, y in _line(a, b):
            if 0 <= y < H and 0 <= x < W and out[y][x] not in ".o" and (x % 2 == 0):
                out[y][x] = "d"

    rows = ["".join(r) for r in out]
    while set(rows[0]) == {"."}:
        rows.pop(0)
    while set(rows[-1]) == {"."}:
        rows.pop()
    left = min(len(r) - len(r.lstrip(".")) for r in rows)
    right = min(len(r) - len(r.rstrip(".")) for r in rows)
    return [r[left:len(r) - right] for r in rows]


PALETTES = {
    "olive": {"o": "#2c3410", "d": "#4b5418", "h": "#c6cf5e", "b": "#99a636", "s": "#6d7825", "p": "#84902d",
              "c": "#ecda5c", "q": "#c8b03a", "k": "#141510", "w": "#f6f6ee", "e": "#b5bf4c"},
    "brown": {"o": "#2e1d0e", "d": "#4a3019", "h": "#c19867", "b": "#93683d", "s": "#684628", "p": "#5a3b20",
              "c": "#dcc8a2", "q": "#b9a37d", "k": "#16110d", "w": "#f6f0e6", "e": "#b08757"},
    "rust": {"o": "#3c160d", "d": "#622d1c", "h": "#e39670", "b": "#bd6544", "s": "#8c452c", "p": "#9d5137",
             "c": "#f6cdab", "q": "#dba788", "k": "#1a110f", "w": "#f9f0e9", "e": "#d27e5a"},
}
SPOTS = {"olive": False, "brown": True, "rust": True}
