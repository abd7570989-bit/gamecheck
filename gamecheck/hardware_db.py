"""Turn free-form CPU/GPU names into entries of the hardware table.

Detected names ("Intel(R) Core(TM) i5-4460  CPU @ 3.20GHz") and the names written in
game requirements ("Intel Core i5-4460") are normalised the same way, then matched
against each table entry's keys. A key only matches on token boundaries and the
longest matching key wins, so "rtx 3060 ti" beats "rtx 3060" and "rx 570" never
matches "rx 5700". Anything unrecognised returns None: the comparison then reports
"unknown" instead of guessing.
"""

import re
from dataclasses import dataclass
from typing import Optional

_TRADEMARKS = re.compile(r"\((?:r|tm|c)\)|[®™]")
_SPACES = re.compile(r"\s+")

# Laptop GPUs share names with desktop parts but run at lower clocks and power.
LAPTOP_GPU_FACTOR = 0.8
_LAPTOP_GPU = re.compile(r"\b(laptop|mobile|max-q|max q)\b")


def normalize_cpu(name: str) -> str:
    s = _TRADEMARKS.sub(" ", name.lower())
    s = s.split("@")[0]
    s = re.sub(r"\b\d+(?:st|nd|rd|th) gen\b", " ", s)
    s = re.sub(r"\b(?:\d+|six|eight|quad|dual|twelve|sixteen)[- ]core\b", " ", s)
    s = re.sub(r"\bwith radeon(?: vega)?(?: mobile)? graphics\b", " ", s)
    s = re.sub(r"\b(?:processor|cpu|intel|amd|apu)\b", " ", s)
    s = s.replace("core2", "core 2")
    s = re.sub(r"\bcore\s+(i[3579])\b", r"\1", s)
    s = re.sub(r"\bcore\s+(ultra)\b", r"\1", s)
    s = re.sub(r"\b(i[3579])\s*-?\s*(\d{3,5})", r"\1-\2", s)
    # F / KF parts are the same chip without integrated graphics.
    s = re.sub(r"\b(i[3579]-\d{4,5}k?)f\b", r"\1", s)
    s = re.sub(r"\b(ultra [3579] \d{3}k?)f\b", r"\1", s)
    s = re.sub(r"\bfx\s*-?\s*(\d{4})", r"fx-\1", s)
    s = re.sub(r"\b(a\d{1,2})\s*-?\s*(\d{4}k?)\b", r"\1-\2", s)
    return _SPACES.sub(" ", s).strip()


def normalize_gpu(name: str) -> str:
    s = _TRADEMARKS.sub(" ", name.lower())
    s = re.sub(r"\b(?:nvidia|geforce|amd|ati|radeon|intel|corporation|series)\b", " ", s)
    s = re.sub(r"\b(laptop|mobile) gpu\b", r"\1", s)
    s = s.replace("-", " ")
    s = re.sub(r"(\d)(ti|super|xtx|xt|gre)\b", r"\1 \2", s)
    s = re.sub(r"(\d+)\s*gb\b", r"\1gb", s)
    return _SPACES.sub(" ", s).strip()


def is_laptop_gpu(name: str) -> bool:
    return bool(_LAPTOP_GPU.search(_TRADEMARKS.sub(" ", name.lower()).replace("-", " ")))


def _contains_key(text: str, key: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])", text) is not None


@dataclass(frozen=True)
class HardwareEntry:
    name: str
    score: float
    keys: tuple
    vram_gb: Optional[float] = None
    integrated: bool = False


class HardwareTable:
    def __init__(self, entries, normalize):
        self._normalize = normalize
        self.entries = []
        self._by_key = []
        for raw in entries:
            keys = tuple(normalize(k) for k in raw.get("keys") or [raw["name"]])
            entry = HardwareEntry(
                name=raw["name"],
                score=float(raw["score"]),
                keys=keys,
                vram_gb=raw.get("vram_gb"),
                integrated=bool(raw.get("integrated", False)),
            )
            self.entries.append(entry)
            for key in keys:
                self._by_key.append((key, entry))
        # Longest key first so the most specific model wins.
        self._by_key.sort(key=lambda item: len(item[0]), reverse=True)

    def match(self, name: str) -> Optional[HardwareEntry]:
        if not name:
            return None
        text = self._normalize(name)
        for key, entry in self._by_key:
            if _contains_key(text, key):
                return entry
        return None

    def by_name(self, name: str) -> Optional[HardwareEntry]:
        for entry in self.entries:
            if entry.name == name:
                return entry
        return None


def cpu_table(library: dict) -> HardwareTable:
    return HardwareTable(library["cpus"], normalize_cpu)


def gpu_table(library: dict) -> HardwareTable:
    return HardwareTable(library["gpus"], normalize_gpu)
