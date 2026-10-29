"""Compare a scanned computer with a game's minimum and recommended requirements.

Per component the status is one of:
  recommended  meets or beats the recommended spec
  minimum      meets the minimum but not the recommended spec
  borderline   up to BORDERLINE_MARGIN below the minimum: may run, with low settings
  below        clearly under the minimum
  unknown      we could not identify the part, so we say so rather than guess
"""

from .hardware_db import LAPTOP_GPU_FACTOR, cpu_table, gpu_table, is_laptop_gpu

BORDERLINE_MARGIN = 0.10   # performance scores are estimates; within 10% below is "borderline"
RAM_TOLERANCE = 0.95       # "16 GB" kits report ~15.9 GB; don't fail a game over that

RANK = {"below": 0, "unknown": 1, "borderline": 2, "minimum": 3, "recommended": 4}

LABELS = {
    "cpu": "Processor", "gpu": "Graphics card", "vram": "Video memory (GB)",
    "ram": "Memory (GB)", "storage": "Free disk space (GB)", "os": "Operating system",
}

NOTES = {
    "cpu_unrecognised": "Processor model not recognised",
    "gpu_unrecognised": "Graphics card not recognised: pick it manually for an accurate result",
    "laptop_gpu": "Laptop GPU: estimated at about 80% of the desktop model",
    "ssd_required": "SSD required",
    "ssd_recommended": "SSD recommended",
}

VERDICTS = {
    "recommended": "Runs well at recommended settings",
    "minimum": "Runs at minimum settings",
    "borderline": "Might run, at low settings",
    "unknown": "Could not confirm: some parts were not recognised",
    "below": "Below minimum requirements",
}


