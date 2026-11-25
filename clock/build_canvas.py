"""Draw the live clock tiles that sit under the banner.

    python clock/build_canvas.py OUTDIR      # live tiles: strip, intro, stack, tail, floor
    python clock/build_canvas.py --static    # the right-column tiles in assets/ (no clock reaches them)

Activity comes from the anonymous public contribution calendar (the same view any
visitor sees), so private activity never appears. If the request fails, the last
saved snapshot is used instead.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import luopan  # noqa: E402

USER = "s4lmon778"
DAYS = 90
SNAPSHOT = Path(__file__).resolve().parent / "activity-snapshot.json"


def fetch_public_activity(end) -> list[dict]:
    start = end - timedelta(days=DAYS - 1)
    url = f"https://github.com/users/{USER}/contributions?from={start:%Y-%m-%d}&to={end:%Y-%m-%d}"
    req = urllib.request.Request(url, headers={"User-Agent": "profile-clock", "Accept": "text/html"})
    html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
    cells = {m["id"]: m["date"] for m in re.finditer(r'<td[^>]*?data-date="(?P<date>[\d-]+)"[^>]*?id="(?P<id>[^"]+)"', html)}
    counts = {}
    for m in re.finditer(r'<tool-tip[^>]*?for="(?P<for>[^"]+)"[^>]*>(?P<text>[^<]*)', html):
        date = cells.get(m["for"])
        if date:
            hit = re.match(r"\s*(\d+) contribution", m["text"])
            counts[date] = int(hit.group(1)) if hit else 0
    days = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(DAYS)]
    if not all(d in counts for d in days):
        raise ValueError("calendar response is missing days")
    return [{"date": d, "count": counts[d]} for d in days]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    if sys.argv[1:] == ["--static"]:
        for name, _, _ in luopan.LINKS:
            write(luopan.ASSETS / f"link-{name}.svg", luopan.link_tile(name))
        write(luopan.ASSETS / "about.svg", luopan.about_tile())
        write(luopan.ASSETS / "spacer.svg", luopan.spacer())
        for name, svg in luopan.toolbox_tiles():
            write(luopan.ASSETS / name, svg)
        print("wrote linked badge tiles and the about tile")
        return
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "canvas")
    t = luopan.now()
    try:
        days = fetch_public_activity(t.date())
        SNAPSHOT.write_text(json.dumps(days), encoding="utf-8")
    except Exception as exc:  # network hiccup or markup change: keep the last good public snapshot
        print(f"activity fetch failed ({exc}); using snapshot", file=sys.stderr)
        days = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    version = luopan._code_version()
    for name, svg in luopan.tiles(t, days).items():
        # each drawing-code version gets its own folder: a design change is a new address the
        # file CDN has never cached (it ignores query strings); root copies stay for old links
        write(out / version / f"{name}.svg", svg)
        write(out / f"{name}.svg", svg)
    print(f"wrote tiles to {out} at {t:%Y-%m-%d %H:%M:%S %Z}, {sum(d['count'] for d in days)} public contributions / {len(days)} days")


if __name__ == "__main__":
    main()
