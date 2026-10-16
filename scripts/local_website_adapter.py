#!/usr/bin/env python3
"""Serve the existing static site and inject one local-only Manager demo."""

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
WIDGET = REPO_ROOT / "scripts" / "local_website_widget.js"
ALLOWED_API_PATHS = {
    "/api/website/catalog",
    "/api/website/pricing",
    "/api/website/bookings",
}


def make_handler(website_root: Path, backend_url: str, demo_page: str):
    demo_page = str(Path(demo_page))

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(website_root), **kwargs)

        def log_message(self, _format, *_args):
            return

        def _proxy(self):
            path = urlsplit(self.path).path
            if path not in ALLOWED_API_PATHS:
                self.send_error(404)
                return
            if self.command not in {"GET", "POST"}:
                self.send_error(405)
                return
            body = None
            headers = {"Accept": "application/json"}
            if self.command == "POST":
                length = int(self.headers.get("Content-Length", "0"))
                if length > 32768:
                    self.send_error(413)
                    return
                body = self.rfile.read(length)
                headers["Content-Type"] = self.headers.get("Content-Type", "application/json")
            if self.headers.get("Idempotency-Key"):
                headers["Idempotency-Key"] = self.headers["Idempotency-Key"]
            try:
                request = Request(backend_url.rstrip("/") + path, data=body, headers=headers, method=self.command)
                with urlopen(request, timeout=15) as response:
                    payload, code = response.read(), response.status
            except HTTPError as exc:
                payload, code = exc.read(), exc.code
            except (URLError, TimeoutError):
                payload, code = json.dumps({"detail": "Local Manager API is unavailable"}).encode(), 502
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if urlsplit(self.path).path.startswith("/api/"):
                return self._proxy()
            if urlsplit(self.path).path == "/__local/website-widget.js":
                payload = WIDGET.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/javascript; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            return super().do_GET()

        def do_POST(self):
            return self._proxy()

        def send_head(self):
            path = unquote(urlsplit(self.path).path).lstrip("/")
            if path == demo_page:
                source = (website_root / path).resolve()
                if not source.is_relative_to(website_root.resolve()):
                    self.send_error(404)
                    return None
                html = source.read_text(encoding="utf-8")
                injection = '''<section id="tct-local-integration" aria-label="Local ThaiCulture Manager quote and booking"><div id="tct-local-booking-widget"></div></section><script defer src="/__local/website-widget.js"></script>'''
                html = html.replace("</main>", injection + "</main>", 1)
                payload = html.encode("utf-8")
                from io import BytesIO
                response = BytesIO(payload)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                return response
            return super().send_head()

    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--website-root", type=Path, required=True)
    parser.add_argument("--backend-url", default="http://127.0.0.1:18082")
    parser.add_argument("--demo-page", default="en/ayutthaya-5-sights-tour.html")
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args()
    if args.backend_url.split(":", 2)[1] not in {"//127.0.0.1", "//localhost"}:
        parser.error("local adapter only accepts a loopback Manager API URL")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.website_root.resolve(), args.backend_url, args.demo_page))
    print(f"Local website adapter listening on http://127.0.0.1:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
