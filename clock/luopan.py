"""罗盘 clock: concentric rings of Chinese time labels, after the 时钟 web wallpaper.

Geometry follows the wallpaper: one ring every 80 units (month, date, weekday,
hour, minute, second), 19-unit labels reading outward, and the current value of
every ring lined up along the radius that points right.

The clock is the bottom layer of the profile. The banner sits on top of it, so
nothing is drawn there; below the banner the README is a stack of image tiles
("canvas" rows) that butt together with align="top", each carrying its own
slice of the same clock with the profile's text and badges drawn over it.

Everything is plain SVG + CSS, so it renders inside a GitHub README <img> with
no scripts. The bright "now" row is a second copy of the current labels seen
through a thin fixed slit; CSS keyframes keep the hour, minute and second rings
turning after the image loads. Labels that can never be seen in a tile are not
drawn at all.
"""
from __future__ import annotations

import base64
import math
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

TZ_NAME = "America/Los_Angeles"
SPACING, FONT = 80, 19
FONT_FAMILY = "'Microsoft YaHei','PingFang SC','Hiragino Sans GB','Noto Sans CJK SC','Noto Sans SC',sans-serif"
UI_FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Consolas,'Liberation Mono',monospace"

# ------------------------------------------------------------------ layout
# Canvas units: the README content width is 1200. y = 0 is the bottom edge of the banner.
W = 1200
CENTER = (-34, 66)          # clock centre: just past the left edge, about where the README box edge sits
SCALE = 1.12
DIVIDER_X = 620             # the bright row ends before this line; the sparkline gets everything to its right
SPARK = (652, 31, 540, 78)  # x, y, width, height inside the strip (clock untouched; strip stays 132 tall)

# Below the strip the page keeps the strip's two columns: text over the rings on the
# left, and links + the Orca card on the right, lined up with the sparkline's edges.
COL_X, COL_W = SPARK[0], SPARK[2]
BADGE_H = 26                # all six language badges fit on one row of the right column at this size
BADGE_GAP = 6
ABOUT_SIZE = 20             # description text, close to the clock's label size
LINKS = [("linkedin", "https://www.linkedin.com/in/chen778", "LinkedIn"),
         ("handshake", "https://ucsd.joinhandshake.com/profiles/uwu7a3", "Handshake")]
LANGS = ["python", "typescript", "rust", "react", "tauri", "sqlite"]
ABOUT = "Desktop tools, web interfaces, and data experiments."
ORCA_ASPECT = 1200 / 190

# Every row is at least ~82 units tall: on a phone that is still taller than one
# 24 px text line, which is what keeps the stacked images from opening gaps.
ROW_STRIP = 132
ROW_INTRO = COL_W / ORCA_ASPECT   # the Orca card
ROW_STACK = 84                    # description and language badges, under the card
ROW_TAIL = 84                     # LinkedIn and Handshake, under those

ASSETS = Path(__file__).resolve().parent.parent / "assets"

# One palette everywhere. Images can't see GitHub's theme (a light-mode phone viewing
# GitHub in dark would flip the colours), so the light text carries a thin dark halo
# instead: invisible on a dark page, and still readable on a white one.
HALO = "stroke:#0d1117;stroke-opacity:.85;stroke-linejoin:round;paint-order:stroke"
COLORS = (
    ".lp-dim{fill:#4a475f}.lp-cap{fill:#999cb5}"
    f".lp-lit{{fill:#f1ecfa;{HALO};stroke-width:2.6px}}.lp-txt{{fill:#e6edf3;{HALO};stroke-width:2.2px}}"
)

_CN = "零一二三四五六七八九十"


def _num(n: int) -> str:
    if n <= 10:
        return _CN[n]
    if n < 20:
        return "十" + (_CN[n % 10] if n % 10 else "")
    return _CN[n // 10] + "十" + (_CN[n % 10] if n % 10 else "")


RINGS = [
    ("month", [f"{_num(i + 1)}月" for i in range(12)]),
    ("day", [f"{_num(i + 1)}号" for i in range(31)]),
    ("week", ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]),
    ("hour", ["两点" if i == 2 else f"{_num(i)}点" for i in range(24)]),
    ("minute", [f"{_num(i)}分" for i in range(60)]),
    ("second", [f"{_num(i)}秒" for i in range(60)]),
]
MOVING = ("hour", "minute", "second")
OUTER = SPACING * len(RINGS) + 5 + FONT * 4.2


