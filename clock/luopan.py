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
SPARK = (652, 38, 540, 62)  # x, y, width, height inside the strip

BADGE_H = 26                # the 18 px badges at desktop width
BADGE_GAP = 6
LINKS = [("linkedin", "https://www.linkedin.com/in/chen778", "LinkedIn"),
         ("handshake", "https://ucsd.joinhandshake.com/profiles/uwu7a3", "Handshake")]
LANGS = ["python", "typescript", "rust", "react", "tauri", "sqlite"]
ABOUT = "Desktop tools, web interfaces, and data experiments."
ORCA_FRACTION = 0.43        # Orca card width as a share of the row
ORCA_ASPECT = 1200 / 190

ROW_STRIP = 132
ROW_LINKS = 84
ROW_ABOUT = 90
ROW_ORCA = W * ORCA_FRACTION / ORCA_ASPECT
ROW_TAIL = 96

ASSETS = Path(__file__).resolve().parent.parent / "assets"

COLORS = (
    ".lp-dim{fill:#4a475f}.lp-lit{fill:#f1ecfa}.lp-txt{fill:#e6edf3}.lp-cap{fill:#999cb5}"
    "@media (prefers-color-scheme:light){.lp-dim{fill:#cfcadf}.lp-lit{fill:#2b2540}.lp-txt{fill:#1f2328}.lp-cap{fill:#6e7187}}"
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
    if guide:
        reach = (DIVIDER_X - 14 - cx) / s       # the faint radius stops short of the divider
        parts.append(f'<path d="M0 0H{reach:.0f}" stroke="#92d8cf" stroke-opacity=".12" stroke-width="1.2"/>')
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
        f'<path d="{d}" fill="none" stroke="url(#sp-line)" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{X(peak):.1f}" cy="{Y(counts[peak]):.1f}" r="2.6" fill="#b9a0e9"/>'
        f'<circle cx="{X(n - 1):.1f}" cy="{Y(counts[-1]):.1f}" r="2.2" fill="#92d8cf"/>'
        f'<text {mono} x="{x}" y="{y - 14}" font-size="10" letter-spacing="1.5">{total} PUBLIC CONTRIBUTIONS · {n} DAYS</text>'
        f'<text {mono} x="{x}" y="{y + h + 14}" font-size="9.5" letter-spacing="1">{day(days[0]["date"])}</text>'
        f'<text {mono} x="{x + w}" y="{y + h + 14}" font-size="9.5" letter-spacing="1" text-anchor="end">{day(days[-1]["date"])}</text>'
    )


# ------------------------------------------------------------------ badges

def _badge(name: str) -> tuple[float, str]:
    """An existing 20-unit badge SVG, scaled to the 18 px row height; returns (width, data URI)."""
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


def rows() -> list[tuple[str, float, float, float, float]]:
    """(name, x0, y0, width, height) of every clock tile, in canvas units."""
    links = sum(link_widths())
    y_links = ROW_STRIP
    y_about = y_links + ROW_LINKS
    y_orca = y_about + ROW_ABOUT
    y_tail = y_orca + ROW_ORCA
    orca_w = W * ORCA_FRACTION
    return [
        ("strip", 0, 0, W, ROW_STRIP),
        ("links", 0, y_links, W - links, ROW_LINKS),
        ("about", 0, y_about, W, ROW_ABOUT),
        ("orca-side", orca_w, y_orca, W - orca_w, ROW_ORCA),
        ("tail", 0, y_tail, W, ROW_TAIL),
    ]


def tiles(t: datetime, days: list[dict]) -> dict[str, str]:
    """Every live tile for one moment, keyed by file stem."""
    style = _keyframes(t)
    out = {}
    for name, x0, y0, w, h in rows():
        view = _view(x0, y0, w, h)
        if name == "strip":
            body = (_clock(t, view, highlight=True, guide=True)
                    + f'<path d="M{DIVIDER_X} 22V{h - 22}" stroke="#b9a0e9" stroke-opacity=".16"/>'
                    + sparkline(days, *SPARK))
            title = f"罗盘 clock in Pacific time, drawn {t:%Y-%m-%d %H:%M %Z}, beside {sum(d['count'] for d in days)} public contributions over {len(days)} days"
            out[name] = _svg(w, h, body, title=title, style=style)
        elif name == "about":
            body = (_clock(t, view, highlight=False, guide=False)
                    + f'<text class="lp-txt" x="0" y="30" font-size="15.2" font-family="{UI_FONT}">{escape(ABOUT)}</text>'
                    + _badge_row(LANGS, 0, 46))
            out[name] = _svg(w, h, body, title=ABOUT, style=style)
        elif name == "tail":
            # the clock fades out here, just above the toolbox
            defs = (f'<linearGradient id="fade" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{h:.1f}">'
                    '<stop stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
                    f'<mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="{w}" height="{h:.1f}">'
                    f'<rect width="{w}" height="{h:.1f}" fill="url(#fade)"/></mask>')
            body = f'<g mask="url(#m)">{_clock(t, view, highlight=False, guide=False)}</g>'
            out[name] = _svg(w, h, body, title="", style=style, defs=defs)
        else:
            out[name] = _svg(w, h, _clock(t, view, highlight=False, guide=False), title="", style=style)
    return out


def link_tile(name: str) -> str:
    """Static tile for one linked badge; the clock never reaches this far right, so it has no rings."""
    widths = dict(zip([n for n, _, _ in LINKS], link_widths()))
    label = {n: l for n, _, l in LINKS}[name]
    w = widths[name]
    bw, uri = _badge(name)
    body = f'<image x="0" y="14" width="{bw:.1f}" height="{BADGE_H}" href="{uri}"/>'
    return _svg(w, ROW_LINKS, body, title=label)


def readme_block(base: str) -> str:
    """The README paragraph that stacks the banner and every tile edge to edge."""
    def pct(width: float) -> str:   # truncate so a row never adds up to more than 100%
        return f"{math.floor(width / W * 1e6) / 1e4:g}%"
    (_, _, _, sw, _), (_, _, _, lw, _), _, (_, _, _, ow, _), _ = rows()
    link_w = link_widths()
    links = "".join(
        f'<a href="{url}"><img src="assets/link-{name}.svg" alt="{label}" width="{pct(w)}" align="top" /></a>'
        for (name, url, label), w in zip(LINKS, link_w)
    )
    return (
        '<p align="center">\n'
        '  <img src="assets/banner.svg?v=11" alt="s4lmon778 — an ASCII salmon and Mobius ribbon" width="100%" align="top" /><br>\n'
        f'  <img src="{base}/strip.svg" alt="罗盘 clock in Pacific time beside 90 days of public GitHub activity" width="100%" align="top" /><br>\n'
        f'  <img src="{base}/links.svg" alt="" width="{pct(lw)}" align="top" />{links}<br>\n'
        f'  <img src="{base}/about.svg" alt="{ABOUT} Python, TypeScript, Rust, React, Tauri, SQLite." width="100%" align="top" /><br>\n'
        f'  <a href="https://github.com/stablyai/orca"><img src="assets/orca-contributor.svg" alt="Contributor to Orca · 135k+ GitHub stars" width="{pct(W - ow)}" align="top" /></a>'
        f'<img src="{base}/orca-side.svg" alt="" width="{pct(ow)}" align="top" /><br>\n'
        f'  <img src="{base}/tail.svg" alt="" width="100%" align="top" />\n'
        '</p>\n'
    )
