#!/usr/bin/env python3
"""WRLD Player: an offline-first local music player (Python standard library only)."""
from __future__ import annotations

import hashlib
import uuid
import json
import mimetypes
import os
import re
import sys
import threading
import subprocess
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from duration_tools import duration_seconds

APP_DIR = Path(__file__).resolve().parent
WEB_DIR = APP_DIR / 'web'
CONFIG_DIR = Path(os.environ.get('APPDATA', str(Path.home()))) / 'WRLDPlayer'
CONFIG_FILE = CONFIG_DIR / 'settings.json'
COLLECTIONS_FILE = CONFIG_DIR / 'collections.json'
DURATION_CACHE_FILE = CONFIG_DIR / 'duration_cache.json'
SUPPORTED = {'.mp3', '.m4a', '.wav', '.ogg', '.flac', '.aac', '.opus'}
MEDIA_MIME = {
    '.mp3': 'audio/mpeg', '.m4a': 'audio/mp4', '.wav': 'audio/wav',
    '.ogg': 'audio/ogg', '.flac': 'audio/flac', '.aac': 'audio/aac',
    '.opus': 'audio/ogg',
}
lock = threading.RLock()
tracks_by_id = {}
root_dir: Path | None = None


def load_config():
    try:
        return json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}


def save_config(root: Path):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps({'music_folder': str(root)}, indent=2), encoding='utf-8')


def read_collections():
    try:
        data = json.loads(COLLECTIONS_FILE.read_text(encoding='utf-8'))
        if isinstance(data, dict) and isinstance(data.get('liked'), list) and isinstance(data.get('playlists'), list):
            return {'liked': data['liked'], 'playlists': data['playlists']}
    except (OSError, ValueError, TypeError):
        pass
    return {'liked': [], 'playlists': []}


