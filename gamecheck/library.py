"""Game library: bundled copy, cached downloaded copy, and the optional online update.

The program never needs the internet. It ships with a library inside the EXE; when the
user presses "Update library" and is online, a newer library is downloaded, validated
and saved to the user data folder, and that saved copy is used from then on (also
offline). A failed or invalid download never replaces the working copy.

The update request is a plain HTTPS GET with no identifiers, cookies or query string.
"""

import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from . import __version__
from .paths import bundled_library_path, user_data_dir

SUPPORTED_SCHEMA = 1
MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024
CACHED_FILENAME = "library.json"
SETTINGS_FILENAME = "settings.json"

# Where "Update library" downloads from. Set this to the raw URL of library.json in your
# own public repository (see docs/UPDATING_LIBRARY.md) before building the EXE; users
# can also override it in settings.json. Empty means the update button explains that no
# update source is configured.
DEFAULT_LIBRARY_URL = ""


class LibraryError(ValueError):
    pass


def validate(library: dict) -> dict:
    """Raise LibraryError unless `library` is structurally usable."""
    if not isinstance(library, dict):
        raise LibraryError("library must be a JSON object")
    if library.get("schema_version") != SUPPORTED_SCHEMA:
        raise LibraryError(f"unsupported schema_version {library.get('schema_version')!r}")
    if not isinstance(library.get("library_version"), int):
        raise LibraryError("library_version must be an integer")
    for table in ("cpus", "gpus"):
        rows = library.get(table)
        if not isinstance(rows, list) or not rows:
            raise LibraryError(f"{table} must be a non-empty list")
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("name"), str):
                raise LibraryError(f"{table}: every entry needs a name")
            if not isinstance(row.get("score"), (int, float)) or row["score"] <= 0:
                raise LibraryError(f"{table}: {row.get('name')!r} needs a positive score")
    games = library.get("games")
    if not isinstance(games, list) or not games:
        raise LibraryError("games must be a non-empty list")
    seen = set()
    for game in games:
        if not isinstance(game, dict) or not isinstance(game.get("id"), str) or not isinstance(game.get("name"), str):
            raise LibraryError("every game needs an id and a name")
        if game["id"] in seen:
            raise LibraryError(f"duplicate game id {game['id']!r}")
        seen.add(game["id"])
        if not isinstance(game.get("minimum"), dict):
            raise LibraryError(f"{game['id']}: minimum requirements missing")
        for tier_name in ("minimum", "recommended"):
            tier = game.get(tier_name)
            if tier is None:
                continue
            if not isinstance(tier, dict):
                raise LibraryError(f"{game['id']}: {tier_name} must be an object")
            for key in ("cpu", "gpu"):
                if not isinstance(tier.get(key, []), list):
                    raise LibraryError(f"{game['id']}: {tier_name}.{key} must be a list")
            for key in ("ram_gb", "vram_gb", "storage_gb"):
                if key in tier and not isinstance(tier[key], (int, float)):
                    raise LibraryError(f"{game['id']}: {tier_name}.{key} must be a number")
    return library


def _read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def cached_library_path() -> Path:
    return user_data_dir() / CACHED_FILENAME


def load() -> tuple:
    """Return (library, source) where source is 'bundled' or 'downloaded'.

    The downloaded copy is used only if it is valid and newer than the bundled one,
    so installing a newer program version never falls back to older game data.
    """
    bundled = validate(_read_json(bundled_library_path()))
    path = cached_library_path()
    if path.exists():
        try:
            cached = validate(_read_json(path))
            if cached["library_version"] > bundled["library_version"]:
                return cached, "downloaded"
        except (OSError, ValueError):
            pass  # corrupt or outdated cache: keep using the bundled library
    return bundled, "bundled"


def load_settings() -> dict:
    try:
        data = _read_json(user_data_dir() / SETTINGS_FILENAME)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(settings: dict) -> None:
    _atomic_write(user_data_dir() / SETTINGS_FILENAME, json.dumps(settings, ensure_ascii=False, indent=1))


def library_url() -> str:
    return load_settings().get("library_url") or DEFAULT_LIBRARY_URL


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def _download(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": f"GameCheck/{__version__}"})
    context = ssl.create_default_context()
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        data = response.read(MAX_DOWNLOAD_BYTES + 1)
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise LibraryError("downloaded library is too large")
    return data


def update(current_version: int, url: Optional[str] = None, timeout: float = 15.0,
           allow_insecure_http: bool = False) -> dict:
    """Try to download a newer library. Never raises; returns a status dict.

    status: 'updated' | 'up_to_date' | 'offline' | 'invalid' | 'not_configured'
    """
    url = url if url is not None else library_url()
    if not url:
        return {"status": "not_configured"}
    if not url.lower().startswith("https://") and not allow_insecure_http:
        return {"status": "invalid", "detail": "update URL must use https://"}
    try:
        raw = _download(url, timeout)
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return {"status": "offline", "detail": str(getattr(exc, "reason", exc))}
    except LibraryError as exc:
        return {"status": "invalid", "detail": str(exc)}
    try:
        library = validate(json.loads(raw.decode("utf-8")))
    except (UnicodeDecodeError, ValueError) as exc:
        return {"status": "invalid", "detail": str(exc)}
    if library["library_version"] <= current_version:
        return {"status": "up_to_date", "library_version": current_version}
    _atomic_write(cached_library_path(), json.dumps(library, ensure_ascii=False))
    return {"status": "updated", "library_version": library["library_version"],
            "games": len(library["games"])}
