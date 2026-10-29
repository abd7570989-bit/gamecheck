import pytest

from conftest import make_system
from gamecheck.compare import Analyzer


@pytest.fixture(scope="module")
def analyzer(library):
    return Analyzer(library)


def result(analyzer, game_id, system, **overrides):
    me = analyzer.describe_system(system, **overrides)
    game = next(g for g in analyzer.library["games"] if g["id"] == game_id)
    r = analyzer.check(game, me)
    return r, {c["key"]: c for c in r["components"]}


def test_exact_minimum_spec_meets_minimum(analyzer):
    # Elden Ring minimum: i5-8400, GTX 1060 3GB, 12 GB RAM.
    r, c = result(analyzer, "elden-ring", make_system(cpu="Intel(R) Core(TM) i5-8400 CPU @ 2.80GHz",
                                                       gpus=[("NVIDIA GeForce GTX 1060 3GB", 3.0)], ram=12))
    assert c["cpu"]["status"] == "minimum"
    assert c["gpu"]["status"] == "minimum"
    assert c["ram"]["status"] == "minimum"
    assert r["overall"] == "minimum"


def test_strong_pc_gets_recommended(analyzer):
    r, c = result(analyzer, "cyberpunk-2077", make_system(cpu="AMD Ryzen 7 7800X3D 8-Core Processor",
                                                           gpus=[("NVIDIA GeForce RTX 4070", 12.0)], ram=32, os_version=11))
    assert all(x["status"] == "recommended" for x in r["components"]), r["components"]
    assert r["overall"] == "recommended"


def test_weak_gpu_is_below(analyzer):
    r, c = result(analyzer, "cyberpunk-2077", make_system(cpu="AMD Ryzen 5 3600 6-Core Processor",
                                                           gpus=[("NVIDIA GeForce GTX 1050 Ti", 4.0)]))
    assert c["gpu"]["status"] == "below"
    assert r["overall"] == "below"
    assert "gpu" in r["weakest"]


def test_alternatives_any_one_is_enough(analyzer):
    # Cyberpunk min GPU: GTX 1060 6GB (100) / RX 580 (98) / Arc A380 (75). An Arc A380 meets the minimum.
    r, c = result(analyzer, "cyberpunk-2077", make_system(cpu="Intel(R) Core(TM) i7-6700 CPU @ 3.40GHz",
                                                           gpus=[("Intel(R) Arc(TM) A380 Graphics", 6.0)], ram=16))
    assert c["gpu"]["status"] == "minimum"


def test_borderline_within_ten_percent(analyzer):
    # GTA V recommended CPU min alternatives: i5-3470 (87) / FX-8350 (92) -> required 87 at recommended.
    # Elden Ring min CPU: i5-8400 (150) / Ryzen 3 3300X (165) -> 150. i5-9400 (155) passes; i7-6700K (145) is within 10%.
    r, c = result(analyzer, "elden-ring", make_system(cpu="Intel(R) Core(TM) i7-6700K CPU @ 4.00GHz"))
    assert c["cpu"]["status"] == "borderline"
    assert r["overall"] == "borderline"
    r, c = result(analyzer, "elden-ring", make_system(cpu="Intel(R) Core(TM) i5-4460  CPU @ 3.20GHz"))
    assert c["cpu"]["status"] == "below"


def test_unrecognised_parts_are_unknown_not_guessed(analyzer):
    r, c = result(analyzer, "elden-ring", make_system(cpu="Intel(R) Xeon(R) CPU E5-2680 v4", gpus=[("Weird GPU 9000", None)]))
    assert c["cpu"]["status"] == "unknown"
    assert c["gpu"]["status"] == "unknown"
    assert c["gpu"]["note"] == "gpu_unrecognised"
    assert r["overall"] == "unknown"


def test_below_beats_unknown(analyzer):
    r, _ = result(analyzer, "elden-ring", make_system(cpu="Unknown CPU", ram=4))
    assert r["overall"] == "below"


def test_manual_override_fixes_unknown(analyzer):
    sysinfo = make_system(cpu="Unknown CPU", gpus=[("Weird GPU 9000", None)])
    r, c = result(analyzer, "elden-ring", sysinfo, cpu_override="Intel Core i7-8700K",
                  gpu_override="NVIDIA GeForce GTX 1070")
    assert c["cpu"]["status"] == "recommended"
    assert c["gpu"]["status"] == "recommended"
    assert c["vram"]["yours"] == 8


def test_invalid_override_falls_back_to_detection(analyzer):
    r, c = result(analyzer, "elden-ring", make_system(), cpu_override="Not A CPU", gpu_override="Not A GPU")
    assert c["cpu"]["yours"] == "Intel Core i5-4460"
    assert c["gpu"]["yours"] == "NVIDIA GeForce GTX 1060 6GB"


