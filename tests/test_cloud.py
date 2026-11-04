"""WRLD Cloud API checks: read-only, loopback, metadata, ranged music."""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import player
from cloud_server import create_cloud_server


class CloudServerTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        (Path(self.folder.name) / "TestSong.mp3").write_bytes(b"cloud-test-1234567890")
        player.rebuild(self.folder.name)
        self.server = create_cloud_server()
        self.addCleanup(self.server.server_close)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.addCleanup(self.server.shutdown)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def fetch(self, path, headers=None, method="GET"):
        return urlopen(Request(self.base + path, headers=headers or {}, method=method), timeout=5)

    def test_loopback_and_metadata(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        with self.fetch("/cloud/tracks") as response:
            data = json.load(response)
        self.assertEqual(data["count"], 1)
        track = data["tracks"][0]
        self.assertEqual(track["title"], "TestSong")
        self.assertNotIn("path", track)
        self.assertNotIn("relative", track)
        self.assertNotIn("folder", data)

    def test_audio_range_and_read_only(self):
        with self.fetch("/cloud/tracks") as response:
            song_id = json.load(response)["tracks"][0]["id"]
        with self.fetch("/cloud/media/" + song_id, {"Range": "bytes=0-4"}) as response:
            self.assertEqual(response.status, 206)
            self.assertEqual(response.read(), b"cloud")
            self.assertEqual(response.headers.get("Accept-Ranges"), "bytes")
        for path in ("/api/tracks", "/api/collections", "/"):
            with self.assertRaises(HTTPError) as error:
                self.fetch(path)
            self.assertEqual(error.exception.code, 404)
        with self.assertRaises(HTTPError) as error:
            self.fetch("/cloud/tracks", method="POST")
        self.assertEqual(error.exception.code, 405)
        with self.assertRaises(HTTPError) as error:
            self.fetch("/cloud/tracks", {"Origin": "https://example.com"})
        self.assertEqual(error.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
