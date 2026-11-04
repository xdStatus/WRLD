"""Personal WRLD Cloud client for the fixed, private Cloudflare Worker.

Credential is encrypted under the current Windows user account using DPAPI.
Neither the token nor its bearer Authorization header is exposed to the WebView.
"""
from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import ssl
import socket
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler

from player import CONFIG_DIR

WORKER_ORIGIN = "https://wrld-cloud.zaavangonzaless.workers.dev"
SECRET_PATH = CONFIG_DIR / "cloud_token.bin"
REMOTE_LIMIT = 5_000_000
_lock = threading.RLock()
_remote_tracks = {}

class CloudError(Exception):
    pass


def _connection_error(exc: BaseException) -> CloudError:
    """Explain connection failures without exposing URLs, headers, or credentials."""
    reason = exc.reason if isinstance(exc, URLError) else exc
    if isinstance(reason, ssl.SSLCertVerificationError):
        return CloudError("WRLD Cloud TLS certificate verification failed (Windows/Python trust store).")
    if isinstance(reason, ssl.SSLError):
        return CloudError("WRLD Cloud TLS handshake failed.")
    if isinstance(reason, (socket.timeout, TimeoutError)):
        return CloudError("WRLD Cloud connection timed out.")
    if isinstance(reason, socket.gaierror):
        return CloudError("WRLD Cloud DNS lookup failed.")
    if isinstance(reason, ConnectionRefusedError):
        return CloudError("WRLD Cloud connection was refused.")
    if isinstance(reason, ConnectionResetError):
        return CloudError("WRLD Cloud connection was reset.")
    if isinstance(reason, OSError):
        return CloudError("WRLD Cloud connection failed (" + type(reason).__name__ + ", Windows error " + str(getattr(reason, "winerror", None) or getattr(reason, "errno", "unknown")) + ").")
    return CloudError("WRLD Cloud connection failed (" + type(reason).__name__ + ").")

class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _crypt(data: bytes, decrypt: bool) -> bytes:
    if os.name != "nt":
        raise CloudError("Cloud credential storage is available in the Windows app.")
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    src = ctypes.create_string_buffer(data)
    inp = DATA_BLOB(len(data), ctypes.cast(src, ctypes.POINTER(ctypes.c_ubyte)))
    out = DATA_BLOB()
    function = crypt32.CryptUnprotectData if decrypt else crypt32.CryptProtectData
    function.restype = wintypes.BOOL
    if decrypt:
        ok = function(ctypes.byref(inp), None, None, None, None, 0x1, ctypes.byref(out))
    else:
        ok = function(ctypes.byref(inp), None, None, None, None, 0x1, ctypes.byref(out))
    if not ok:
        raise CloudError("Could not unlock the Windows-protected cloud access key.")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(out.pbData, ctypes.c_void_p))


def set_token(token: str) -> dict:
    token = str(token or "").strip()
    if not 32 <= len(token) <= 512 or not re.fullmatch(r"[A-Za-z0-9_-]+", token):
        raise CloudError("The access key must be at least 32 characters.")
    ciphertext = _crypt(token.encode("utf-8"), False)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    temp = SECRET_PATH.with_suffix(".tmp")
    temp.write_bytes(base64.b64encode(ciphertext))
    temp.replace(SECRET_PATH)
    return cloud_status()


def _read_token() -> str:
    try:
        return _crypt(base64.b64decode(SECRET_PATH.read_bytes()), True).decode("utf-8")
    except FileNotFoundError:
        return ""


def cloud_status() -> dict:
    return {"url": WORKER_ORIGIN, "configured": SECRET_PATH.exists()}


class _BlockRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _make_https_opener():
    # Windows verifies Cloudflare's chain against the Windows certificate
    # store, including trusted intermediates, rather than a frozen bundle.
    # Keep hostname verification and redirect blocking enabled.
    if os.name == "nt":
        import truststore
        tls_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        return build_opener(_BlockRedirects, HTTPSHandler(context=tls_context))
    return build_opener(_BlockRedirects)


_https_opener = _make_https_opener()


def _authorized_request(path: str, *, range_header: str = "", method: str = "GET"):
    # Routes must come from our validated Worker API, not arbitrary HTTPS URLs.
    if not (path == "/api/tracks" or path.startswith("/api/stream/")):
        raise CloudError("Invalid cloud endpoint.")
    token = _read_token()
    if not token:
        raise CloudError("Enter your WRLD Cloud access key in Settings.")
    headers = {"Authorization": "Bearer " + token, "Accept": "application/json"}
    if range_header:
        headers["Range"] = range_header
    request = Request(WORKER_ORIGIN + path, headers=headers, method=method)
    response = _https_opener.open(request, timeout=25)
    # The token may never be forwarded to a redirect host.
    if urlsplit(response.geturl()).netloc != urlsplit(WORKER_ORIGIN).netloc:
        response.close()
        raise CloudError("Unexpected cloud redirect.")
    return response


def list_tracks() -> dict:
    try:
        with _authorized_request("/api/tracks") as response:
            if response.headers.get("Content-Length") and int(response.headers["Content-Length"]) > REMOTE_LIMIT:
                raise CloudError("Cloud library response is too large.")
            raw = response.read(REMOTE_LIMIT + 1)
            if len(raw) > REMOTE_LIMIT:
                raise CloudError("Cloud library response is too large.")
            payload = json.loads(raw)
    except HTTPError as exc:
        raise CloudError("Access key rejected (401)." if exc.code == 401 else "Worker returned HTTP " + str(exc.code)) from None
    except (URLError, TimeoutError, OSError) as exc:
        raise _connection_error(exc) from None
    if not isinstance(payload, dict) or not isinstance(payload.get("tracks"), list):
        raise CloudError("Invalid cloud library response.")
    songs, lookup = [], {}
    for track in payload["tracks"][:20000]:
        if not isinstance(track, dict):
            continue
        key, path = track.get("id"), track.get("streamPath")
        if not isinstance(key, str) or not (0 < len(key) <= 2048) or not isinstance(path, str):
            continue
        if not path.startswith("/api/stream/") or len(path) > 4096 or any(c in path for c in "?#"):
            continue
        identifier = "r2_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
        title = str(track.get("title") or Path(key).stem)[:300]
        artist = str(track.get("artist") or "Juice WRLD")[:200]
        ext = Path(key).suffix.lower()
        song = {"id": identifier, "title": title, "artist": artist,
                "album": "WRLD Cloud", "duration": 0, "bytes": int(track.get("size") or 0),
                "format": ext.lstrip(".").upper(), "relative": key,
                "modified": 0}
        songs.append(song)
        lookup[identifier] = path
    with _lock:
        _remote_tracks.clear()
        _remote_tracks.update(lookup)
    return {"folder": "WRLD Cloud · Cloudflare R2", "folder_exists": True,
            "count": len(songs), "tracks": songs}


def open_stream(identifier: str, range_header: str = "", method: str = "GET"):
    if not re.fullmatch(r"r2_[0-9a-f]{24}", identifier):
        raise CloudError("Invalid cloud song.")
    with _lock:
        path = _remote_tracks.get(identifier)
    if not path:
        raise CloudError("Cloud song not found. Refresh the library.")
    try:
        return _authorized_request(path, range_header=range_header, method=method)
    except HTTPError as exc:
        raise CloudError("Cloud Worker returned HTTP " + str(exc.code)) from None
    except (URLError, TimeoutError, OSError):
        raise CloudError("Cloud streaming connection failed.") from None