def now() -> datetime:
    return datetime.now(ZoneInfo(TZ_NAME))


def reading(t: datetime) -> dict[str, int]:
    return {
        "month": t.month - 1,
        "day": t.day - 1,
        "week": (t.weekday() + 1) % 7,      # Sunday first, as in the wallpaper
        "hour": t.hour,
        "minute": t.minute,
        "second": t.second,
    }


# ------------------------------------------------------------------ visibility

def _label_seen(radius: float, text: str, angle: float, view) -> bool:
    """Does a label at this final angle land inside the tile? view = (cx, cy, scale, width, height)."""
    cx, cy, s, w, h = view
    pad = FONT * s
    a = math.radians(angle)
    for k in range(5):
        rho = (radius + k / 4 * len(text) * FONT) * s
        x, y = cx + rho * math.cos(a), cy + rho * math.sin(a)
        if -pad <= x <= w + pad and -pad <= y <= h + pad:
            return True
    return False


def _annulus_seen(r_in: float, r_out: float, view) -> bool:
    """Does any part of a ring's band pass through the tile while it turns?"""
    cx, cy, s, w, h = view
    pad = FONT * s
    x0, y0, x1, y1 = -pad, -pad, w + pad, h + pad
    near = math.hypot(max(x0 - cx, 0, cx - x1), max(y0 - cy, 0, cy - y1))
    far = max(math.hypot(x - cx, y - cy) for x in (x0, x1) for y in (y0, y1))
    return near <= r_out * s and far >= r_in * s


# ------------------------------------------------------------------ rings

def _ring_markup(t: datetime, view, *, only_current: bool = False) -> str:
    """The rings visible in one tile, rotated so the current labels sit at angle 0.

    Turning rings keep every label once any part of their band can pass through
    the tile; still rings keep only the labels that land inside it (or just the
    current one for the bright copy).
    """
    r = reading(t)
    out = []
    for i, (key, labels) in enumerate(RINGS):
        n, step = len(labels), 360 / len(labels)
        radius = SPACING * (i + 1) + 5
        longest = max(len(x) for x in labels) * FONT
        if not _annulus_seen(radius, radius + longest, view):
            continue
        moving = key in MOVING
        if only_current:
            keep = range(n) if moving else [r[key]]
        elif moving:
            keep = range(n)
        else:
            keep = [j for j in range(n) if _label_seen(radius, labels[j], (j - r[key]) * step, view)]
        texts = "".join(f'<text x="{radius}" transform="rotate({j * step:.3f})">{escape(labels[j])}</text>' for j in keep)
        if not texts:
            continue
        if moving:
            out.append(f'<g class="lp-{key}">{texts}</g>')
        else:
            out.append(f'<g transform="rotate({-r[key] * step:.3f})">{texts}</g>')
    return "".join(out)


