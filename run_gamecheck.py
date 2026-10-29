"""Launcher used by PyInstaller (it cannot run a package's __main__ directly)."""

import sys

from gamecheck.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