def test_laptop_gpu_penalised(analyzer):
    # Desktop RTX 3060 (175) meets Cyberpunk's recommended GPU (2060 SUPER 170). Laptop (140) does not.
    _, desk = result(analyzer, "cyberpunk-2077", make_system(gpus=[("NVIDIA GeForce RTX 3060", 12.0)]))
    _, lap = result(analyzer, "cyberpunk-2077", make_system(gpus=[("NVIDIA GeForce RTX 3060 Laptop GPU", 6.0)]))
    assert desk["gpu"]["status"] == "recommended"
    assert lap["gpu"]["status"] == "minimum"
    assert lap["gpu"]["note"] == "laptop_gpu"


def test_best_gpu_chosen_on_hybrid_laptop(analyzer):
    me = analyzer.describe_system(make_system(gpus=[("Intel(R) UHD Graphics 630", None),
                                                    ("NVIDIA GeForce GTX 1660 Ti", 6.0)]))
    assert me["gpu_model"] == "NVIDIA GeForce GTX 1660 Ti"


def test_vram_reported_by_driver_preferred(analyzer):
    me = analyzer.describe_system(make_system(gpus=[("AMD Radeon RX 580 Series", 4.0)]))
    assert me["vram_gb"] == 4.0
    me = analyzer.describe_system(make_system(gpus=[("AMD Radeon RX 580 Series", None)]))
    assert me["vram_gb"] == 8   # table default when the driver doesn't say


def test_low_vram_below(analyzer):
    # RX 580 4GB has the GPU power for Cyberpunk minimum but not the 6 GB VRAM.
    r, c = result(analyzer, "cyberpunk-2077", make_system(cpu="Intel(R) Core(TM) i7-6700 CPU @ 3.40GHz",
                                                           gpus=[("AMD Radeon RX 580 Series", 4.0)]))
    assert c["gpu"]["status"] == "minimum"
    assert c["vram"]["status"] == "below"
    assert r["overall"] == "below"


def test_integrated_gpu_skips_vram(analyzer):
    r, c = result(analyzer, "valorant", make_system(gpus=[("Intel(R) UHD Graphics 620", None)]))
    assert "vram" not in c
    assert c["gpu"]["status"] == "recommended"   # UHD 620 (9) >= GT 730 (8)


def test_ram_tolerance(analyzer):
    _, c = result(analyzer, "elden-ring", make_system(ram=15.85))
    assert c["ram"]["status"] == "recommended"
    _, c = result(analyzer, "elden-ring", make_system(ram=8))
    assert c["ram"]["status"] == "below"


def test_disk_space_is_a_warning_not_the_verdict(analyzer):
    r, c = result(analyzer, "red-dead-redemption-2",
                  make_system(cpu="AMD Ryzen 5 3600 6-Core Processor", gpus=[("NVIDIA GeForce RTX 3070", 8.0)], free=20))
    assert c["storage"]["status"] == "below"
    assert r["needs_disk_space"] is True
    assert r["overall"] == "recommended"


def test_os_checks(analyzer):
    _, c = result(analyzer, "elden-ring", make_system(os_version=7))
    assert c["os"]["status"] == "below"
    _, c = result(analyzer, "elden-ring", make_system(is_64bit=False))
    assert c["os"]["status"] == "below"
    _, c = result(analyzer, "elden-ring", make_system(family="linux"))
    assert c["os"]["status"] == "unknown"


def test_minimum_only_game_never_claims_recommended(analyzer):
    r, _ = result(analyzer, "counter-strike-2", make_system(cpu="AMD Ryzen 7 7800X3D 8-Core Processor",
                                                             gpus=[("NVIDIA GeForce RTX 4090", 24.0)], ram=64))
    assert r["has_recommended"] is False
    assert r["overall"] == "minimum"


def test_check_all_covers_library(analyzer):
    me = analyzer.describe_system(make_system())
    results = analyzer.check_all(me)
    assert len(results) == len(analyzer.library["games"])
    assert {r["overall"] for r in results} <= {"recommended", "minimum", "borderline", "below", "unknown"}


def test_manual_choice_is_flagged(analyzer):
    me = analyzer.describe_system(make_system(), cpu_override="Intel Core i7-8700K")
    assert me["cpu_manual"] is True and me["gpu_manual"] is False
    assert me["gpu_detected"] == "NVIDIA GeForce GTX 1060 6GB"
    me = analyzer.describe_system(make_system(), gpu_override="NVIDIA GeForce GTX 1070")
    assert me["gpu_manual"] is True and me["cpu_manual"] is False
