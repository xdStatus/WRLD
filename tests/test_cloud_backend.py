"""Test private Cloudflare streaming client without network or real credentials."""
import json
import unittest
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import ssl
import socket
import cloud_backend

class Response:
    def __init__(self,data,url):
        self.data=BytesIO(data);self.url=url;self.headers={}
    def read(self,n=-1):return self.data.read(n)
    def geturl(self):return self.url
    def close(self):pass
    def __enter__(self):return self
    def __exit__(self,*args):pass

class CloudBackendTests(unittest.TestCase):
    def test_library_and_no_exposed_key(self):
        data={"tracks":[{"id":"My Song.mp3","title":"My Song","size":15000,
            "artist":"Juice WRLD","streamPath":"/api/stream/My%20Song.mp3"}]}
        def fake_open(req,timeout):
            self.assertEqual(req.get_header("Authorization"),"Bearer "+"f"*64)
            self.assertEqual(req.get_header("User-agent"),"WRLD-Player/1.8.11")
            self.assertEqual(req.full_url,cloud_backend.WORKER_ORIGIN+"/api/tracks")
            return Response(json.dumps(data).encode(),req.full_url)
        with patch.object(cloud_backend,"_read_token",return_value="f"*64), \
             patch.object(cloud_backend._https_opener,"open",side_effect=fake_open):
            found=cloud_backend.list_tracks()
        self.assertEqual(found["count"],1)
        self.assertEqual(found["tracks"][0]["title"],"My Song")
        self.assertNotIn("f"*64,str(found))
        self.assertEqual(cloud_backend._remote_tracks[found["tracks"][0]["id"]],
                         "/api/stream/My%20Song.mp3")
    def test_redirects_disabled(self):
        self.assertIsNone(cloud_backend._BlockRedirects().redirect_request(
            None,None,302,"Found",{},"https://example.com/"))
        with patch.object(cloud_backend,"_read_token",return_value="f"*64), \
             patch.object(cloud_backend._https_opener,"open",side_effect=HTTPError(
                 cloud_backend.WORKER_ORIGIN+"/api/tracks",302,"Found",{},None)):
            with self.assertRaisesRegex(cloud_backend.CloudError,"302"):
                cloud_backend.list_tracks()
    def test_safe_connection_diagnostics(self):
        cases = [
            (URLError(ssl.SSLCertVerificationError("certificate problem")), "certificate verification"),
            (URLError(socket.timeout("timeout")), "timed out"),
            (URLError(socket.gaierror(-2, "DNS failure")), "DNS lookup"),
            (URLError(ConnectionResetError(10054, "reset")), "reset"),
        ]
        for error, expected in cases:
            with self.subTest(expected=expected):
                message = str(cloud_backend._connection_error(error))
                self.assertIn(expected, message)
                self.assertNotIn("Bearer", message)

    def test_status_has_no_token(self):
        self.assertEqual(cloud_backend.WORKER_ORIGIN,
                         "https://wrld-cloud.zaavangonzaless.workers.dev")
        self.assertNotIn("token",str(cloud_backend.cloud_status()))

if __name__=="__main__":
    unittest.main()
