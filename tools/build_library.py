"""Regenerate gamecheck/data/library.json from the tables below.

Scores are approximate relative gaming performance (CPU: Core i5-4460 = 100,
GPU: GeForce GTX 1060 6GB = 100), compiled from public benchmark aggregates.
They are estimates for comparison, not exact benchmarks.

Bump LIBRARY_VERSION every time you publish a changed library, otherwise
installed copies will not pick it up.

Usage:  python tools/build_library.py
"""

import json
from datetime import date
from pathlib import Path

SCHEMA_VERSION = 1
LIBRARY_VERSION = 1

# (name, score, extra keys)
CPUS = [
    ("Intel Core 2 Duo E8400", 35), ("Intel Core 2 Quad Q6600", 40), ("Intel Core 2 Quad Q9550", 50),
    ("AMD Phenom 9850", 35), ("AMD Phenom II X4 940", 45), ("AMD Phenom II X4 965", 50),
    ("Intel Core i5-750", 52), ("Intel Core i7-920", 60),
    ("Intel Core i3-2100", 50), ("Intel Core i5-2400", 75), ("Intel Core i5-2500K", 82), ("Intel Core i7-2600K", 95),
    ("Intel Core i3-3210", 52), ("Intel Core i3-3225", 55), ("Intel Core i5-3470", 87), ("Intel Core i5-3570K", 92),
    ("Intel Core i7-3770", 105), ("Intel Core i7-3770K", 108),
    ("Intel Core i3-4150", 62), ("Intel Core i5-4430", 92), ("Intel Core i5-4460", 100), ("Intel Core i5-4590", 104),
    ("Intel Core i5-4670K", 106), ("Intel Core i5-4690", 107), ("Intel Core i5-4690K", 108),
    ("Intel Core i7-4770", 120), ("Intel Core i7-4770K", 123), ("Intel Core i7-4790", 128), ("Intel Core i7-4790K", 132),
    ("Intel Core i3-6100", 75), ("Intel Core i3-6300", 80), ("Intel Core i5-6400", 105), ("Intel Core i5-6500", 110),
    ("Intel Core i5-6600", 116), ("Intel Core i5-6600K", 120), ("Intel Core i7-6700", 138), ("Intel Core i7-6700K", 145),
    ("Intel Core i5-7300U", 70), ("Intel Core i5-7400", 115), ("Intel Core i5-7600K", 128), ("Intel Core i7-7700", 150),
    ("Intel Core i7-7700K", 155),
    ("Intel Core i3-8100", 110), ("Intel Core i5-8250U", 85), ("Intel Core i5-8400", 150), ("Intel Core i5-8600K", 165),
    ("Intel Core i7-8700", 180), ("Intel Core i7-8700K", 188),
    ("Intel Core i5-9400", 155), ("Intel Core i5-9600K", 172), ("Intel Core i7-9700", 195), ("Intel Core i7-9700K", 205),
    ("Intel Core i9-9900K", 225),
    ("Intel Core i3-10100", 130), ("Intel Core i5-10210U", 90), ("Intel Core i5-10400", 175), ("Intel Core i5-10600K", 200),
    ("Intel Core i7-10700", 225), ("Intel Core i7-10700K", 235), ("Intel Core i7-10750H", 165), ("Intel Core i9-10900K", 255),
    ("Intel Core i5-1135G7", 115), ("Intel Core i5-11400", 200), ("Intel Core i5-11400H", 190), ("Intel Core i7-11700K", 250),
    ("Intel Core i3-12100", 185), ("Intel Core i5-12400", 235), ("Intel Core i5-12600K", 285), ("Intel Core i7-12700", 310),
    ("Intel Core i7-12700H", 260), ("Intel Core i7-12700K", 325), ("Intel Core i9-12900K", 355),
    ("Intel Core i5-13400", 260), ("Intel Core i5-13600K", 340), ("Intel Core i7-13700K", 390), ("Intel Core i9-13900K", 430),
    ("Intel Core i5-14400", 270), ("Intel Core i5-14600K", 350), ("Intel Core i7-14700K", 410), ("Intel Core i9-14900K", 440),
    ("Intel Core Ultra 5 125H", 230), ("Intel Core Ultra 7 155H", 270),
    ("Intel Core Ultra 5 245K", 330), ("Intel Core Ultra 7 265K", 400), ("Intel Core Ultra 9 285K", 440),
    ("AMD FX-4300", 55), ("AMD FX-4350", 58), ("AMD FX-6300", 75), ("AMD FX-8320", 85), ("AMD FX-8350", 92),
    ("AMD A8-7600", 50), ("AMD A10-7800", 55), ("AMD Athlon 200GE", 60),
    ("AMD Ryzen 3 1200", 95), ("AMD Ryzen 3 1300X", 105), ("AMD Ryzen 5 1400", 110), ("AMD Ryzen 5 1500X", 125),
    ("AMD Ryzen 5 1600", 140), ("AMD Ryzen 5 1600X", 145), ("AMD Ryzen 7 1700", 155), ("AMD Ryzen 7 1800X", 165),
    ("AMD Ryzen 3 2200G", 105), ("AMD Ryzen 5 2400G", 125), ("AMD Ryzen 5 2600", 155), ("AMD Ryzen 5 2600X", 162),
    ("AMD Ryzen 7 2700X", 180),
    ("AMD Ryzen 3 3100", 140), ("AMD Ryzen 3 3200G", 115), ("AMD Ryzen 3 3300U", 70), ("AMD Ryzen 3 3300X", 165),
    ("AMD Ryzen 5 3400G", 135), ("AMD Ryzen 5 3500U", 85), ("AMD Ryzen 5 3600", 190), ("AMD Ryzen 5 3600X", 198),
    ("AMD Ryzen 7 3700X", 215), ("AMD Ryzen 7 3800X", 222), ("AMD Ryzen 9 3900X", 245),
    ("AMD Ryzen 5 4500", 190), ("AMD Ryzen 5 4600H", 165),
    ("AMD Ryzen 5 5500", 210), ("AMD Ryzen 5 5600", 245), ("AMD Ryzen 5 5600G", 230), ("AMD Ryzen 5 5600H", 215),
    ("AMD Ryzen 5 5600X", 252), ("AMD Ryzen 7 5700X", 270), ("AMD Ryzen 7 5800H", 245), ("AMD Ryzen 7 5800X", 285),
    ("AMD Ryzen 7 5800X3D", 320), ("AMD Ryzen 9 5900X", 305), ("AMD Ryzen 9 5950X", 320),
    ("AMD Ryzen 7 6800H", 270),
    ("AMD Ryzen 5 7600", 300), ("AMD Ryzen 5 7600X", 310), ("AMD Ryzen 7 7700X", 340), ("AMD Ryzen 7 7800X3D", 400),
    ("AMD Ryzen 9 7950X", 400),
    ("AMD Ryzen 5 9600X", 335), ("AMD Ryzen 7 9700X", 370), ("AMD Ryzen 7 9800X3D", 450),
]

