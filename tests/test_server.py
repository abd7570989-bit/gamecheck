import json
import threading
import urllib.error
import urllib.request

import pytest

from conftest import make_system
from gamecheck import library as lib
from gamecheck.server import AppState, make_server


@pytest.fixture
def server():
    state = AppState(scan_func=lambda: make_system(gpus=[("Weird GPU 9000", None)]))
    srv = make_server(0, state)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    port = srv.server_address[1]
    srv.base = f"http://127.0.0.1:{port}"
    srv.tok = srv.RequestHandlerClass.token
    yield srv
    srv.shutdown()
    srv.server_close()


def call(srv, path, method="GET", body=None, token=True, host=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-GameCheck-Token"] = srv.tok
    if host:
        headers["Host"] = host
    req = urllib.request.Request(srv.base + path, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if r.headers.get_content_type() == "application/json" else raw.decode())
    except urllib.error.HTTPError as e:
        return e.code, None


def test_binds_to_localhost_only(server):
    assert server.server_address[0] == "127.0.0.1"


def test_index_has_token_and_is_arabic(server):
    status, html = call(server, "/", token=False)
    assert status == 200
    assert server.tok in html and "__GAMECHECK_TOKEN__" not in html
    assert 'dir="rtl"' in html and "مواصفات جهازك" in html


def test_api_requires_token(server):
    assert call(server, "/api/system", token=False)[0] == 403
    assert call(server, "/api/shutdown", method="POST", body={}, token=False)[0] == 403


def test_foreign_host_rejected(server):
    # Blocks DNS-rebinding: a page on evil.example resolving to 127.0.0.1.
    assert call(server, "/", token=False, host="evil.example")[0] == 403
    assert call(server, "/api/system", host="evil.example")[0] == 403


def test_system_and_results(server):
    status, data = call(server, "/api/system")
    assert status == 200 and data["resolved"]["cpu_model"] == "Intel Core i5-4460"
    status, data = call(server, "/api/results")
    assert status == 200 and len(data["results"]) == data["library"]["games"]
    assert data["library"]["source"] == "bundled"


def test_override_round_trip(server):
    _, data = call(server, "/api/results")
    elden = next(r for r in data["results"] if r["id"] == "forza-horizon-5")
    assert elden["overall"] == "unknown"   # GPU not recognised
    status, _ = call(server, "/api/overrides", "POST", {"gpu_override": "NVIDIA GeForce GTX 1070"})
    assert status == 200
    assert lib.load_settings()["gpu_override"] == "NVIDIA GeForce GTX 1070"
    _, data = call(server, "/api/results")
    elden = next(r for r in data["results"] if r["id"] == "forza-horizon-5")
    assert elden["overall"] != "unknown"
    _, hw = call(server, "/api/hardware")
    assert hw["settings"] == {"gpu_override": "NVIDIA GeForce GTX 1070"}
    call(server, "/api/overrides", "POST", {"gpu_override": ""})
    assert "gpu_override" not in lib.load_settings()


def test_override_rejects_unknown_names(server):
    call(server, "/api/overrides", "POST", {"cpu_override": "<script>"})
    assert "cpu_override" not in lib.load_settings()


def test_update_not_configured(server, monkeypatch):
    monkeypatch.setattr(lib, "DEFAULT_LIBRARY_URL", "")
    status, data = call(server, "/api/update-library", "POST", {})
    assert status == 200 and data["status"] == "not_configured"


def test_update_success_reloads(server, library):
    from test_library import FakeLibraryServer, newer
    fake = FakeLibraryServer(json.dumps(newer(library)).encode())
    try:
        lib.save_settings({"library_url": fake.url})
        orig = lib.update
        lib.update = lambda v, **kw: orig(v, allow_insecure_http=True)
        try:
            status, data = call(server, "/api/update-library", "POST", {})
        finally:
            lib.update = orig
        assert data["status"] == "updated" and data["library"]["source"] == "downloaded"
        _, res = call(server, "/api/results")
        assert any(r["id"] == "new-game" for r in res["results"])
    finally:
        fake.close()


def test_security_headers(server):
    req = urllib.request.Request(server.base + "/")
    with urllib.request.urlopen(req) as r:
        assert "default-src 'self'" in r.headers["Content-Security-Policy"]
        assert r.headers["Cache-Control"] == "no-store"


def test_unknown_paths(server):
    assert call(server, "/etc/passwd", token=False)[0] == 404
    assert call(server, "/api/nope")[0] == 404


def test_shutdown(server):
    status, data = call(server, "/api/shutdown", "POST", {})
    assert status == 200 and data == {"ok": True}
