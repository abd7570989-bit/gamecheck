"""Local web interface. Listens on 127.0.0.1 only; nothing is reachable from the network.

Every API call must carry the per-run token embedded in the page, and the Host header
must be our own address, so other websites open in the browser cannot drive it.
"""

import json
import secrets
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import __version__, library as library_mod
from .compare import Analyzer
from .paths import web_dir
from .scanner import scan


class AppState:
    def __init__(self, scan_func=scan):
        self._scan_func = scan_func
        self.lock = threading.Lock()
        self.library, self.source = library_mod.load()
        self.analyzer = Analyzer(self.library)
        self.system = None

    def get_system(self, refresh=False):
        with self.lock:
            if self.system is None or refresh:
                self.system = self._scan_func()
            return self.system

    def me(self):
        settings = library_mod.load_settings()
        return self.analyzer.describe_system(self.get_system(), settings.get("cpu_override"),
                                             settings.get("gpu_override"))

    def reload_library(self):
        with self.lock:
            self.library, self.source = library_mod.load()
            self.analyzer = Analyzer(self.library)

    def library_info(self):
        return {"library_version": self.library["library_version"], "updated": self.library.get("updated"),
                "source": self.source, "games": len(self.library["games"]),
                "update_configured": bool(library_mod.library_url())}


class Handler(BaseHTTPRequestHandler):
    server_version = f"GameCheck/{__version__}"
    state: AppState = None
    token: str = ""

    def log_message(self, fmt, *args):  # keep the console quiet; nothing is logged to disk
        pass

    def _send(self, status, body: bytes, content_type: str):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
                         "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, status=HTTPStatus.OK):
        self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _host_ok(self):
        host, port = self.server.server_address[:2]
        return self.headers.get("Host") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def _authorised(self):
        return secrets.compare_digest(self.headers.get("X-GameCheck-Token", ""), self.token)

    def _guard(self, api: bool) -> bool:
        if not self._host_ok():
            self._send(HTTPStatus.FORBIDDEN, b"forbidden", "text/plain")
            return False
        if api and not self._authorised():
            self._json({"error": "unauthorised"}, HTTPStatus.FORBIDDEN)
            return False
        return True

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            if not self._guard(api=False):
                return
            html = (web_dir() / "index.html").read_text(encoding="utf-8")
            html = html.replace("__GAMECHECK_TOKEN__", self.token).replace("__GAMECHECK_VERSION__", __version__)
            self._send(HTTPStatus.OK, html.encode("utf-8"), "text/html; charset=utf-8")
            return
        if not url.path.startswith("/api/"):
            self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")
            return
        if not self._guard(api=True):
            return
        query = parse_qs(url.query)
        st = self.state
        if url.path == "/api/system":
            system = st.get_system(refresh=query.get("refresh") == ["1"])
            self._json({"system": system, "resolved": st.me()})
        elif url.path == "/api/results":
            self._json({"results": st.analyzer.check_all(st.me()), "library": st.library_info()})
        elif url.path == "/api/hardware":
            self._json({"cpus": sorted(e.name for e in st.analyzer.cpus.entries),
                        "gpus": sorted(e.name for e in st.analyzer.gpus.entries),
                        "settings": {k: v for k, v in library_mod.load_settings().items()
                                     if k in ("cpu_override", "gpu_override")}})
        else:
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > 64 * 1024:
            return None
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
            return data if isinstance(data, dict) else None
        except ValueError:
            return None

    def do_POST(self):
        if not self._guard(api=True):
            return
        path = urlparse(self.path).path
        st = self.state
        if path == "/api/update-library":
            result = library_mod.update(st.library["library_version"])
            if result["status"] == "updated":
                st.reload_library()
            self._json(dict(result, library=st.library_info()))
        elif path == "/api/overrides":
            body = self._body()
            if body is None:
                self._json({"error": "bad request"}, HTTPStatus.BAD_REQUEST)
                return
            settings = library_mod.load_settings()
            for key, table in (("cpu_override", st.analyzer.cpus), ("gpu_override", st.analyzer.gpus)):
                if key in body:
                    value = body[key]
                    if value and table.by_name(value):
                        settings[key] = value
                    else:
                        settings.pop(key, None)
            library_mod.save_settings(settings)
            self._json({"ok": True})
        elif path == "/api/shutdown":
            self._json({"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        else:
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)


def make_server(port=0, state=None):
    """Create (but do not start) the server. Port 0 picks a free port."""
    handler = type("BoundHandler", (Handler,), {"state": state or AppState(), "token": secrets.token_urlsafe(24)})
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    server.daemon_threads = True
    return server