# (name, score, vram_gb, integrated, extra keys)
GPUS = [
    ("NVIDIA GeForce 9800 GT", 10, 1, False, []), ("NVIDIA GeForce GT 640", 10, 2, False, []),
    ("NVIDIA GeForce GT 730", 8, 2, False, []), ("NVIDIA GeForce GT 1030", 22, 2, False, []),
    ("NVIDIA GeForce GTX 650", 18, 1, False, []), ("NVIDIA GeForce GTX 650 Ti", 25, 1, False, []),
    ("NVIDIA GeForce GTX 660", 40, 2, False, []), ("NVIDIA GeForce GTX 660 Ti", 48, 2, False, []),
    ("NVIDIA GeForce GTX 670", 55, 2, False, []), ("NVIDIA GeForce GTX 680", 60, 2, False, []),
    ("NVIDIA GeForce GTX 750", 30, 1, False, []), ("NVIDIA GeForce GTX 750 Ti", 35, 2, False, []),
    ("NVIDIA GeForce GTX 760", 50, 2, False, []), ("NVIDIA GeForce GTX 770", 62, 2, False, []),
    ("NVIDIA GeForce GTX 780", 70, 3, False, []), ("NVIDIA GeForce GTX 780 Ti", 80, 3, False, []),
    ("NVIDIA GeForce GTX 950", 45, 2, False, []), ("NVIDIA GeForce GTX 960", 55, 2, False, []),
    ("NVIDIA GeForce GTX 970", 85, 4, False, []), ("NVIDIA GeForce GTX 980", 102, 4, False, []),
    ("NVIDIA GeForce GTX 980 Ti", 130, 6, False, []),
    ("NVIDIA GeForce GTX 1050", 47, 2, False, []), ("NVIDIA GeForce GTX 1050 Ti", 58, 4, False, []),
    ("NVIDIA GeForce GTX 1060 3GB", 92, 3, False, []),
    ("NVIDIA GeForce GTX 1060 6GB", 100, 6, False, ["NVIDIA GeForce GTX 1060"]),
    ("NVIDIA GeForce GTX 1070", 135, 8, False, []), ("NVIDIA GeForce GTX 1070 Ti", 150, 8, False, []),
    ("NVIDIA GeForce GTX 1080", 165, 8, False, []), ("NVIDIA GeForce GTX 1080 Ti", 210, 11, False, []),
    ("NVIDIA GeForce GTX 1630", 40, 4, False, []), ("NVIDIA GeForce GTX 1650", 72, 4, False, []),
    ("NVIDIA GeForce GTX 1650 SUPER", 95, 4, False, []), ("NVIDIA GeForce GTX 1660", 115, 6, False, []),
    ("NVIDIA GeForce GTX 1660 SUPER", 128, 6, False, []), ("NVIDIA GeForce GTX 1660 Ti", 130, 6, False, []),
    ("NVIDIA GeForce RTX 2060", 150, 6, False, []), ("NVIDIA GeForce RTX 2060 SUPER", 170, 8, False, []),
    ("NVIDIA GeForce RTX 2070", 180, 8, False, []), ("NVIDIA GeForce RTX 2070 SUPER", 200, 8, False, []),
    ("NVIDIA GeForce RTX 2080", 215, 8, False, []), ("NVIDIA GeForce RTX 2080 SUPER", 225, 8, False, []),
    ("NVIDIA GeForce RTX 2080 Ti", 270, 11, False, []),
    ("NVIDIA GeForce RTX 3050", 125, 8, False, []), ("NVIDIA GeForce RTX 3060", 175, 12, False, []),
    ("NVIDIA GeForce RTX 3060 Ti", 225, 8, False, []), ("NVIDIA GeForce RTX 3070", 255, 8, False, []),
    ("NVIDIA GeForce RTX 3070 Ti", 270, 8, False, []), ("NVIDIA GeForce RTX 3080", 330, 10, False, []),
    ("NVIDIA GeForce RTX 3080 Ti", 365, 12, False, []), ("NVIDIA GeForce RTX 3090", 375, 24, False, []),
    ("NVIDIA GeForce RTX 3090 Ti", 400, 24, False, []),
    ("NVIDIA GeForce RTX 4060", 210, 8, False, []), ("NVIDIA GeForce RTX 4060 Ti", 250, 8, False, []),
    ("NVIDIA GeForce RTX 4070", 325, 12, False, []), ("NVIDIA GeForce RTX 4070 SUPER", 375, 12, False, []),
    ("NVIDIA GeForce RTX 4070 Ti", 400, 12, False, []), ("NVIDIA GeForce RTX 4070 Ti SUPER", 425, 16, False, []),
    ("NVIDIA GeForce RTX 4080", 490, 16, False, []), ("NVIDIA GeForce RTX 4080 SUPER", 500, 16, False, []),
    ("NVIDIA GeForce RTX 4090", 640, 24, False, []),
    ("NVIDIA GeForce RTX 5060", 250, 8, False, []), ("NVIDIA GeForce RTX 5060 Ti", 290, 8, False, []),
    ("NVIDIA GeForce RTX 5070", 390, 12, False, []), ("NVIDIA GeForce RTX 5070 Ti", 480, 16, False, []),
    ("NVIDIA GeForce RTX 5080", 550, 16, False, []), ("NVIDIA GeForce RTX 5090", 780, 32, False, []),
    ("AMD Radeon HD 4870", 14, 1, False, []), ("AMD Radeon HD 5770", 18, 1, False, []),
    ("AMD Radeon HD 7770", 27, 1, False, []), ("AMD Radeon HD 7850", 40, 2, False, ["AMD Radeon HD 7800 Series"]),
    ("AMD Radeon HD 7870", 47, 2, False, []), ("AMD Radeon HD 7950", 58, 3, False, ["AMD Radeon HD 7900 Series"]),
    ("AMD Radeon HD 7970", 65, 3, False, []),
    ("AMD Radeon R5 200 Series", 5, 1, False, ["Radeon R5 230", "Radeon R5 235"]),
    ("AMD Radeon R7 240", 8, 2, False, []), ("AMD Radeon R7 250", 13, 1, False, []),
    ("AMD Radeon R7 260X", 30, 2, False, []), ("AMD Radeon R7 370", 45, 2, False, []),
    ("AMD Radeon R9 270", 45, 2, False, []), ("AMD Radeon R9 270X", 50, 2, False, []),
    ("AMD Radeon R9 280", 58, 3, False, []), ("AMD Radeon R9 280X", 65, 3, False, []),
    ("AMD Radeon R9 285", 62, 2, False, []), ("AMD Radeon R9 290", 85, 4, False, []),
    ("AMD Radeon R9 290X", 92, 4, False, []), ("AMD Radeon R9 380", 62, 4, False, []),
    ("AMD Radeon R9 390", 95, 8, False, []), ("AMD Radeon R9 Fury", 115, 4, False, []),
    ("AMD Radeon RX 460", 40, 2, False, []), ("AMD Radeon RX 470", 85, 4, False, []),
    ("AMD Radeon RX 480", 95, 4, False, []), ("AMD Radeon RX 550", 25, 2, False, []),
    ("AMD Radeon RX 560", 42, 4, False, []), ("AMD Radeon RX 570", 88, 4, False, []),
    ("AMD Radeon RX 580", 98, 8, False, []), ("AMD Radeon RX 590", 108, 8, False, []),
    ("AMD Radeon RX Vega 56", 140, 8, False, []), ("AMD Radeon RX Vega 64", 155, 8, False, []),
    ("AMD Radeon RX 5500 XT", 105, 4, False, []), ("AMD Radeon RX 5600 XT", 150, 6, False, []),
    ("AMD Radeon RX 5700", 165, 8, False, []), ("AMD Radeon RX 5700 XT", 185, 8, False, []),
    ("AMD Radeon RX 6400", 60, 4, False, []), ("AMD Radeon RX 6500 XT", 75, 4, False, []),
    ("AMD Radeon RX 6600", 175, 8, False, []), ("AMD Radeon RX 6600 XT", 200, 8, False, []),
    ("AMD Radeon RX 6650 XT", 210, 8, False, []), ("AMD Radeon RX 6700 XT", 250, 12, False, []),
    ("AMD Radeon RX 6750 XT", 265, 12, False, []), ("AMD Radeon RX 6800", 310, 16, False, []),
    ("AMD Radeon RX 6800 XT", 360, 16, False, []), ("AMD Radeon RX 6900 XT", 385, 16, False, []),
    ("AMD Radeon RX 6950 XT", 410, 16, False, []),
    ("AMD Radeon RX 7600", 210, 8, False, []), ("AMD Radeon RX 7600 XT", 220, 16, False, []),
    ("AMD Radeon RX 7700 XT", 300, 12, False, []), ("AMD Radeon RX 7800 XT", 360, 16, False, []),
    ("AMD Radeon RX 7900 GRE", 400, 16, False, []), ("AMD Radeon RX 7900 XT", 470, 20, False, []),
    ("AMD Radeon RX 7900 XTX", 530, 24, False, []),
    ("AMD Radeon RX 9060 XT", 290, 16, False, []), ("AMD Radeon RX 9070", 430, 16, False, []),
    ("AMD Radeon RX 9070 XT", 480, 16, False, []),
    ("AMD Radeon Vega 8 Graphics", 22, None, True, ["Radeon Vega 8"]),
    ("AMD Radeon 780M", 60, None, True, []),
    ("Intel HD Graphics 4000", 5, None, True, ["Intel HD 4000"]),
    ("Intel HD Graphics 530", 8, None, True, []), ("Intel HD Graphics 620", 9, None, True, []),
    ("Intel UHD Graphics 620", 9, None, True, []), ("Intel UHD Graphics 630", 10, None, True, []),
    ("Intel UHD Graphics 730", 12, None, True, []), ("Intel UHD Graphics 770", 12, None, True, []),
    ("Intel Iris Xe Graphics", 25, None, True, ["Intel Iris Xe"]),
    ("Intel Arc A380", 75, 6, False, []), ("Intel Arc A580", 175, 8, False, []),
    ("Intel Arc A750", 200, 8, False, []), ("Intel Arc A770", 215, 16, False, []),
    ("Intel Arc B580", 250, 12, False, []),
]

