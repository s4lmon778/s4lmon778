"""The full toolbox: every tool as a logo badge, grouped by category.

    python clock/toolbox.py      # (re)fetch the badges into assets/tools/

Badges come from Shields in the same style as the language badges. Tools whose brand
isn't in the Simple Icons set get a small generic icon drawn here instead of an
imitation of someone's logo.
"""
from __future__ import annotations

import base64
import subprocess
import urllib.parse
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "assets" / "tools"
ACCENTS = ["91d9ce", "b9a0e9", "d2bddf"]   # mint, lilac, soft pink: the existing badge colours

# Generic 24×24 icons for tools without a Simple Icons logo. {c} is the accent colour.
GLYPHS = {
    "terminal": '<rect x="2" y="4" width="20" height="16" rx="2.5" fill="none" stroke="{c}" stroke-width="2"/>'
                '<path d="M6 9l4 3-4 3M12 15h6" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    "database": '<ellipse cx="12" cy="5.5" rx="8" ry="3" fill="none" stroke="{c}" stroke-width="2"/>'
                '<path d="M4 5.5v13c0 1.7 3.6 3 8 3s8-1.3 8-3v-13M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" fill="none" stroke="{c}" stroke-width="2"/>',
    "store": '<path d="M12 2l9 5v10l-9 5-9-5V7z M3 7l9 5 9-5M12 12v10" fill="none" stroke="{c}" stroke-width="2" stroke-linejoin="round"/>',
    "chart": '<path d="M3 21h18" stroke="{c}" stroke-width="2" stroke-linecap="round"/>'
             '<rect x="5" y="11" width="3.5" height="8" rx="1" fill="{c}"/><rect x="10.3" y="6" width="3.5" height="13" rx="1" fill="{c}"/>'
             '<rect x="15.6" y="9" width="3.5" height="10" rx="1" fill="{c}"/>',
    "server": '<rect x="3" y="3" width="18" height="7.5" rx="2" fill="none" stroke="{c}" stroke-width="2"/>'
              '<rect x="3" y="13.5" width="18" height="7.5" rx="2" fill="none" stroke="{c}" stroke-width="2"/>'
              '<circle cx="7" cy="6.75" r="1.3" fill="{c}"/><circle cx="7" cy="17.25" r="1.3" fill="{c}"/>',
    "exchange": '<path d="M4 8h14l-3.5-3.5M20 16H6l3.5 3.5" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    "image": '<rect x="2.5" y="4" width="19" height="16" rx="2.5" fill="none" stroke="{c}" stroke-width="2"/>'
             '<circle cx="8.5" cy="9.5" r="2" fill="{c}"/><path d="M3.5 18l6-6 4 4 3-3 4.5 4.5" fill="none" stroke="{c}" stroke-width="2" stroke-linejoin="round"/>',
    "wave": '<path d="M2 12h2M6 8v8M10 4v16M14 7v10M18 10v4M22 12h-2" fill="none" stroke="{c}" stroke-width="2.2" stroke-linecap="round"/>',
    "nodes": '<circle cx="6" cy="12" r="3.2" fill="none" stroke="{c}" stroke-width="2"/><circle cx="18" cy="6" r="3.2" fill="none" stroke="{c}" stroke-width="2"/>'
             '<circle cx="18" cy="18" r="3.2" fill="none" stroke="{c}" stroke-width="2"/><path d="M8.8 10.5l6.4-3.2M8.8 13.5l6.4 3.2" stroke="{c}" stroke-width="2"/>',
    "plug": '<path d="M9 2v5M15 2v5M6 7h12v4a6 6 0 0 1-12 0zM12 17v5" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    "play": '<circle cx="12" cy="12" r="9.5" fill="none" stroke="{c}" stroke-width="2"/><path d="M10 8l6 4-6 4z" fill="{c}"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="{c}" stroke-width="2.2"/>'
              '<path d="M15.5 15.5L21 21M8 10.5h5" stroke="{c}" stroke-width="2.2" stroke-linecap="round"/>',
    "brackets": '<path d="M8 6l-6 6 6 6M16 6l6 6-6 6M14 4l-4 16" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    "spark": '<path d="M12 2l2.3 6.4L21 11l-6.7 2.6L12 20l-2.3-6.4L3 11l6.7-2.6z" fill="{c}"/>',
    "chat": '<path d="M4 4h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H10l-5 4v-4H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z" fill="none" stroke="{c}" stroke-width="2" stroke-linejoin="round"/>'
            '<circle cx="8" cy="11" r="1.3" fill="{c}"/><circle cx="12" cy="11" r="1.3" fill="{c}"/><circle cx="16" cy="11" r="1.3" fill="{c}"/>',
}