class Analyzer:
    def __init__(self, library: dict):
        self.library = library
        self.cpus = cpu_table(library)
        self.gpus = gpu_table(library)

    # ---------- the user's machine

    def describe_system(self, system: dict, cpu_override=None, gpu_override=None) -> dict:
        """Resolve detected names to table entries. Overrides are names picked by the user."""
        cpu_entry = self.cpus.by_name(cpu_override) if cpu_override else None
        cpu_entry = cpu_entry or self.cpus.match(system["cpu"]["name"])

        cpu_manual = bool(cpu_override and cpu_entry and cpu_entry.name == cpu_override)
        detected_gpus = [g["name"] for g in system.get("gpus", [])]
        best = None
        if gpu_override and self.gpus.by_name(gpu_override):
            entry = self.gpus.by_name(gpu_override)
            best = {"name": entry.name, "entry": entry, "laptop": False, "vram_gb": entry.vram_gb}
        else:
            # Laptops often have an integrated and a dedicated GPU: games use the stronger one.
            for gpu in system.get("gpus", []):
                entry = self.gpus.match(gpu["name"])
                laptop = is_laptop_gpu(gpu["name"])
                score = entry.score * (LAPTOP_GPU_FACTOR if laptop else 1) if entry else -1
                if best is None or score > best["score"]:
                    best = {"name": gpu["name"], "entry": entry, "laptop": laptop,
                            "vram_gb": gpu.get("vram_gb"), "score": score}
        gpu_score = None
        vram = None
        integrated = False
        if best and best["entry"]:
            gpu_score = best["entry"].score * (LAPTOP_GPU_FACTOR if best["laptop"] else 1)
            integrated = best["entry"].integrated
            # Trust the driver-reported VRAM; fall back to the model's usual size.
            vram = best["vram_gb"] if best["vram_gb"] else best["entry"].vram_gb
        elif best:
            vram = best["vram_gb"]
        free = max((d["free_gb"] for d in system.get("disks", [])), default=None)
        return {
            "cpu_name": system["cpu"]["name"],
            "cpu_model": cpu_entry.name if cpu_entry else None,
            "cpu_score": cpu_entry.score if cpu_entry else None,
            "cpu_manual": cpu_manual,
            "gpu_name": best["name"] if best else None,
            "gpu_model": best["entry"].name if best and best["entry"] else None,
            "gpu_score": gpu_score,
            "gpu_manual": bool(best and gpu_override and best["name"] == gpu_override),
            "gpu_detected": ", ".join(detected_gpus) or None,
            "gpu_laptop": bool(best and best["laptop"]),
            "gpu_integrated": integrated,
            "vram_gb": vram,
            "ram_gb": system.get("ram_gb"),
            "free_disk_gb": free,
            "os": system.get("os", {}),
        }

    # ---------- requirements

    def _required_score(self, table, names):
        """Lowest score among the listed alternatives (any one of them is enough)."""
        scores = [e.score for e in (table.match(n) for n in names) if e]
        return min(scores) if scores else None

    @staticmethod
    def _grade(value, minimum, recommended, borderline=True):
        if minimum is None and recommended is None:
            return None
        if value is None:
            return "unknown"
        if recommended is not None and value >= recommended:
            return "recommended"
        if minimum is None or value >= minimum:
            return "minimum"
        if borderline and value >= minimum * (1 - BORDERLINE_MARGIN):
            return "borderline"
        return "below"

    def check(self, game: dict, me: dict) -> dict:
        minimum = game.get("minimum") or {}
        rec = game.get("recommended") or {}
        components = []

        def add(key, yours, req_min, req_rec, status, note=None):
            if status is None:
                return
            components.append({"key": key, "label": LABELS[key], "yours": yours, "minimum": req_min,
                               "recommended": req_rec, "status": status, "note": note})

        cmin = self._required_score(self.cpus, minimum.get("cpu", []))
        crec = self._required_score(self.cpus, rec.get("cpu", []))
        add("cpu", me["cpu_model"] or me["cpu_name"], minimum.get("cpu"), rec.get("cpu"),
            self._grade(me["cpu_score"], cmin, crec),
            None if me["cpu_score"] is not None else "cpu_unrecognised")

        gmin = self._required_score(self.gpus, minimum.get("gpu", []))
        grec = self._required_score(self.gpus, rec.get("gpu", []))
        gnote = None
        if me["gpu_score"] is None:
            gnote = "gpu_unrecognised"
        elif me["gpu_laptop"]:
            gnote = "laptop_gpu"
        add("gpu", me["gpu_model"] or me["gpu_name"], minimum.get("gpu"), rec.get("gpu"),
            self._grade(me["gpu_score"], gmin, grec), gnote)

        vmin, vrec = minimum.get("vram_gb"), rec.get("vram_gb")
        if not me["gpu_integrated"]:
            add("vram", me["vram_gb"], vmin, vrec, self._grade(me["vram_gb"], vmin, vrec, borderline=False))

        rmin, rrec = minimum.get("ram_gb"), rec.get("ram_gb")
        ram = me["ram_gb"] / RAM_TOLERANCE if me["ram_gb"] else None
        add("ram", me["ram_gb"], rmin, rrec, self._grade(ram, rmin, rrec, borderline=False))

        smin, srec = minimum.get("storage_gb"), rec.get("storage_gb")
        snote = "ssd_required" if minimum.get("ssd") else ("ssd_recommended" if rec.get("ssd") else None)
        add("storage", me["free_disk_gb"], smin, srec,
            self._grade(me["free_disk_gb"], smin, srec, borderline=False), snote)

        add("os", me["os"].get("name"), _os_label(minimum.get("os")), None,
            _os_status(minimum.get("os"), me["os"]))

        # Free disk space is something the user can fix, so it is reported as a warning
        # and does not decide whether the hardware can run the game.
        hardware = [c for c in components if c["key"] != "storage"]
        overall = min((c["status"] for c in hardware), key=RANK.__getitem__, default="unknown")
        # Components without a recommended spec stop at "minimum"; they shouldn't hold back
        # a machine that beats every recommended spec the game does list.
        if overall == "minimum" and rec and all(c["status"] == "recommended" for c in hardware
                                                if c["recommended"] is not None):
            overall = "recommended"
        storage = next((c for c in components if c["key"] == "storage"), None)
        return {
            "id": game["id"], "name": game["name"], "source": game.get("source"),
            "has_recommended": bool(rec), "overall": overall, "verdict": VERDICTS[overall],
            "components": components,
            "weakest": [c["key"] for c in hardware if c["status"] in ("below", "borderline")],
            "needs_disk_space": bool(storage and storage["status"] == "below"),
        }

    def check_all(self, me: dict) -> list:
        return [self.check(game, me) for game in self.library["games"]]


def _os_label(req):
    return f"Windows {req['windows']} 64-bit" if req and req.get("windows") else None


def _os_status(req, os_info):
    if not req or not req.get("windows"):
        return None
    if os_info.get("family") != "windows":
        return "unknown"
    if os_info.get("is_64bit") is False:
        return "below"
    version = os_info.get("version")
    if version is None:
        return "unknown"
    return "recommended" if version >= req["windows"] else "below"
