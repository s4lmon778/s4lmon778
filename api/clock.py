"""Live 罗盘 clock for the GitHub profile, deployed as a Vercel function.

    GET /api/clock          the clock beside the right column
    GET /api/clock?wide=1   the full-width clock for narrow windows

Every request draws the clock for the current California time, and the response tells
GitHub's image proxy not to cache it, so each profile view starts at the right time and
the rings keep turning from there.
"""
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "clock"))
import luopan  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        wide = parse_qs(urlparse(self.path).query).get("wide", ["0"])[0] == "1"
        body = luopan.clock_svg(luopan.now(), wide=wide).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0")
        self.send_header("CDN-Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
