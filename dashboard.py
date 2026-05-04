"""Run the dashboard: collect fresh data → serve web/ on localhost → open browser."""

from __future__ import annotations

import argparse
import http.server
import os
import socketserver
import sys
import threading
import webbrowser
from pathlib import Path

from collector.collect import main as collect_main

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"


def serve(port: int, open_browser: bool):
    os.chdir(WEB_DIR)
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        url = f"http://localhost:{port}"
        print(f"\n  Dashboard live at  {url}")
        print("  Ctrl+C to stop.\n")
        if open_browser:
            threading.Timer(0.6, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  bye")


def main():
    ap = argparse.ArgumentParser(description="Claude Dashboard launcher")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--no-collect", action="store_true",
                    help="Skip data refresh, just serve existing data.json")
    ap.add_argument("--no-admin", action="store_true",
                    help="Skip Anthropic Admin API fetch (local logs only)")
    args = ap.parse_args()

    if not args.no_collect:
        collect_main(skip_admin=args.no_admin)

    serve(args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