def _keyframes(t: datetime) -> str:
    """Hour/minute/second rings advance one label per tick with a 1 s ease, like the wallpaper.

    Each ring loops over its full cycle; a negative delay puts it at the current phase
    when the image loads. Every tile is drawn from the same moment, so they turn together.
    """
    css = []
    secs = t.second + t.microsecond / 1e6
    phase = {"second": secs, "minute": t.minute * 60 + secs, "hour": (t.hour * 60 + t.minute) * 60 + secs}
    for key, n, tick in (("second", 60, 1), ("minute", 60, 60), ("hour", 24, 3600)):
        period, step = n * tick, 360 / n
        frames = []
        for k in range(n):
            frames.append(f"{k * tick / period * 100:.5f}%{{transform:rotate({-k * step:.3f}deg)}}")
            if tick > 1:   # rest on label k, then turn to k+1 during the last second
                frames.append(f"{(k * tick + tick - 1) / period * 100:.5f}%{{transform:rotate({-k * step:.3f}deg)}}")
        frames.append("100%{transform:rotate(-360deg)}")
        css.append(f"@keyframes lp-{key}{{{''.join(frames)}}}")
        rest = -int(phase[key] // tick) * step
        css.append(
            f".lp-{key}{{transform-box:view-box;transform-origin:0 0;transform:rotate({rest:.3f}deg);"
            f"animation:lp-{key} {period}s ease infinite;animation-delay:-{phase[key]:.3f}s}}"
        )
    # still image for anyone who asks for reduced motion; it rests on the drawn time
    css.append("@media (prefers-reduced-motion:reduce){" + ",".join(f".lp-{k}" for k in MOVING) + "{animation:none}}")
    return "".join(css)


def _clock(t: datetime, view, *, highlight: bool, guide: bool) -> str:
    cx, cy, s = view[:3]
    parts = []
    rings = _ring_markup(t, view)
    if rings:
        parts.append(f'<g class="lp-dim">{rings}</g>')
    if highlight:
        parts.append(f'<g class="lp-lit" clip-path="url(#lp-slit)">{_ring_markup(t, view, only_current=True)}</g>')
    if not parts:
        return ""
    return (f'<g transform="translate({cx:.2f} {cy:.2f}) scale({s})" font-size="{FONT}" '
            f'font-family="{FONT_FAMILY}" dominant-baseline="central">{"".join(parts)}</g>')


SLIT = f'<clipPath id="lp-slit"><rect x="0" y="{-FONT * 0.66:.2f}" width="{OUTER:.0f}" height="{FONT * 1.32:.2f}"/></clipPath>'


# ------------------------------------------------------------------ 节气 and 时辰 seal at the hub
# A real 罗盘 also reads the season and the double-hour. They sit in a small seal at the
# compass hub, just left of the bright row, so the six wallpaper rings stay as they are.

SEAL = (5, 41, 49, 50)      # x, y, width, height inside the strip (ends just before the bright row)
SOLAR_TERMS = [  # name, C for the 21st-century day formula  [Y·0.2422 + C] − L
    ("小寒", 5.4055), ("大寒", 20.12), ("立春", 3.87), ("雨水", 18.73), ("惊蛰", 5.63), ("春分", 20.646),
    ("清明", 4.81), ("谷雨", 20.1), ("立夏", 5.52), ("小满", 21.04), ("芒种", 5.678), ("夏至", 21.37),
    ("小暑", 7.108), ("大暑", 22.83), ("立秋", 7.5), ("处暑", 23.13), ("白露", 7.646), ("秋分", 23.042),
    ("寒露", 8.318), ("霜降", 23.438), ("立冬", 7.438), ("小雪", 22.36), ("大雪", 7.18), ("冬至", 21.94),
]
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"


def solar_term(t: datetime) -> str:
    """The 节气 in effect on t's date (the latest one that has begun)."""
    y = t.year % 100
    current = SOLAR_TERMS[-1][0]          # early January still sits in last year's 冬至
    for i, (name, c) in enumerate(SOLAR_TERMS):
        month = i // 2 + 1
        leap = (y - 1) // 4 if month <= 2 else y // 4
        if (month, int(y * 0.2422 + c) - leap) <= (t.month, t.day):
            current = name
    return current


def shichen(t: datetime) -> str:
    """The 时辰 (double-hour): 子 is 23:00–01:00, 丑 01:00–03:00, and so on."""
    return BRANCHES[(t.hour + 1) // 2 % 12] + "时"


def _seal(t: datetime) -> str:
    x, y, w, h = SEAL
    mid = x + w / 2
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="#b9a0e9" fill-opacity=".06" '
        f'stroke="#b9a0e9" stroke-opacity=".5"/>'
        f'<g class="lp-lit" font-size="19.5" font-family="{FONT_FAMILY}" text-anchor="middle" dominant-baseline="central">'
        f'<text x="{mid}" y="{y + h * .28:.1f}">{solar_term(t)}</text>'
        f'<text x="{mid}" y="{y + h * .74:.1f}">{shichen(t)}</text></g>'
    )


# ------------------------------------------------------------------ bubbles
# A few bubbles leave the tank floor and rise through the rings until the banner covers
# them. Each one is described once in canvas units; every tile it crosses draws its own
# copy with the same timing, so they pass from tile to tile without a jump.

def _bubble_set() -> list[tuple[float, float, float, float, float, float]]:
    from random import Random
    rng = Random(778)
    out = []
    for x in (64, 132, 214, 287, 371, 446, 529, 588):
        out.append((x + rng.uniform(-14, 14), rng.uniform(1.7, 3.9), rng.uniform(17, 29),
                    rng.uniform(3, 7), rng.uniform(2.6, 4.4), rng.uniform(0, 60)))
    return out  # x, radius, rise seconds, sway, sway seconds, phase


BUBBLES = _bubble_set()


def _bubble_css(t: datetime, rise: float) -> str:
    ts = t.timestamp()
    css = []
    for i, (_, _, period, sway, sway_s, phase) in enumerate(BUBBLES):
        css.append(
            f"@keyframes bu{i}{{0%{{transform:translateY(0);opacity:0}}8%{{opacity:.75}}80%{{opacity:.55}}"
            f"100%{{transform:translateY(-{rise:.0f}px);opacity:0}}}}"
            f"@keyframes sw{i}{{from{{transform:translateX(-{sway:.1f}px)}}to{{transform:translateX({sway:.1f}px)}}}}"
            f".bu{i}{{animation:bu{i} {period:.2f}s linear infinite;animation-delay:-{(ts + phase) % period:.2f}s}}"
            f".sw{i}{{animation:sw{i} {sway_s:.2f}s ease-in-out infinite alternate;"
            f"animation-delay:-{(ts + phase) % (2 * sway_s):.2f}s}}"
        )
    css.append("@media (prefers-reduced-motion:reduce){" + ",".join(f".bu{i},.sw{i}" for i in range(len(BUBBLES)))
               + "{animation:none;opacity:0}}")
    return "".join(css)


def _bubbles(x0: float, y0: float, w: float, start_y: float) -> str:
    out = []
    for i, (x, r, *_rest) in enumerate(BUBBLES):
        if x + r + 8 < x0 or x - r - 8 > x0 + w:
            continue
        out.append(
            f'<g transform="translate({x - x0:.1f} {start_y - y0:.1f})"><g class="bu{i}"><circle class="sw{i}" r="{r:.1f}" '
            f'fill="#92d8cf" fill-opacity=".08" stroke="#92d8cf" stroke-opacity=".75" stroke-width=".9"/></g></g>'
        )
    return "".join(out)


# ------------------------------------------------------------------ tank floor
# The banner is the top of the tank; the floor closes it at the bottom. It fades in from
# nothing at its top edge to solid at the bottom, so the rings run into it and are
# gradually caught. A small frog hops along it inside the same fade, so each leap
# carries it up out of the solid floor and back down.

FLOOR_FADE = '<linearGradient id="fl-fade" x2="0" y2="1"><stop stop-color="#fff" stop-opacity="0"/>' \
             '<stop offset=".28" stop-color="#fff" stop-opacity=".3"/><stop offset=".52" stop-color="#fff"/></linearGradient>'


def _floor(w: float, h: float) -> str:
    from random import Random
    rng = Random(1778)
    sediment = "".join(
        f'<circle cx="{rng.uniform(10, w - 10):.1f}" cy="{rng.uniform(h * .62, h - 7):.1f}" '
        f'r="{rng.uniform(.5, 1.6):.1f}" fill="{rng.choice(["#b9a0e9", "#92d8cf", "#cfd9ff"])}" opacity="{rng.uniform(.12, .42):.2f}"/>'
        for _ in range(60)
    )
    wave = lambda y: f"M-80 {y:.0f}Q170 {y - 14:.0f} 410 {y - 2:.0f}T910 {y:.0f}T1320 {y - 10:.0f}"
    return (
        '<defs><linearGradient id="fl-bg" x2="1" y2="1"><stop stop-color="#0c101d"/><stop offset=".55" stop-color="#111528"/>'
        '<stop offset="1" stop-color="#17132a"/></linearGradient>'
        '<radialGradient id="fl-mint"><stop stop-color="#58dbca" stop-opacity=".16"/><stop offset="1" stop-color="#58dbca" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="fl-violet"><stop stop-color="#8760e4" stop-opacity=".2"/><stop offset="1" stop-color="#8760e4" stop-opacity="0"/></radialGradient>'
        '<linearGradient id="fl-line"><stop stop-color="#a890ee" stop-opacity="0"/><stop offset=".5" stop-color="#a890ee" stop-opacity=".7"/>'
        '<stop offset="1" stop-color="#79d7d0" stop-opacity="0"/></linearGradient>'
        f'<clipPath id="fl-card"><rect width="{w}" height="{h}" rx="24"/></clipPath></defs>'
        '<style>@keyframes fl-drift{to{stroke-dashoffset:-100}}.fl-drift{animation:fl-drift 8s linear infinite}'
        '@media (prefers-reduced-motion:reduce){.fl-drift{animation:none}}</style>'
        f'<g clip-path="url(#fl-card)"><rect width="{w}" height="{h}" fill="url(#fl-bg)"/>'
        f'<ellipse cx="330" cy="{h + 10}" rx="520" ry="{h * .7:.0f}" fill="url(#fl-mint)"/>'
        f'<ellipse cx="930" cy="{h * .55:.0f}" rx="380" ry="{h * .6:.0f}" fill="url(#fl-violet)"/>'
        f'<g fill="none" stroke="url(#fl-line)"><path d="{wave(h * .66)}" opacity=".32"/><path d="{wave(h * .8)}" opacity=".2"/>'
        f'<path class="fl-drift" d="{wave(h * .66)}" stroke="#97e8dc" stroke-dasharray="3 22" opacity=".22"/></g>'
        f"{sediment}</g>"
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="23.5" fill="none" stroke="#a99bce" stroke-opacity=".14"/>'
    )


# Three chunky pixel-art toads, side view, facing right: round bodies, big glossy eyes,
# lighter bellies. The sprites are built in layers from shapes in toad_sprites.py.
from toad_sprites import PALETTES as TOAD_PALETTES, SPOTS as TOAD_SPOTS, build as _toad_rows  # noqa: E402

TOAD_PIXEL = 1.6      # canvas units per sprite pixel
TOADS = [("olive", 11), ("brown", 23), ("rust", 37)]  # name, seed for its hopping habits


def _sprite(rows: list[str], pal: dict[str, str]) -> str:
    """Pixel rows as crisp rects (runs merged), centred on x = 0 with the feet on y = 0."""
    width = max(len(r) for r in rows)
    p = TOAD_PIXEL
    x0, y0 = -width * p / 2, -len(rows) * p
    out = []
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            ch = row[x]
            run = 1
            while x + run < len(row) and row[x + run] == ch:
                run += 1
            if ch != ".":
                out.append(f'<rect x="{x0 + x * p:.2f}" y="{y0 + y * p:.2f}" width="{run * p + .05:.2f}" height="{p + .05:.2f}" fill="{pal[ch]}"/>')
            x += run
    return f'<g shape-rendering="crispEdges">{"".join(out)}</g>'


def _toad_art(name: str) -> tuple[str, str]:
    pal, spots = TOAD_PALETTES[name], TOAD_SPOTS[name]
    return _sprite(_toad_rows("sit", spots), pal), _sprite(_toad_rows("leap", spots), pal)


def _toad_track(seed: int, left: float, right: float):
    """A random but repeatable round trip: hop lengths, pauses, airtime and height all vary."""
    from random import Random
    rng = Random(seed)
    pace = rng.uniform(.8, 1.25)          # this toad's overall speed
    xs, ys, face, pose = [], [], [], []
    clock, x = 0.0, left
    for d in (1, -1):
        face.append((clock, d))
        goal = right if d > 0 else left
        while abs(goal - x) > 1:
            dist = min(rng.uniform(60, 150), abs(goal - x))
            rest = rng.choice([rng.uniform(.4, 1.1), rng.uniform(1.1, 2.6), rng.uniform(2.6, 5.5)])
            air = (.38 + dist / 300) / pace
            height = rng.uniform(44, 82) * (.6 + dist / 300)
            xs.append((clock, x)); ys.append((clock, 0, "rest")); pose.append((clock, 0))
            clock += rest
            xs.append((clock, x)); ys.append((clock, 0, "up")); pose.append((clock, 1))
            ys.append((clock + air / 2, -height, "down"))
            clock += air
            x += d * dist
        xs.append((clock, x)); ys.append((clock, 0, "rest")); pose.append((clock, 0))
        clock += rng.uniform(1.5, 4.5)    # sit a while at the end before turning round
    return clock, xs, ys, face, pose, rng.uniform(0, clock)


def _toads(t: datetime, w: float, ground: float) -> tuple[str, str]:
    """Markup and CSS for the three toads hopping along the floor, each in step with real time."""
    left, right = 50.0, w - 50.0
    ease = {"up": "cubic-bezier(.2,.62,.42,1)", "down": "cubic-bezier(.58,0,.8,.38)", "rest": "linear"}
    css, markup = [], []
    for name, seed in TOADS:
        # each toad turns round at its own spots, so they never pile up at the ends
        period, xs, ys, face, pose, phase = _toad_track(seed, left + (seed % 5) * 14, right - (seed % 7) * 11)
        pct = lambda s: f"{s / period * 100:.4f}%"
        k = f"td-{name}"
        css.append(
            f"@keyframes {k}-x{{{''.join(f'{pct(s)}{{transform:translateX({v:.1f}px)}}' for s, v in xs)}100%{{transform:translateX({left:.1f}px)}}}}"
            f"@keyframes {k}-y{{{''.join(f'{pct(s)}{{transform:translateY({v:.1f}px);animation-timing-function:{ease[e]}}}' for s, v, e in ys)}100%{{transform:translateY(0)}}}}"
            f"@keyframes {k}-f{{{''.join(f'{pct(s)}{{transform:scaleX({v})}}' for s, v in face)}100%{{transform:scaleX(1)}}}}"
            f"@keyframes {k}-l{{{''.join(f'{pct(s)}{{opacity:{v}}}' for s, v in pose)}100%{{opacity:0}}}}"
            f"@keyframes {k}-s{{{''.join(f'{pct(s)}{{opacity:{1 - v}}}' for s, v in pose)}100%{{opacity:1}}}}"
        )
        common = f"{period:.3f}s infinite;animation-delay:{-((t.timestamp() + phase) % period):.3f}s"
        css.append(
            f".{k}-x{{animation:{k}-x linear {common}}}.{k}-y{{animation:{k}-y {common}}}"
            f".{k}-f{{transform-box:view-box;transform-origin:0 0;animation:{k}-f step-end {common}}}"
            f".{k}-l{{animation:{k}-l step-end {common}}}.{k}-s{{animation:{k}-s step-end {common}}}"
        )
        sit, leap = _toad_art(name)
        rest_x = left + (right - left) * (seed % 7) / 7      # where it sits if motion is turned off
        markup.append(
            f'<g transform="translate(0 {ground})"><g class="{k}-x" style="transform:translateX({rest_x:.1f}px)">'
            f'<g class="{k}-y"><g class="{k}-f"><g class="{k}-s">{sit}</g><g class="{k}-l" opacity="0">{leap}</g></g></g></g></g>'
        )
    names = ",".join(f".td-{n}-{p}" for n, *_ in TOADS for p in "xyfls")
    css.append(f"@media (prefers-reduced-motion:reduce){{{names}{{animation:none}}}}")
    return "".join(markup), "".join(css)


# ------------------------------------------------------------------ sparkline

def _smooth(points: list[tuple[float, float]], floor: float) -> str:
    d = f"M{points[0][0]:.1f},{points[0][1]:.1f}"
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i else points[i]
        p1, p2 = points[i], points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, min(floor, p1[1] + (p2[1] - p0[1]) / 6))
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, min(floor, p2[1] - (p3[1] - p1[1]) / 6))
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def sparkline(days: list[dict], x: float, y: float, w: float, h: float) -> str:
    counts = [d["count"] for d in days]
    total, top, n = sum(counts), max(max(counts), 1), len(counts)
    X = lambda i: x + i * (w / (n - 1))
    Y = lambda v: y + h - v / top * h
    d = _smooth([(X(i), Y(v)) for i, v in enumerate(counts)], y + h)
    peak = counts.index(max(counts))
    mono = f'font-family="{MONO}" class="lp-cap"'
    day = lambda s: datetime.fromisoformat(s).strftime("%b %d").upper().replace(" 0", " ")
    return (
        '<defs><linearGradient id="sp-line"><stop stop-color="#92d8cf"/><stop offset="1" stop-color="#b9a0e9"/></linearGradient>'
        '<linearGradient id="sp-area" x2="0" y2="1"><stop stop-color="#b9a0e9" stop-opacity=".28"/>'
        '<stop offset="1" stop-color="#b9a0e9" stop-opacity="0"/></linearGradient></defs>'
        f'<path d="M{x} {y + h + .5:.1f}H{x + w}" stroke="#b9a0e9" stroke-opacity=".16"/>'
        f'<path d="{d} L{x + w:.1f},{y + h:.1f} L{x:.1f},{y + h:.1f} Z" fill="url(#sp-area)"/>'
        f'<path d="{d}" fill="none" stroke="url(#sp-line)" stroke-width="1.9" stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{X(peak):.1f}" cy="{Y(counts[peak]):.1f}" r="3" fill="#b9a0e9"/>'
        f'<circle cx="{X(n - 1):.1f}" cy="{Y(counts[-1]):.1f}" r="2.6" fill="#92d8cf"/>'
        f'<text {mono} x="{x}" y="{y - 13}" font-size="11" letter-spacing="1.5">{total} PUBLIC CONTRIBUTIONS · {n} DAYS</text>'
        f'<text {mono} x="{x}" y="{y + h + 15}" font-size="10.5" letter-spacing="1">{day(days[0]["date"])}</text>'
        f'<text {mono} x="{x + w}" y="{y + h + 15}" font-size="10.5" letter-spacing="1" text-anchor="end">{day(days[-1]["date"])}</text>'
    )


