import pytest

from gamecheck.hardware_db import cpu_table, gpu_table, is_laptop_gpu, normalize_cpu, normalize_gpu


@pytest.fixture(scope="module")
def cpus(library):
    return cpu_table(library)


@pytest.fixture(scope="module")
def gpus(library):
    return gpu_table(library)


# Strings as Windows / drivers actually report them.
@pytest.mark.parametrize("detected, expected", [
    ("Intel(R) Core(TM) i5-4460  CPU @ 3.20GHz", "Intel Core i5-4460"),
    ("Intel(R) Core(TM) i7-8700K CPU @ 3.70GHz", "Intel Core i7-8700K"),
    ("12th Gen Intel(R) Core(TM) i5-12400F", "Intel Core i5-12400"),
    ("13th Gen Intel(R) Core(TM) i5-13600KF", "Intel Core i5-13600K"),
    ("Intel(R) Core(TM) i5 CPU         750  @ 2.67GHz", "Intel Core i5-750"),
    ("Intel(R) Core(TM)2 Quad CPU    Q6600  @ 2.40GHz", "Intel Core 2 Quad Q6600"),
    ("Intel(R) Core(TM)2 Duo CPU     E8400  @ 3.00GHz", "Intel Core 2 Duo E8400"),
    ("Intel(R) Core(TM) Ultra 7 155H", "Intel Core Ultra 7 155H"),
    ("11th Gen Intel(R) Core(TM) i5-1135G7 @ 2.40GHz", "Intel Core i5-1135G7"),
    ("AMD Ryzen 5 3600 6-Core Processor", "AMD Ryzen 5 3600"),
    ("AMD Ryzen 5 3600X 6-Core Processor", "AMD Ryzen 5 3600X"),
    ("AMD Ryzen 7 5800X3D 8-Core Processor", "AMD Ryzen 7 5800X3D"),
    ("AMD Ryzen 5 5600G with Radeon Graphics", "AMD Ryzen 5 5600G"),
    ("AMD Ryzen 3 2200G with Radeon Vega Graphics", "AMD Ryzen 3 2200G"),
    ("AMD FX(tm)-6300 Six-Core Processor", "AMD FX-6300"),
    ("AMD FX(tm)-8350 Eight-Core Processor", "AMD FX-8350"),
    ("AMD Phenom(tm) 9850 Quad-Core Processor", "AMD Phenom 9850"),
    ("AMD Phenom(tm) II X4 940 Processor", "AMD Phenom II X4 940"),
    ("AMD Athlon 200GE with Radeon Vega Graphics", "AMD Athlon 200GE"),
])
def test_cpu_detection_strings(cpus, detected, expected):
    entry = cpus.match(detected)
    assert entry is not None and entry.name == expected


