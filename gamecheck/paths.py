"""Locations of bundled resources and the per-user data folder."""

import os
import sys
from pathlib import Path


def resource_dir() -> Path:
    """Folder holding bundled read-only files (works in source and PyInstaller builds)."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / "gamecheck"
    return Path(__file__).resolve().parent


def bundled_library_path() -> Path:
    return resource_dir() / "data" / "library.json"


def web_dir() -> Path:
    return resource_dir() / "web"


def user_data_dir() -> Path:
    """Writable folder for the downloaded library copy and settings.

    Nothing here identifies the user; it only holds game data and local preferences.
    """
    override = os.environ.get("GAMECHECK_DATA_DIR")
    if override:
        path = Path(override)
    elif sys.platform == "win32":
        root = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        path = Path(root) / "GameCheck"
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / "GameCheck"
    else:
        root = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        path = Path(root) / "gamecheck"
    path.mkdir(parents=True, exist_ok=True)
    return path
