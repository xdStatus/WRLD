import unittest
from unittest.mock import patch
import cloud_collections as cc
from cloud_sync import CloudSyncConflict

BASE = {"liked": [], "playlists": [], "history": [], "listeningMs": 0}
TRACK = "r2_" + "a" * 24

class CloudCollectionTests(unittest.TestCase):
    def test_like_and_unlike(self):
        liked, _ = cc._change(BASE, {"action":"like", "track_id":TRACK, "enabled":True})
        self.assertEqual(liked["liked"], [TRACK])
        self.assertEqual(BASE["liked"], [])
        unliked, _ = cc._change(liked, {"action":"like", "track_id":TRACK, "enabled":False})
        self.assertEqual(unliked["liked"], [])

    def test_playlist_roundtrip(self):
        created, info = cc._change(BASE, {"action":"create", "name":"Cloud Mix", "initial_track_id":TRACK})
        pid = info["created_playlist_id"]
        self.assertEqual(created["playlists"][0]["ids"], [TRACK])
        removed, _ = cc._change(created, {"action":"remove", "playlist_id":pid, "track_id":TRACK})
        self.assertEqual(removed["playlists"][0]["ids"], [])
        renamed, _ = cc._change(removed, {"action":"rename", "playlist_id":pid, "name":"Updated"})
        self.assertEqual(renamed["playlists"][0]["name"], "Updated")
        deleted, _ = cc._change(renamed, {"action":"delete", "playlist_id":pid})
        self.assertEqual(deleted["playlists"], [])

    def test_history(self):
        changed, _ = cc._change(BASE, {"action":"played", "track_id":TRACK})
        self.assertEqual(changed["history"], [TRACK])

    def test_reject_local_track(self):
        with self.assertRaises(ValueError):
            cc._change(BASE, {"action":"like", "track_id":"f"*20, "enabled":True})

    def test_conflict_rebases_on_latest(self):
        state = {"revision":0, "data":BASE.copy()}
        attempts = []
        def fetch():
            return {"revision":state["revision"], "data":state["data"]}
        def save(revision, data):
            attempts.append(revision)
            if len(attempts)==1:
                state["revision"]=1
                state["data"]={"liked": [], "playlists": [], "history":[TRACK], "listeningMs":0}
                raise CloudSyncConflict(fetch())
            state["revision"]+=1
            state["data"]=data
            return {"revision":state["revision"], "data":data}
        with patch.object(cc,"fetch_saved",side_effect=fetch),patch.object(cc,"save_saved",side_effect=save):
            result=cc.change({"action":"like", "track_id":TRACK, "enabled":True})
        self.assertEqual(attempts,[0,1])
        self.assertEqual(result["history"],[TRACK])
        self.assertEqual(result["liked"],[TRACK])

if __name__ == "__main__":
    unittest.main()
