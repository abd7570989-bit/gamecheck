import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gamecheck.paths import bundled_library_path  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Every test gets its own empty user data folder."""
    data = tmp_path / "userdata"
    monkeypatch.setenv("GAMECHECK_DATA_DIR", str(data))
    return data


@pytest.fixture(scope="session")
def library():
    return json.loads(bundled_library_path().read_text(encoding="utf-8"))


@pytest.fixture
def library_copy(library):
    return copy.deepcopy(library)


def make_system(cpu="Intel(R) Core(TM) i5-4460  CPU @ 3.20GHz", gpus=(("NVIDIA GeForce GTX 1060 6GB", 6.0),),
                ram=16.0, free=500.0, os_version=10, family="windows", is_64bit=True):
    return {
        "os": {"family": family, "name": f"Windows {os_version}", "version": os_version, "is_64bit": is_64bit},
        "cpu": {"name": cpu, "threads": 4},
        "ram_gb": ram,
        "gpus": [{"name": n, "vram_gb": v} for n, v in gpus],
        "disks": [{"mount": "C:\\", "free_gb": free, "total_gb": 1000.0}],
        "errors": [],
    }