W10 = {"windows": 10}


def tier(cpu, gpu, ram, storage, vram=None, os=W10, ssd=False):
    out = {"cpu": cpu, "gpu": gpu, "ram_gb": ram, "storage_gb": storage, "os": os}
    if vram is not None:
        out["vram_gb"] = vram
    if ssd:
        out["ssd"] = True
    return out


GAMES = [
    {
        "id": "cyberpunk-2077", "name": "Cyberpunk 2077",
        "source": "https://store.steampowered.com/app/1091500/",
        "minimum": tier(["Intel Core i7-6700", "AMD Ryzen 5 1600"],
                        ["NVIDIA GeForce GTX 1060 6GB", "AMD Radeon RX 580", "Intel Arc A380"], 12, 70, vram=6, ssd=True),
        "recommended": tier(["Intel Core i7-12700", "AMD Ryzen 7 7800X3D"],
                            ["NVIDIA GeForce RTX 2060 SUPER", "AMD Radeon RX 5700 XT", "Intel Arc A770"], 16, 70, vram=8, ssd=True),
    },
    {
        "id": "elden-ring", "name": "Elden Ring",
        "source": "https://store.steampowered.com/app/1245620/",
        "minimum": tier(["Intel Core i5-8400", "AMD Ryzen 3 3300X"],
                        ["NVIDIA GeForce GTX 1060 3GB", "AMD Radeon RX 580"], 12, 60, vram=3),
        "recommended": tier(["Intel Core i7-8700K", "AMD Ryzen 5 3600X"],
                            ["NVIDIA GeForce GTX 1070", "AMD Radeon RX Vega 56"], 16, 60, vram=8),
    },
    {
        "id": "red-dead-redemption-2", "name": "Red Dead Redemption 2",
        "source": "https://store.steampowered.com/app/1174180/",
        "minimum": tier(["Intel Core i5-2500K", "AMD FX-6300"],
                        ["NVIDIA GeForce GTX 770", "AMD Radeon R9 280"], 8, 150, vram=2),
        "recommended": tier(["Intel Core i7-4770K", "AMD Ryzen 5 1500X"],
                            ["NVIDIA GeForce GTX 1060 6GB", "AMD Radeon RX 480"], 12, 150, vram=4),
    },
    {
        "id": "gta-v", "name": "Grand Theft Auto V",
        "source": "https://store.steampowered.com/app/271590/",
        "minimum": tier(["Intel Core 2 Quad Q6600", "AMD Phenom 9850"],
                        ["NVIDIA GeForce 9800 GT", "AMD Radeon HD 4870"], 4, 110, vram=1),
        "recommended": tier(["Intel Core i5-3470", "AMD FX-8350"],
                            ["NVIDIA GeForce GTX 660", "AMD Radeon HD 7870"], 8, 110, vram=2),
    },
    {
        "id": "baldurs-gate-3", "name": "Baldur's Gate 3",
        "source": "https://store.steampowered.com/app/1086940/",
        "minimum": tier(["Intel Core i5-4690", "AMD FX-8350"],
                        ["NVIDIA GeForce GTX 970", "AMD Radeon RX 480"], 8, 150, vram=4, ssd=True),
        "recommended": tier(["Intel Core i7-8700K", "AMD Ryzen 5 3600"],
                            ["NVIDIA GeForce RTX 2060 SUPER", "AMD Radeon RX 5700 XT"], 16, 150, vram=8, ssd=True),
    },
    {
        "id": "hogwarts-legacy", "name": "Hogwarts Legacy",
        "source": "https://store.steampowered.com/app/990080/",
        "minimum": tier(["Intel Core i5-6600", "AMD Ryzen 5 1400"],
                        ["NVIDIA GeForce GTX 960", "AMD Radeon RX 470", "Intel Arc A380"], 16, 85, vram=4, ssd=True),
        "recommended": tier(["Intel Core i7-8700", "AMD Ryzen 5 3600"],
                            ["NVIDIA GeForce GTX 1080 Ti", "AMD Radeon RX 5700 XT", "Intel Arc A770"], 16, 85, vram=8, ssd=True),
    },
    {
        "id": "black-myth-wukong", "name": "Black Myth: Wukong",
        "source": "https://store.steampowered.com/app/2358720/",
        "minimum": tier(["Intel Core i5-8400", "AMD Ryzen 5 1600"],
                        ["NVIDIA GeForce GTX 1060 6GB", "AMD Radeon RX 580"], 16, 130, vram=6, ssd=True),
        "recommended": tier(["Intel Core i7-9700", "AMD Ryzen 5 5500"],
                            ["NVIDIA GeForce RTX 2060", "AMD Radeon RX 5700 XT", "Intel Arc A750"], 16, 130, vram=6, ssd=True),
    },
    {
        "id": "forza-horizon-5", "name": "Forza Horizon 5",
        "source": "https://store.steampowered.com/app/1551360/",
        "minimum": tier(["Intel Core i5-4460", "AMD Ryzen 3 1200"],
                        ["NVIDIA GeForce GTX 970", "AMD Radeon RX 470"], 8, 110, vram=4),
        "recommended": tier(["Intel Core i5-8400", "AMD Ryzen 5 1500X"],
                            ["NVIDIA GeForce GTX 1070", "AMD Radeon RX 590"], 16, 110, vram=8),
    },
    {
        "id": "the-witcher-3", "name": "The Witcher 3: Wild Hunt (Next-Gen)",
        "source": "https://store.steampowered.com/app/292030/",
        "minimum": tier(["Intel Core i5-2500K", "AMD Phenom II X4 940"],
                        ["NVIDIA GeForce GTX 770", "AMD Radeon R9 290"], 8, 50, vram=2),
        "recommended": tier(["Intel Core i7-6700K", "AMD Ryzen 5 1600"],
                            ["NVIDIA GeForce GTX 1070", "AMD Radeon RX 480"], 12, 50, vram=4),
    },
    {
        "id": "pubg", "name": "PUBG: Battlegrounds",
        "source": "https://store.steampowered.com/app/578080/",
        "minimum": tier(["Intel Core i5-4430", "AMD FX-6300"],
                        ["NVIDIA GeForce GTX 960", "AMD Radeon R7 370"], 8, 40, vram=2),
        "recommended": tier(["Intel Core i5-6600K", "AMD Ryzen 5 1600"],
                            ["NVIDIA GeForce GTX 1060 3GB", "AMD Radeon RX 580"], 16, 50, vram=3),
    },
    {
        "id": "apex-legends", "name": "Apex Legends",
        "source": "https://store.steampowered.com/app/1172470/",
        "minimum": tier(["Intel Core i3-6300", "AMD FX-4350"],
                        ["NVIDIA GeForce GT 640", "AMD Radeon HD 7770"], 6, 75, vram=1),
        "recommended": tier(["Intel Core i5-3570K"],
                            ["NVIDIA GeForce GTX 970", "AMD Radeon R9 290"], 8, 75, vram=4),
    },
    {
        "id": "counter-strike-2", "name": "Counter-Strike 2",
        "source": "https://store.steampowered.com/app/730/",
        "minimum": tier(["Intel Core i5-750"], [], 8, 85, vram=1),
    },
    {
        "id": "valorant", "name": "VALORANT",
        "source": "https://playvalorant.com/",
        "minimum": tier(["Intel Core 2 Duo E8400", "AMD Athlon 200GE"],
                        ["Intel HD Graphics 4000", "AMD Radeon R5 200 Series"], 4, 30, vram=1),
        "recommended": tier(["Intel Core i3-4150", "AMD Ryzen 3 1200"],
                            ["NVIDIA GeForce GT 730", "AMD Radeon R7 240"], 4, 30, vram=1),
    },
    {
        "id": "fortnite", "name": "Fortnite",
        "source": "https://www.fortnite.com/technical-specifications",
        "minimum": tier(["Intel Core i3-3225"],
                        ["Intel HD Graphics 4000", "AMD Radeon Vega 8 Graphics"], 8, 30),
        "recommended": tier(["Intel Core i5-7300U", "AMD Ryzen 3 3300U"],
                            ["NVIDIA GeForce GTX 960", "AMD Radeon R9 280"], 16, 30, vram=2),
    },
]


def main():
    library = {
        "schema_version": SCHEMA_VERSION,
        "library_version": LIBRARY_VERSION,
        "updated": date.today().isoformat(),
        "cpus": [{"name": n, "score": s} for n, s in CPUS],
        "gpus": [
            dict({"name": n, "score": s}, **({"vram_gb": v} if v else {}),
                 **({"integrated": True} if i else {}), **({"keys": [n] + k} if k else {}))
            for n, s, v, i, k in GPUS
        ],
        "games": GAMES,
    }
    out = Path(__file__).resolve().parent.parent / "gamecheck" / "data" / "library.json"
    out.write_text(json.dumps(library, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(CPUS)} CPUs, {len(GPUS)} GPUs, {len(GAMES)} games)")


if __name__ == "__main__":
    main()
