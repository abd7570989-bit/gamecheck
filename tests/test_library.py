import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from gamecheck import library as lib


class FakeLibraryServer:
    """Serves a body on http://127.0.0.1 and records the request headers."""

    def __init__(self, body: bytes, status=200):
        outer = self
        self.requests = []

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                outer.requests.append({"path": self.path, "headers": dict(self.headers)})
                self.send_response(status)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/library.json"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def serve():
    servers = []

    def start(body, status=200):
        s = FakeLibraryServer(body if isinstance(body, bytes) else json.dumps(body).encode(), status)
        servers.append(s)
        return s
    yield start
    for s in servers:
        s.close()


def newer(library, version=2, extra_game=True):
    lib_new = json.loads(json.dumps(library))
    lib_new["library_version"] = version
    if extra_game:
        lib_new["games"].append({"id": "new-game", "name": "New Game",
                                 "minimum": {"cpu": ["Intel Core i5-4460"], "gpu": [], "ram_gb": 8, "storage_gb": 10}})
    return lib_new


def test_bundled_library_valid(library):
    assert lib.validate(library) is library
    loaded, source = lib.load()
    assert source == "bundled"


def test_update_downloads_and_persists_for_offline_use(serve, library):
    s = serve(newer(library))
    r = lib.update(library["library_version"], url=s.url, allow_insecure_http=True)
    assert r == {"status": "updated", "library_version": 2, "games": len(library["games"]) + 1}
    loaded, source = lib.load()   # later, offline: no network involved
    assert source == "downloaded"
    assert loaded["games"][-1]["id"] == "new-game"


def test_update_request_carries_no_identifiers(serve, library):
    s = serve(newer(library))
    lib.update(1, url=s.url, allow_insecure_http=True)
    req = s.requests[0]
    assert req["path"] == "/library.json"
    assert "Cookie" not in req["headers"]
    assert req["headers"]["User-Agent"].startswith("GameCheck/")


def test_up_to_date(serve, library):
    s = serve(newer(library, version=1))
    assert lib.update(1, url=s.url, allow_insecure_http=True)["status"] == "up_to_date"
    assert not lib.cached_library_path().exists()


@pytest.mark.parametrize("body", [b"not json", b"[]", json.dumps({"schema_version": 99}).encode(),
                                  json.dumps({"schema_version": 1, "library_version": 5, "cpus": [], "gpus": [],
                                              "games": []}).encode()])
def test_invalid_download_changes_nothing(serve, library, body):
    s = serve(body)
    assert lib.update(1, url=s.url, allow_insecure_http=True)["status"] == "invalid"
    assert not lib.cached_library_path().exists()
    assert lib.load()[1] == "bundled"


def test_http_error_is_offline_and_changes_nothing(serve):
    s = serve(b"oops", status=500)
    assert lib.update(1, url=s.url, allow_insecure_http=True)["status"] == "offline"


def test_no_connection(library):
    r = lib.update(1, url="http://127.0.0.1:9/library.json", timeout=2, allow_insecure_http=True)
    assert r["status"] == "offline"
    assert lib.load()[1] == "bundled"


def test_https_required_by_default():
    assert lib.update(1, url="http://example.com/library.json")["status"] == "invalid"


def test_not_configured(monkeypatch):
    monkeypatch.setattr(lib, "DEFAULT_LIBRARY_URL", "")
    assert lib.update(1)["status"] == "not_configured"


def test_settings_url_overrides_default(serve, library):
    s = serve(newer(library))
    lib.save_settings({"library_url": s.url})
    assert lib.library_url() == s.url


def test_too_large_rejected(serve, monkeypatch):
    monkeypatch.setattr(lib, "MAX_DOWNLOAD_BYTES", 100)
    s = serve(b"x" * 500)
    assert lib.update(1, url=s.url, allow_insecure_http=True)["status"] == "invalid"


def test_corrupt_cache_falls_back_to_bundled():
    lib.cached_library_path().write_text("{broken", encoding="utf-8")
    assert lib.load()[1] == "bundled"


def test_older_cache_ignored_after_program_upgrade(library):
    # The bundled library of a newer program version may be newer than an old downloaded copy.
    lib.cached_library_path().write_text(json.dumps(newer(library, version=library["library_version"])),
                                         encoding="utf-8")
    assert lib.load()[1] == "bundled"


def test_validate_rejects_duplicate_ids(library):
    bad = newer(library)
    bad["games"].append(dict(bad["games"][0]))
    with pytest.raises(lib.LibraryError):
        lib.validate(bad)