# ------------------------------------------------------------------ badges

def _badge(name: str) -> tuple[float, str]:
    """An existing 20-unit badge SVG, scaled to BADGE_H; returns (width, data URI)."""
    src = (ASSETS / f"badge-{name}.svg").read_text(encoding="utf-8")
    w = float(src.split('width="', 1)[1].split('"', 1)[0]) * BADGE_H / 20
    return w, "data:image/svg+xml;base64," + base64.b64encode(src.encode()).decode()


def _badge_row(names: list[str], x: float, y: float) -> str:
    out = []
    for name in names:
        w, uri = _badge(name)
        out.append(f'<image x="{x:.1f}" y="{y}" width="{w:.1f}" height="{BADGE_H}" href="{uri}"/>')
        x += w + BADGE_GAP
    return "".join(out)


def link_widths() -> list[float]:
    """Widths of the linked badge tiles (each badge plus the gap after it, except the last)."""
    widths = [_badge(name)[0] for name, _, _ in LINKS]
    return [w + (BADGE_GAP if i < len(widths) - 1 else 0) for i, w in enumerate(widths)]


# ------------------------------------------------------------------ tiles

def _svg(w: float, h: float, body: str, *, title: str, style: str = "", defs: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.2f}" height="{h:.2f}" viewBox="0 0 {w:.2f} {h:.2f}" role="img">'
        f"<title>{escape(title)}</title><style>{COLORS}{style}</style><defs>{SLIT}{defs}</defs>{body}</svg>\n"
    )


