#!/usr/bin/env python3
"""Private, read-only Windows music API. Expose via Tailscale Serve ONLY."""
from __future__ import annotations

import re
import threading
from http.server import ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

from player import Handler, public_tracks

CLOUD_HOST = "127.0.0.1"
CLOUD_PORT = 18766


class CloudHandler(Handler):
    server_version = "WRLDCloud/0.1"

    def do_GET(self):
        # Never enable CORS or serve dashboard/admin endpoints to remote devices.
        if self.headers.get("Origin"):
            return self.json_out(403, {"error": "Cross-origin browser requests are not supported"})
        path = unquote(urlsplit(self.path).path)
        if path == "/cloud/tracks":
            tracks = [
                {key: song.get(key) for key in
                 ("id", "title", "artist", "album", "duration", "modified", "format")}
                for song in public_tracks()["tracks"]
            ]
            return self.json_out(200, {"version": 1, "count": len(tracks), "tracks": tracks})
        if path.startswith("/cloud/media/"):
            identifier = path[len("/cloud/media/"):]
            if re.fullmatch(r"[0-9a-f]{20}", identifier):
                return self.stream_track(identifier)
        return self.json_out(404, {"error": "Not found"})

    def do_POST(self):
        return self.json_out(405, {"error": "WRLD Cloud is read-only"})

    def do_PUT(self):
        return self.do_POST()

    def do_DELETE(self):
        return self.do_POST()

    def do_HEAD(self):
        return self.do_GET()


def create_cloud_server():
    server = ThreadingHTTPServer((CLOUD_HOST, CLOUD_PORT), CloudHandler)
    server.daemon_threads = True
    return server


def start_cloud_server():
    server = create_cloud_server()
    threading.Thread(target=server.serve_forever, daemon=True,
                     name="WRLD-cloud-library").start()
    return server