# (category, [(name, simple-icons slug or "glyph:<name>")])
CATALOG = [
    ("LANGUAGES & FORMATS", [
        ("Python", "python"), ("TypeScript", "typescript"), ("JavaScript", "javascript"), ("Rust", "rust"),
        ("SQL", "glyph:database"), ("HTML", "html5"), ("CSS", "css"), ("PowerShell", "glyph:terminal"),
        ("Batch", "glyph:terminal"), ("Markdown", "markdown"), ("JSON", "json"), ("YAML", "yaml"), ("SVG", "svg")]),
    ("INTERFACES & DESKTOP", [
        ("React", "react"), ("React Router", "reactrouter"), ("Tauri", "tauri"), ("Electron", "electron"),
        ("Vite", "vite"), ("Tailwind CSS", "tailwindcss"), ("Zustand", "glyph:store"), ("Recharts", "glyph:chart"),
        ("Lucide", "lucide"), ("Canvas", "html5"), ("Tkinter", "python")]),
    ("DATA, SERVERS & MEDIA", [
        ("SQLite", "sqlite"), ("pandas", "pandas"), ("NumPy", "numpy"), ("Streamlit", "streamlit"),
        ("FastAPI", "fastapi"), ("Uvicorn", "glyph:server"), ("HTTPX", "glyph:exchange"), ("Pillow", "glyph:image"),
        ("FFmpeg", "ffmpeg"), ("faster-whisper", "glyph:wave"), ("WebRTC", "webrtc"), ("PeerJS", "glyph:nodes"),
        ("WebSockets", "glyph:plug"), ("sql.js", "sqlite")]),
    ("BUILD, TEST & SHIP", [
        ("Git", "git"), ("GitHub", "github"), ("GitHub CLI", "github"), ("GitHub Actions", "githubactions"),
        ("Node.js", "nodedotjs"), ("npm", "npm"), ("Bun", "bun"), ("pnpm", "pnpm"), ("uv", "uv"),
        ("Playwright", "glyph:play"), ("Vitest", "vitest"), ("Testing Library", "testinglibrary"), ("unittest", "python"),
        ("ESLint", "eslint"), ("Prettier", "prettier"), ("Oxlint", "oxc"), ("CodeQL", "glyph:search"),
        ("Dependabot", "dependabot")]),
    ("EDITORS & AI COMPANIONS", [
        ("VS Code", "glyph:brackets"), ("Codex", "glyph:spark"), ("Claude Code", "claude"),
        ("ChatGPT", "glyph:chat"), ("DeepSeek", "deepseek"), ("Muse Spark", "meta")]),
]


def file_for(name: str) -> Path:
    stem = "".join(ch if ch.isalnum() else "-" for ch in name.lower()).strip("-")
    return TOOLS_DIR / f"{stem}.svg"


def _url(name: str, logo: str, accent: str) -> str:
    label = urllib.parse.quote(name.replace("-", "--").replace("_", "__"))
    if logo.startswith("glyph:"):
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{GLYPHS[logo[6:]].format(c="#" + accent)}</svg>'
        logo_q = urllib.parse.quote("data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode(), safe="")
        return f"https://img.shields.io/badge/-{label}-171c29?style=flat&logo={logo_q}"
    return f"https://img.shields.io/badge/-{label}-171c29?style=flat&logo={logo}&logoColor={accent}"


def fetch_all() -> None:
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    i = 0
    for _, tools in CATALOG:
        for name, logo in tools:
            url = _url(name, logo, ACCENTS[i % len(ACCENTS)])
            svg = subprocess.run(["curl", "-sf", url], capture_output=True, check=True).stdout.decode("utf-8")
            if "<image" not in svg:
                raise SystemExit(f"no logo came back for {name}")
            file_for(name).write_text(svg + "\n", encoding="utf-8", newline="\n")
            i += 1
    print(f"wrote {i} tool badges to {TOOLS_DIR}")


if __name__ == "__main__":
    fetch_all()