def _view(x0: float, y0: float, w: float, h: float):
    return (CENTER[0] - x0, CENTER[1] - y0, SCALE, w, h)


Y_INTRO = ROW_STRIP
Y_STACK = Y_INTRO + ROW_INTRO
Y_TAIL = Y_STACK + ROW_STACK
Y_FLOOR = Y_TAIL + ROW_TAIL
ROW_FLOOR = 172
TOAD_GROUND = ROW_FLOOR - 14      # the toads sit in the solid lower part of the floor
BUBBLE_START = Y_FLOOR + ROW_FLOOR - 18   # bubbles leave from the bottom of the floor...
BUBBLE_RISE = BUBBLE_START + 12           # ...and rise until the banner covers them
ABOUT_BASELINE = 30         # description text in the about tile
LANGS_Y = 44                # language badges under it
LINKS_Y = 8                 # link badges near the top of the last row, just under the language badges


def rows() -> list[tuple[str, float, float, float, float]]:
    """(name, x0, y0, width, height) of every live tile, in canvas units.

    Rings only reach the left column (the clock never passes x = 600). The right column
    is the linked badges and the Orca card; the floor closes the tank across the full width.
    """
    return [
        ("strip", 0, 0, W, ROW_STRIP),
        ("intro", 0, Y_INTRO, COL_X, ROW_INTRO),
        ("stack", 0, Y_STACK, COL_X, ROW_STACK),
        ("tail", 0, Y_TAIL, COL_X, ROW_TAIL),
        ("floor", 0, Y_FLOOR, W, ROW_FLOOR),
    ]


