import socket
import sys
import types

import pytest

from gamecheck import scanner


@pytest.fixture
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("scanner tried to use the network")
    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def test_scan_works_offline(no_network):
    result = scanner.scan()
    assert set(result) == {"os", "cpu", "ram_gb", "gpus", "disks", "errors"}
    if sys.platform.startswith("linux"):
        assert result["cpu"]["name"]
        assert result["ram_gb"] and result["ram_gb"] > 0
        assert result["disks"] and result["disks"][0]["free_gb"] >= 0
    assert result["errors"] == []


def test_registry_vram_parsing():
    assert scanner._registry_vram_gb(8 * scanner.GB) == 8
    assert scanner._registry_vram_gb((6 * scanner.GB).to_bytes(8, "little")) == 6
    assert scanner._registry_vram_gb(0) is None
    assert scanner._registry_vram_gb(None) is None


class FakeKey:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_winreg(tree):
    """Minimal winreg stand-in: tree maps key path -> {value name: value} and subkey lists."""
    mod = types.SimpleNamespace(HKEY_LOCAL_MACHINE="HKLM")

    def OpenKey(root, path):
        if path not in tree:
            raise OSError("missing")
        return FakeKey(path)

    def QueryValueEx(key, name):
        values = tree[key.path]
        if name not in values:
            raise OSError("missing")
        return values[name], 1

    def EnumKey(key, index):
        subs = tree[key.path].get("__subkeys__", [])
        if index >= len(subs):
            raise OSError("done")
        return subs[index]

    mod.OpenKey, mod.QueryValueEx, mod.EnumKey = OpenKey, QueryValueEx, EnumKey
    return mod


def test_windows_gpu_registry_reading(monkeypatch):
    base = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
    tree = {
        base: {"__subkeys__": ["0000", "0001", "0002", "Configuration", "0003"]},
        base + r"\0000": {"DriverDesc": "Intel(R) UHD Graphics 630", "HardwareInformation.MemorySize": 1024 ** 3},
        base + r"\0001": {"DriverDesc": "NVIDIA GeForce RTX 3070",
                          "HardwareInformation.qwMemorySize": 8 * 1024 ** 3,
                          "HardwareInformation.MemorySize": 4 * 1024 ** 3 - 1},
        base + r"\0002": {"DriverDesc": "Microsoft Basic Display Adapter"},
        base + r"\0003": {"DriverDesc": "NVIDIA GeForce RTX 3070"},   # duplicate entry for a 2nd output
    }
    monkeypatch.setitem(sys.modules, "winreg", fake_winreg(tree))
    gpus = scanner._win_gpus()
    assert gpus == [{"name": "Intel(R) UHD Graphics 630", "vram_gb": 1.0},
                    {"name": "NVIDIA GeForce RTX 3070", "vram_gb": 8.0}]


def test_windows_cpu_from_registry(monkeypatch):
    tree = {r"HARDWARE\DESCRIPTION\System\CentralProcessor\0":
            {"ProcessorNameString": "  AMD Ryzen 5 3600 6-Core Processor  "}}
    monkeypatch.setitem(sys.modules, "winreg", fake_winreg(tree))
    assert scanner._win_cpu() == "AMD Ryzen 5 3600 6-Core Processor"


@pytest.mark.parametrize("build, expected", [(19045, 10), (22631, 11), (26100, 11)])
def test_windows_11_detected_from_build(monkeypatch, build, expected):
    monkeypatch.setattr(sys, "getwindowsversion", lambda: types.SimpleNamespace(major=10, build=build), raising=False)
    monkeypatch.setenv("PROCESSOR_ARCHITECTURE", "AMD64")
    info = scanner._win_os()
    assert info["version"] == expected and info["name"] == f"Windows {expected}" and info["is_64bit"]


def test_failing_probe_does_not_break_scan(monkeypatch):
    if not sys.platform.startswith("linux"):
        pytest.skip("linux probe names")
    monkeypatch.setattr(scanner, "_linux_gpus", lambda: 1 / 0)
    result = scanner.scan()
    assert result["gpus"] == []
    assert result["errors"] and result["errors"][0].startswith("gpu:")
    assert result["cpu"]["name"]