def write_collections(data):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG_DIR / f'collections.{uuid.uuid4().hex}.tmp'
    try:
        with temporary.open('w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, COLLECTIONS_FILE)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def collection_action(data):
    action = data.get('action')
    with lock:
        collections = read_collections()
        liked = collections['liked']
        playlists = collections['playlists']
        result = {}
        track_id = data.get('track_id')
        playlist_id = data.get('playlist_id')
        if action in ('like', 'add', 'remove'):
            if not isinstance(track_id, str) or not re.fullmatch(r'[0-9a-f]{20}', track_id):
                raise ValueError('Invalid song selection')
        if action == 'like':
            enabled = data.get('enabled')
            if not isinstance(enabled, bool):
                raise ValueError('Invalid liked-song state')
            if enabled and track_id not in liked:
                liked.append(track_id)
            elif not enabled and track_id in liked:
                liked.remove(track_id)
            if len(liked) > 20_000:
                raise ValueError('Too many liked songs')
        elif action == 'create':
            name = data.get('name')
            if not isinstance(name, str) or not 1 <= len(name.strip()) <= 70:
                raise ValueError('Playlist name must contain 1–70 characters')
            if len(playlists) >= 150:
                raise ValueError('Playlist limit reached')
            identifier = uuid.uuid4().hex[:14]
            initial_id = data.get('initial_track_id')
            if initial_id is not None and (not isinstance(initial_id, str) or not re.fullmatch(r'[0-9a-f]{20}', initial_id)):
                raise ValueError('Invalid initial song')
            playlists.insert(0, {'id': identifier, 'name': name.strip(), 'ids': [initial_id] if initial_id else []})
            result['created_playlist_id'] = identifier
        elif action in ('rename', 'delete', 'add', 'remove'):
            if not isinstance(playlist_id, str):
                raise ValueError('Invalid playlist selection')
            playlist = next((p for p in playlists if p.get('id') == playlist_id), None)
            if playlist is None:
                raise ValueError('Playlist not found')
            if action == 'rename':
                name = data.get('name')
                if not isinstance(name, str) or not 1 <= len(name.strip()) <= 70:
                    raise ValueError('Playlist name must contain 1–70 characters')
                playlist['name'] = name.strip()
            elif action == 'delete':
                playlists.remove(playlist)
            elif action == 'add':
                if track_id not in playlist['ids']:
                    if len(playlist['ids']) >= 10_000:
                        raise ValueError('Playlist is full')
                    playlist['ids'].append(track_id)
            elif action == 'remove':
                if track_id in playlist['ids']:
                    playlist['ids'].remove(track_id)
        else:
            raise ValueError('Unknown playlist action')
        write_collections(collections)
        return {**collections, **result}


def pick_default_dir():
    value = load_config().get('music_folder')
    if value:
        return Path(value).expanduser()
    return Path.home() / 'Music' / 'WRLD'


def parse_mp3_tags(path: Path):
    """Read only tiny ID3 text frames for artist/album; filename always wins for title."""
    info = {}
    try:
        with path.open('rb') as f:
            header = f.read(10)
            if len(header) != 10 or header[:3] != b'ID3' or header[3] not in (3, 4):
                return info
            version = header[3]
            tag_size = sum(b << s for b, s in zip(header[6:10], (21, 14, 7, 0)))
            remaining = min(tag_size, 256_000)
            while remaining >= 10:
                h = f.read(10)
                remaining -= len(h)
                if len(h) < 10 or h[:4].strip(b'\0') == b'':
                    break
                frame = h[:4]
                if not re.match(rb'^[A-Z0-9]{4}$', frame):
                    break
                size = int.from_bytes(h[4:8], 'big') if version == 3 else sum(b << s for b, s in zip(h[4:8], (21, 14, 7, 0)))
                if size <= 0 or size > remaining:
                    break
                if frame in (b'TPE1', b'TALB') and size <= 8192:
                    data = f.read(size)
                    codec = {0: 'latin-1', 1: 'utf-16', 2: 'utf-16-be', 3: 'utf-8'}.get(data[0], 'latin-1') if data else 'latin-1'
                    try:
                        text = data[1:].decode(codec, errors='replace').split('\x00')[0].strip()
                        if text and len(text) <= 140:
                            info['artist' if frame == b'TPE1' else 'album'] = text
                    except Exception:
                        pass
                else:
                    f.seek(size, 1)
                remaining -= size
                if 'artist' in info and 'album' in info:
                    break
    except OSError:
        pass
    return info




def read_duration_cache():
    try:
        data=json.loads(DURATION_CACHE_FILE.read_text(encoding='utf-8'))
        return data if isinstance(data,dict) else {}
    except (OSError,ValueError):
        return {}


def write_duration_cache(data):
    try:
        CONFIG_DIR.mkdir(parents=True,exist_ok=True)
        temp=CONFIG_DIR / f'duration_cache.{uuid.uuid4().hex}.tmp'
        temp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        os.replace(temp,DURATION_CACHE_FILE)
    except OSError:
        pass
    finally:
        try:temp.unlink(missing_ok=True)
        except (OSError,UnboundLocalError):pass

def scan_folder(folder: Path):
    items = {}
    if not folder.is_dir():
        return items
    cache=read_duration_cache()
    new_cache={}
    try:
        iterator = folder.rglob('*')
        for path in iterator:
            try:
                if not path.is_file() or path.suffix.lower() not in SUPPORTED:
                    continue
                relative = path.relative_to(folder).as_posix()
                file_id = hashlib.sha256(relative.casefold().encode('utf-8')).hexdigest()[:20]
                stat = path.stat()
                display_title = path.stem.strip() or 'Untitled'
                key=str(path)
                signature=f'v16-frames:{stat.st_size}:{stat.st_mtime_ns}'
                cached=cache.get(key)
                if isinstance(cached,dict) and cached.get('signature')==signature:
                    duration=cached.get('duration')
                else:
                    duration=duration_seconds(path,stat.st_size)
                if duration is not None and not (0 < duration < 604800):duration=None
                new_cache[key]={'signature':signature,'duration':duration}
                tags = parse_mp3_tags(path) if path.suffix.lower() == '.mp3' else {}
                artist = tags.get('artist') or 'Juice WRLD'
                # Metadata from downloaders often contains video/source labels. Fall back to the collection artist.
                if len(artist) > 90 or 'getmp3' in artist.lower():
                    artist = 'Juice WRLD'
                items[file_id] = {
                    'id': file_id, 'title': display_title, 'artist': artist,
                    'album': tags.get('album') or ('WRLD Collection' if path.parent == folder else path.parent.name),
                    'format': path.suffix[1:].upper(), 'bytes': stat.st_size,
                    'modified': stat.st_mtime, 'duration': duration, 'relative': relative,
                    'path': path,
                }
            except (OSError, ValueError):
                continue
    except (OSError, PermissionError):
        return items
    if new_cache != cache:write_duration_cache(new_cache)
    return items


def rebuild(folder=None):
    global root_dir, tracks_by_id
    with lock:
        target = folder if folder is not None else root_dir
    if target is None:
        target = pick_default_dir()
    target = Path(target).expanduser().resolve()
    result = scan_folder(target)
    with lock:
        root_dir = target
        tracks_by_id = result
    return len(result)


def public_tracks():
    with lock:
        songs = [{key: val for key, val in song.items() if key != 'path'} for song in tracks_by_id.values()]
        folder = str(root_dir) if root_dir else ''
    songs.sort(key=lambda item: (item['title'].casefold(), item['relative'].casefold()))
    return {'folder': folder, 'folder_exists': Path(folder).is_dir(), 'count': len(songs), 'tracks': songs}


def embedded_mp3_cover(path: Path):
    try:
        with path.open('rb') as f:
            h = f.read(10)
            if len(h) != 10 or h[:3] != b'ID3' or h[3] not in (3, 4):
                return None
            tag_size = sum(b << s for b, s in zip(h[6:10], (21, 14, 7, 0)))
            if tag_size > 8_000_000:
                return None
            remaining = tag_size
            while remaining >= 10:
                hdr = f.read(10)
                remaining -= len(hdr)
                if len(hdr) < 10 or not re.match(rb'^[A-Z0-9]{4}$', hdr[:4]):
                    return None
                size = int.from_bytes(hdr[4:8], 'big') if h[3] == 3 else sum(b << s for b, s in zip(hdr[4:8], (21, 14, 7, 0)))
                if size <= 0 or size > remaining:
                    return None
                if hdr[:4] == b'APIC' and size < 5_000_000:
                    data = f.read(size)
                    if not data:
                        return None
                    mime_end = data.find(b'\0', 1)
                    if mime_end < 0 or mime_end > 100:
                        return None
                    mime = data[1:mime_end].decode('ascii', errors='ignore').lower()
                    pos = mime_end + 2  # picture type follows MIME separator
                    if pos >= len(data):
                        return None
                    if data[0] in (1, 2):
                        # UTF-16 descriptions use 2-byte terminator
                        i = pos
                        while i + 1 < len(data):
                            if data[i:i+2] == b'\0\0':
                                pos = i + 2
                                break
                            i += 2
                        else:
                            return None
                    else:
                        end = data.find(b'\0', pos)
                        if end < 0:
                            return None
                        pos = end + 1
                    blob = data[pos:]
                    if blob.startswith(b'\xff\xd8\xff'):
                        return 'image/jpeg', blob
                    if blob.startswith(b'\x89PNG\r\n\x1a\n'):
                        return 'image/png', blob
                    if mime in ('image/jpeg', 'image/png') and blob:
                        return mime, blob
                    return None
                f.seek(size, 1)
                remaining -= size
    except OSError:
        pass
    return None


def cover_for_path(path: Path):
    for candidate in ('cover.jpg', 'cover.jpeg', 'folder.jpg', 'folder.png', 'cover.png', 'front.jpg', 'front.png'):
        image_path = path.parent / candidate
        if image_path.is_file():
            try:
                data = image_path.read_bytes()
                if len(data) <= 6_000_000:
                    return mimetypes.guess_type(str(image_path))[0] or 'image/jpeg', data
            except OSError:
                pass
    if path.suffix.lower() == '.mp3':
        return embedded_mp3_cover(path)
    return None


class Handler(BaseHTTPRequestHandler):
    server_version = 'WRLDPlayer/1.0'

    def log_message(self, format, *args):
        # Keep the terminal quiet except for important exceptions.
        if args and str(args[1] if len(args) > 1 else '') in ('404', '500'):
            super().log_message(format, *args)

    def send_bytes(self, status, data, content_type, extra_headers=None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store' if (content_type.startswith('application/json') or content_type.startswith('text/html')) else 'private, max-age=900')
        for name, value in (extra_headers or {}).items():
            self.send_header(name, str(value))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(data)

    def json_out(self, status, obj):
        self.send_bytes(status, json.dumps(obj, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if self.headers.get('Sec-Fetch-Site') not in (None, 'none', 'same-origin'):
            return self.json_out(403, {'error': 'Only the local player can request these files.'})
        path = unquote(urlsplit(self.path).path)
        if path in ('/', '/index.html'):
            return self.serve_static('index.html', 'text/html; charset=utf-8')
        if path == '/favicon.svg':
            return self.serve_static('favicon.svg','image/svg+xml')
        if path in ('/favicon.ico','/favicon.png'):
            return self.serve_static('favicon.ico','image/x-icon')
        if path == '/api/tracks':
            return self.json_out(200, public_tracks())
        if path == '/api/collections':
            with lock:
                return self.json_out(200, read_collections())
        if path.startswith('/media/'):
            return self.stream_track(path.rsplit('/', 1)[-1])
        if path.startswith('/api/art/'):
            track_id = path.rsplit('/', 1)[-1]
            with lock:
                track = tracks_by_id.get(track_id)
            if not track:
                return self.json_out(404, {'error': 'Track not found'})
            cover = cover_for_path(track['path'])
            if not cover:
                return self.send_bytes(404, b'', 'text/plain')
            return self.send_bytes(200, cover[1], cover[0])
        return self.json_out(404, {'error': 'Not found'})

    def serve_static(self, name, content_type):
        return self.send_bytes(200, (WEB_DIR / name).read_bytes(), content_type)

    def do_POST(self):
        origin = self.headers.get('Origin')
        if origin and origin != f'http://127.0.0.1:{self.server.server_port}':
            return self.json_out(403, {'error': 'External websites cannot control this player.'})
        if self.headers.get('Sec-Fetch-Site') not in (None, 'none', 'same-origin'):
            return self.json_out(403, {'error': 'External websites cannot control this player.'})
        path = urlsplit(self.path).path
        try:
            n = int(self.headers.get('Content-Length', '0'))
            if n > 4096:
                return self.json_out(413, {'error': 'Request too large'})
            payload = json.loads(self.rfile.read(n) or b'{}') if n else {}
        except (ValueError, json.JSONDecodeError):
            return self.json_out(400, {'error': 'Invalid request'})
        if path == '/api/collection-action':
            try:
                return self.json_out(200, collection_action(payload))
            except ValueError as exc:
                return self.json_out(400, {'error': str(exc)})
            except OSError:
                return self.json_out(500, {'error': 'Could not save collection data'})
        if path == '/api/rescan':
            rebuild()
            return self.json_out(200, public_tracks())
        if path == '/api/change-folder':
            requested = payload.get('folder', '')
            if not isinstance(requested, str) or not requested.strip():
                return self.json_out(400, {'error': 'Choose a folder first.'})
            folder = Path(os.path.expandvars(requested.strip().strip('"'))).expanduser()
            if not folder.is_dir():
                return self.json_out(400, {'error': 'That folder does not exist on this computer.'})
            count = rebuild(folder)
            save_config(folder.resolve())
            return self.json_out(200, {'message': 'Music folder updated', 'count': count, **public_tracks()})
        if path == '/api/browse-folder':
            try:
                import tkinter as tk
                from tkinter import filedialog
                win = tk.Tk()
                win.withdraw()
                win.attributes('-topmost', True)
                selected = filedialog.askdirectory(initialdir=str(root_dir if root_dir and root_dir.is_dir() else Path.home()))
                win.destroy()
                if selected:
                    folder = Path(selected)
                    count = rebuild(folder)
                    save_config(folder.resolve())
                    return self.json_out(200, {'message': 'Music folder updated', 'count': count, **public_tracks()})
                return self.json_out(200, {'cancelled': True})
            except Exception as exc:
                return self.json_out(500, {'error': f'Folder picker unavailable. Paste the folder path instead. ({type(exc).__name__})'})
        return self.json_out(404, {'error': 'Not found'})

    def stream_track(self, track_id):
        with lock:
            track = tracks_by_id.get(track_id)
        if track is None:
            return self.json_out(404, {'error': 'Track not found. Rescan your folder.'})
        path = track['path']
        try:
            size = path.stat().st_size
        except OSError:
            return self.json_out(404, {'error': 'Audio file missing. Rescan your folder.'})
        start, end = 0, size - 1
        partial = False
        header = self.headers.get('Range', '')
        if header:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', header.strip())
            if match:
                partial = True
                a, b = match.groups()
                if a:
                    start = int(a)
                    end = min(int(b), size - 1) if b else size - 1
                elif b:
                    start = max(0, size - int(b))
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header('Content-Range', f'bytes */{size}')
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
        length = max(0, end - start + 1)
        self.send_response(206 if partial else 200)
        self.send_header('Content-Type', MEDIA_MIME.get(path.suffix.lower(), 'application/octet-stream'))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(length))
        self.send_header('Cache-Control', 'private, max-age=3600')
        if partial:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        if self.command == 'HEAD':
            return
        try:
            with path.open('rb') as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(262_144, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass



def open_app_window(address: str):
    """On Windows, use Edge/Chrome app mode for a dedicated music-player window."""
    if sys.platform == 'win32':
        bases = [
            Path(os.environ.get('PROGRAMFILES(X86)', r'C:\Program Files (x86)')),
            Path(os.environ.get('PROGRAMFILES', r'C:\Program Files')),
            Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local'))),
        ]
        candidates = [
            bases[0] / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe',
            bases[1] / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe',
            bases[0] / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
            bases[1] / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
            bases[2] / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
        ]
        for executable in candidates:
            if executable.is_file():
                try:
                    subprocess.Popen([str(executable), f'--app={address}', '--window-size=1470,925'],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                except OSError:
                    pass
    webbrowser.open(address)

def main():
    count = rebuild()
    try:
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    except OSError:
        print('Opening a fresh local player session.')
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    address = f'http://127.0.0.1:{server.server_port}/'
    print('')
    print('=' * 57)
    print(' WRLD PLAYER - your offline music collection')
    print('=' * 57)
    print(f' Folder: {root_dir}')
    print(f' Tracks found: {count}')
    print(f' Open: {address}')
    print(' The music stays on THIS computer. No uploads or account.')
    print(' Keep this window open while you listen. Ctrl+C to stop.')
    print('=' * 57)
    print('', flush=True)
    try:
        open_app_window(address)
    except Exception:
        pass
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