def tiles(t: datetime, days: list[dict]) -> dict[str, str]:
    """Every live tile for one moment, keyed by file stem."""
    style = _keyframes(t) + _bubble_css(t, BUBBLE_RISE)
    out = {}
    for name, x0, y0, w, h in rows():
        view = _view(x0, y0, w, h)
        rings = _clock(t, view, highlight=name == "strip", guide=name == "strip")
        bubbles = _bubbles(x0, y0, w, BUBBLE_START)
        if name == "strip":
            body = (rings + bubbles + _seal(t) + f'<path d="M{DIVIDER_X} 22V{h - 22}" stroke="#b9a0e9" stroke-opacity=".16"/>'
                    + sparkline(days, *SPARK))
            title = (f"罗盘 clock in Pacific time, drawn {t:%Y-%m-%d %H:%M %Z} ({solar_term(t)}, {shichen(t)}), "
                     f"beside {sum(d['count'] for d in days)} public contributions over {len(days)} days")
            out[name] = _svg(w, h, body, title=title, style=style)
        elif name in ("intro", "stack"):
            out[name] = _svg(w, h, rings + bubbles, title="", style=style)
        elif name == "tail":
            out[name] = _svg(w, h, rings + bubbles, title="", style=style)
        else:
            # rings run on underneath; the floor and the frog fade in over them, top to bottom
            frog, frog_css = _toads(t, w, TOAD_GROUND)
            defs = (FLOOR_FADE + f'<mask id="fl-mask" maskUnits="userSpaceOnUse" x="-40" y="-40" width="{w + 80}" height="{h + 80}">'
                    f'<rect width="{w}" height="{h}" fill="url(#fl-fade)"/></mask>')
            body = rings + f'<g mask="url(#fl-mask)">{_floor(w, h)}{frog}</g>' + bubbles
            out[name] = _svg(w, h, body, title="", style=style + frog_css, defs=defs)
    return out


