import json
import unittest
from unittest.mock import patch
import cloud_sync

class Response:
    status = 200
    def __init__(self):
        self.headers = {}
    def geturl(self):
        return cloud_sync.SYNC_URL
    def read(self, size):
        return json.dumps({"revision":1,"data":{"liked":[],"playlists":[],"history":[],"listeningMs":0}}).encode()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False

class CloudSyncTransportTests(unittest.TestCase):
    def test_authenticated_sync_matches_cloud_music_user_agent(self):
        requests = []
        def opener(request, timeout):
            requests.append(request)
            return Response()
        with patch.object(cloud_sync._https_opener, "open", side_effect=opener):
            snapshot = cloud_sync.fetch("test-only-token")
            self.assertEqual(snapshot["revision"], 1)
            self.assertEqual(requests[0].get_header("User-agent"), "WRLD-Player/1.8.38")
            self.assertEqual(requests[0].get_header("Authorization"), "Bearer test-only-token")
            self.assertEqual(requests[0].get_method(), "GET")
            cloud_sync.save("test-only-token", 0, snapshot["data"])
            self.assertEqual(requests[1].get_method(), "PUT")
            self.assertEqual(requests[1].get_header("Content-type"), "application/json")

if __name__ == "__main__":
    unittest.main()