@pytest.mark.parametrize("detected, expected", [
    ("NVIDIA GeForce GTX 1060 6GB", "NVIDIA GeForce GTX 1060 6GB"),
    ("NVIDIA GeForce GTX 1060", "NVIDIA GeForce GTX 1060 6GB"),
    ("NVIDIA GeForce GTX 1060 3GB", "NVIDIA GeForce GTX 1060 3GB"),
    ("NVIDIA GeForce RTX 3060", "NVIDIA GeForce RTX 3060"),
    ("NVIDIA GeForce RTX 3060 Ti", "NVIDIA GeForce RTX 3060 Ti"),
    ("NVIDIA GeForce RTX 3060 Laptop GPU", "NVIDIA GeForce RTX 3060"),
    ("NVIDIA GeForce RTX 4070 Ti SUPER", "NVIDIA GeForce RTX 4070 Ti SUPER"),
    ("NVIDIA GeForce RTX 4070 SUPER", "NVIDIA GeForce RTX 4070 SUPER"),
    ("NVIDIA GeForce GTX 1660 SUPER", "NVIDIA GeForce GTX 1660 SUPER"),
    ("NVIDIA GeForce 9800 GT", "NVIDIA GeForce 9800 GT"),
    ("AMD Radeon RX 580 Series", "AMD Radeon RX 580"),
    ("Radeon RX 580 2048SP", "AMD Radeon RX 580"),
    ("AMD Radeon RX 5700 XT", "AMD Radeon RX 5700 XT"),
    ("AMD Radeon RX 5700", "AMD Radeon RX 5700"),
    ("AMD Radeon RX 570", "AMD Radeon RX 570"),
    ("AMD Radeon RX 7900 XTX", "AMD Radeon RX 7900 XTX"),
    ("AMD Radeon RX 7900 XT", "AMD Radeon RX 7900 XT"),
    ("Radeon RX Vega", None),
    ("AMD Radeon RX Vega 56", "AMD Radeon RX Vega 56"),
    ("AMD Radeon(TM) Vega 8 Graphics", "AMD Radeon Vega 8 Graphics"),
    ("AMD Radeon HD 7800 Series", "AMD Radeon HD 7850"),
    ("AMD Radeon R9 200 Series", None),
    ("AMD Radeon(TM) Graphics", None),
    ("Intel(R) UHD Graphics 620", "Intel UHD Graphics 620"),
    ("Intel(R) HD Graphics 620", "Intel HD Graphics 620"),
    ("Intel(R) HD Graphics 4000", "Intel HD Graphics 4000"),
    ("Intel(R) Iris(R) Xe Graphics", "Intel Iris Xe Graphics"),
    ("Intel(R) Arc(TM) A770 Graphics", "Intel Arc A770"),
    ("Microsoft Basic Display Adapter", None),
    ("Advanced Radeon RX 6700 XT", "AMD Radeon RX 6700 XT"),  # Linux lspci form
])
def test_gpu_detection_strings(gpus, detected, expected):
    entry = gpus.match(detected)
    assert (entry.name if entry else None) == expected


def test_no_false_prefix_matches(gpus, cpus):
    assert gpus.match("NVIDIA GeForce GTX 10600") is None
    assert cpus.match("Intel Core i5-7500") is None   # not in table; must not match i5-750
    assert cpus.match("Intel Core i5-44600") is None


def test_unknown_inputs(gpus, cpus):
    assert gpus.match("") is None and cpus.match("") is None
    assert cpus.match("Intel(R) Xeon(R) Processor @ 2.10GHz") is None


def test_laptop_detection():
    assert is_laptop_gpu("NVIDIA GeForce RTX 3060 Laptop GPU")
    assert is_laptop_gpu("NVIDIA GeForce GTX 1650 with Max-Q Design")
    assert not is_laptop_gpu("NVIDIA GeForce RTX 3060")


def test_every_requirement_resolves(library, cpus, gpus):
    """A requirement the table can't resolve would silently weaken a comparison."""
    missing = []
    for game in library["games"]:
        for tier in ("minimum", "recommended"):
            reqs = game.get(tier) or {}
            missing += [(game["id"], n) for n in reqs.get("cpu", []) if cpus.match(n) is None]
            missing += [(game["id"], n) for n in reqs.get("gpu", []) if gpus.match(n) is None]
    assert missing == []


def test_requirement_names_resolve_to_themselves(library, cpus, gpus):
    for row in library["cpus"]:
        assert cpus.match(row["name"]).name == row["name"]
    for row in library["gpus"]:
        assert gpus.match(row["name"]).name == row["name"]


def test_keys_are_unique(library):
    seen = {}
    for row in library["gpus"]:
        for key in row.get("keys") or [row["name"]]:
            k = normalize_gpu(key)
            assert k not in seen, f"{key} collides with {seen[k]}"
            seen[k] = row["name"]
    seen = {}
    for row in library["cpus"]:
        k = normalize_cpu(row["name"])
        assert k not in seen, f"{row['name']} collides with {seen[k]}"
        seen[k] = row["name"]


def test_recommended_never_below_minimum(library, cpus, gpus):
    for game in library["games"]:
        rec = game.get("recommended")
        if not rec:
            continue
        mn = game["minimum"]
        for table, key in ((cpus, "cpu"), (gpus, "gpu")):
            lo = [table.match(n).score for n in mn.get(key, [])]
            hi = [table.match(n).score for n in rec.get(key, [])]
            if lo and hi:
                assert min(hi) >= min(lo), (game["id"], key)
        for key in ("ram_gb", "vram_gb", "storage_gb"):
            if key in mn and key in rec:
                assert rec[key] >= mn[key], (game["id"], key)
