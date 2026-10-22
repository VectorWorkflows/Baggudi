#!/usr/bin/env python3
"""Serve the built site on the local network, so it can be opened on a phone.

    python serve.py                 serves dist/ on 0.0.0.0:8000
    python serve.py some-folder     serves another build folder
    python serve.py --port 8080

Missing paths get 404.html with status 404 (hi/404.html under /hi/). If the site was built with
--base /rcc/, it is served under /rcc/ so every link works.
"""
import argparse
import json
import socket
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent


def lan_ip():
    """This machine's address on the local network (no packets are sent)."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def make_handler(folder, base):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(folder), **kwargs)

        def resolve(self):
            """The file this request maps to, or None."""
            path = unquote(urlsplit(self.path).path)
            if not path.startswith(base):
                return None
            target = (folder / path[len(base):]).resolve()
            if folder not in target.parents and target != folder:
                return None
            if target.is_dir():
                target = target / "index.html"
            return target if target.is_file() and not target.name.startswith(".") else None

        def send_head(self):
            path = unquote(urlsplit(self.path).path)
            target = self.resolve()
            if target is None:
                return self.not_found()
            # Folders are always addressed with a trailing slash.
            if target.name == "index.html" and not path.endswith(("/", "index.html")):
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                self.send_header("Location", path + "/")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            return self.send_file(target, HTTPStatus.OK)

        def not_found(self):
            # Hindi paths get the Hindi page.
            path = unquote(urlsplit(self.path).path)
            page = folder / "hi" / "404.html"
            if not (path.startswith(base + "hi/") and page.is_file()):
                page = folder / "404.html"
            if page.is_file():
                return self.send_file(page, HTTPStatus.NOT_FOUND)
            self.send_error(HTTPStatus.NOT_FOUND)
            return None

        def send_file(self, target, status):
            handle = target.open("rb")
            self.send_response(status)
            self.send_header("Content-Type", self.guess_type(str(target)))
            self.send_header("Content-Length", str(target.stat().st_size))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            return handle

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Serve the built site on the local network.")
    parser.add_argument("folder", nargs="?", default="dist", help="build folder to serve (default dist)")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    folder = (ROOT / args.folder).resolve()  # an absolute folder replaces ROOT
    if not (folder / "index.html").is_file():
        sys.exit(f"Nothing to serve in {folder}. Run: python build.py --draft")
    marker = folder / ".build.json"
    base = json.loads(marker.read_text(encoding="utf-8"))["base"] if marker.is_file() else "/"

    server = ThreadingHTTPServer(("0.0.0.0", args.port), make_handler(folder, base))
    path = "" if base == "/" else base
    print(f"Open on your phone: http://{lan_ip()}:{args.port}{path}")
    print(f"On this computer:   http://localhost:{args.port}{path}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
