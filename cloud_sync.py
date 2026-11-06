"""WRLD Cloud collections synchronization transport.

The caller must provide the existing securely stored access key. This module
never persists credentials, never silently overwrites conflicts, and is inert
unless the app explicitly selects its cloud library.
"""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request
from cloud_backend import _read_token, _https_opener, WORKER_ORIGIN

SYNC_URL = WORKER_ORIGIN + "/api/sync"
MAX_RESPONSE = 2_000_000


class CloudSyncError(Exception):
    pass


class CloudSyncConflict(CloudSyncError):
    def __init__(self, snapshot):
        super().__init__("Cloud collections changed on another device")
        self.snapshot = snapshot


def _request(method, access_key, body=None):
    if not access_key:
        raise CloudSyncError("WRLD Cloud access key is missing")
    data = json.dumps(body, separators=(",", ":")).encode("utf-8") if body is not None else None
    if data is not None and len(data) > MAX_RESPONSE:
        raise CloudSyncError("Sync payload is too large")
    request = Request(
        SYNC_URL,
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + access_key,
            "Accept": "application/json",
            **({"Content-Type": "application/json"} if data is not None else {}),
        },
    )
    try:
        with _https_opener.open(request, timeout=15) as response:
            status = response.status
            raw = response.read(MAX_RESPONSE + 1)
    except HTTPError as exc:
        status = exc.code
        if status == 401:
            raise CloudSyncError("WRLD Cloud access key rejected") from None
        if status != 409:
            raise CloudSyncError(f"Cloud sync unavailable (HTTP {status})") from None
        raw = exc.read(MAX_RESPONSE + 1)
    except (URLError, TimeoutError) as exc:
        raise CloudSyncError("Could not reach WRLD Cloud") from exc
    if len(raw) > MAX_RESPONSE:
        raise CloudSyncError("Cloud sync response is too large")
    try:
        result = json.loads(raw)
        revision = result["revision"]
        payload = result["data"]
        if type(revision) is not int or revision < 0 or not isinstance(payload, dict):
            raise ValueError("Invalid cloud sync snapshot")
    except (ValueError, KeyError, TypeError) as exc:
        raise CloudSyncError("Invalid cloud sync response") from exc
    snapshot = {"revision": revision, "data": payload}
    if status == 409:
        raise CloudSyncConflict(snapshot)
    return snapshot


def fetch(access_key):
    return _request("GET", access_key)


def save(access_key, revision, collections):
    if type(revision) is not int or revision < 0:
        raise ValueError("Invalid sync revision")
    if not isinstance(collections, dict):
        raise ValueError("Collections must be a dictionary")
    return _request("PUT", access_key, {"revision": revision, "data": collections})

def fetch_saved():
    """Fetch with the existing DPAPI-protected cloud key."""
    return fetch(_read_token())


def save_saved(revision, collections):
    return save(_read_token(), revision, collections)
