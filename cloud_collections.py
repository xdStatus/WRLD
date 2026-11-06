"""Windows cloud collection actions with revision-safe remote writes.

Never touch local collections.json. Every edit is rebased on the latest D1
snapshot, and server conflicts are retried without discarding another device's
changes.
"""
import re
import uuid
from cloud_sync import fetch_saved, save_saved, CloudSyncConflict

CLOUD_ID = re.compile(r"^r2_[0-9a-f]{24}$")


def _valid_track(value):
    return isinstance(value, str) and CLOUD_ID.fullmatch(value) is not None


def _change(data, request):
    data = {
        "liked": list(data.get("liked", [])),
        "playlists": [
            {"id": p["id"], "name": p["name"], "ids": list(p.get("ids", []))}
            for p in data.get("playlists", []) if isinstance(p, dict)
            and isinstance(p.get("id"), str) and isinstance(p.get("name"), str)
        ],
        "history": list(data.get("history", [])),
        "listeningMs": max(0, int(data.get("listeningMs", 0))),
    }
    action = request.get("action")
    song_id = request.get("track_id")
    playlist_id = request.get("playlist_id")
    result = {}
    if action in ("like", "add", "remove") and not _valid_track(song_id):
        raise ValueError("Invalid cloud song selection")
    if action == "like":
        enabled = request.get("enabled")
        if not isinstance(enabled, bool):
            raise ValueError("Invalid liked-song state")
        if enabled and song_id not in data["liked"]:
            data["liked"].append(song_id)
        elif not enabled and song_id in data["liked"]:
            data["liked"].remove(song_id)
    elif action == "create":
        name = request.get("name")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 70:
            raise ValueError("Playlist name must contain 1–70 characters")
        if len(data["playlists"]) >= 150:
            raise ValueError("Playlist limit reached")
        initial = request.get("initial_track_id")
        if initial is not None and not _valid_track(initial):
            raise ValueError("Invalid initial song")
        identifier = uuid.uuid4().hex[:14]
        data["playlists"].insert(0, {"id": identifier, "name": name.strip(), "ids": [initial] if initial else []})
        result["created_playlist_id"] = identifier
    elif action in ("rename", "delete", "add", "remove"):
        playlist = next((p for p in data["playlists"] if p["id"] == playlist_id), None)
        if playlist is None:
            raise ValueError("Playlist not found")
        if action == "rename":
            name = request.get("name")
            if not isinstance(name, str) or not 1 <= len(name.strip()) <= 70:
                raise ValueError("Playlist name must contain 1–70 characters")
            playlist["name"] = name.strip()
        elif action == "delete":
            data["playlists"].remove(playlist)
        elif action == "add":
            if song_id not in playlist["ids"]:
                if len(playlist["ids"]) >= 10000:
                    raise ValueError("Playlist is full")
                playlist["ids"].append(song_id)
        elif action == "remove" and song_id in playlist["ids"]:
            playlist["ids"].remove(song_id)
    elif action == "played":
        if not _valid_track(song_id):
            raise ValueError("Invalid cloud song selection")
        data["history"] = ([song_id] + [x for x in data["history"] if x != song_id])[:50]
    else:
        raise ValueError("Unknown cloud collection action")
    return data, result


def change(request):
    for _ in range(4):
        current = fetch_saved()
        changed, result = _change(current["data"], request)
        try:
            saved = save_saved(current["revision"], changed)
            return {**saved["data"], **result}
        except CloudSyncConflict:
            continue
    raise ValueError("Cloud collections changed repeatedly; please retry")
