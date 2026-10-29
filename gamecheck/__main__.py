"""Entry point: `python -m gamecheck` or GameCheck.exe."""

import argparse
import json
import sys
import threading
import webbrowser

from . import APP_NAME, __version__


def main(argv=None):
    parser = argparse.ArgumentParser(prog=APP_NAME, description="Free, offline game compatibility checker.")
    parser.add_argument("--report", action="store_true", help="print a text report and exit (no browser)")
    parser.add_argument("--json", action="store_true", help="print the scan and results as JSON and exit")
    parser.add_argument("--update-library", action="store_true", help="download the latest game library and exit")
    parser.add_argument("--no-browser", action="store_true", help="start the interface without opening a browser")
    parser.add_argument("--port", type=int, default=0, help="local port (default: any free port)")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    args = parser.parse_args(argv)

    from .server import AppState
    from . import library as library_mod

    if args.update_library:
        state = AppState()
        result = library_mod.update(state.library["library_version"])
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["status"] in ("updated", "up_to_date") else 1

    if args.report or args.json:
        from .report import render
        state = AppState()
        me = state.me()
        results = state.analyzer.check_all(me)
        if args.json:
            print(json.dumps({"system": state.get_system(), "resolved": me, "results": results,
                              "library": state.library_info()}, ensure_ascii=False, indent=1))
        else:
            print(render(me, results, state.library_info()))
        return 0

    from .server import make_server
    server = make_server(args.port)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"{APP_NAME} {__version__}")
    print(f"Interface: {url}")
    print("Runs entirely on this computer. Close this window (or press the Exit button) to quit.", flush=True)
    if not args.no_browser:
        threading.Timer(0.3, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