def link_tile(name: str) -> str:
    """Static tile for one linked badge in the right column (no rings reach it)."""
    widths = dict(zip([n for n, _, _ in LINKS], link_widths()))
    label = {n: l for n, _, l in LINKS}[name]
    bw, uri = _badge(name)
    body = f'<image x="0" y="{LINKS_Y}" width="{bw:.1f}" height="{BADGE_H}" href="{uri}"/>'
    return _svg(widths[name], ROW_TAIL, body, title=label)


def about_tile() -> str:
    """Static right-column tile under the Orca card: the description and the language badges."""
    body = (f'<text class="lp-txt" x="0" y="{ABOUT_BASELINE}" font-size="{ABOUT_SIZE}" font-family="{UI_FONT}">{escape(ABOUT)}</text>'
            + _badge_row(LANGS, 0, LANGS_Y))
    return _svg(COL_W, ROW_STACK, body, title=ABOUT + " Python, TypeScript, Rust, React, Tauri, SQLite.")


def readme_block(base: str) -> str:
    """The README paragraph that stacks the banner and every tile edge to edge."""
    def pct(width: float) -> str:   # truncate so a row never adds up to more than 100%
        return f"{math.floor(width / W * 1e6) / 1e4:g}%"
    links = "".join(
        f'<a href="{url}"><img src="assets/link-{name}.svg" alt="{label}" width="{pct(w)}" align="top" /></a>'
        for (name, url, label), w in zip(LINKS, link_widths())
    )
    col = pct(COL_X)
    return (
        '<p>\n'
        '  <img src="assets/banner.svg?v=11" alt="s4lmon778 — an ASCII salmon and Mobius ribbon" width="100%" align="top" /><br>\n'
        f'  <img src="{base}/strip.svg" alt="罗盘 clock in Pacific time beside 90 days of public GitHub activity" width="100%" align="top" /><br>\n'
        f'  <img src="{base}/intro.svg" alt="" width="{col}" align="top" />'
        f'<a href="https://github.com/stablyai/orca"><img src="assets/orca-contributor.svg" alt="Contributor to Orca · 135k+ GitHub stars" width="{pct(COL_W)}" align="top" /></a><br>\n'
        f'  <img src="{base}/stack.svg" alt="" width="{col}" align="top" />'
        f'<img src="assets/about.svg" alt="{ABOUT} Python, TypeScript, Rust, React, Tauri, SQLite." width="{pct(COL_W)}" align="top" /><br>\n'
        f'  <img src="{base}/tail.svg" alt="" width="{col}" align="top" />{links}<br>\n'
        f'  <img src="{base}/floor.svg" alt="" width="100%" align="top" />\n'
        '</p>\n'
    )
