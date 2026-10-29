# PyInstaller build recipe. Build with:  pyinstaller --noconfirm gamecheck.spec
# Produces a single file: dist/GameCheck.exe on Windows (dist/GameCheck elsewhere).
a = Analysis(
    ["run_gamecheck.py"],
    datas=[("gamecheck/data/library.json", "gamecheck/data"), ("gamecheck/web/index.html", "gamecheck/web")],
    # Not used by GameCheck; leaving them out keeps the EXE small.
    excludes=["tkinter", "unittest", "pydoc", "doctest", "lib2to3", "sqlite3", "xmlrpc", "pytest"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas,
    name="GameCheck",
    console=True,      # the small console window shows the address and closing it quits the app
    upx=False,         # UPX-packed EXEs trigger more antivirus false positives
    icon=None,
    version="version_info.txt" if __import__("sys").platform == "win32" else None,
)
