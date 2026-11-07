#!/usr/bin/env python3
"""WRLD native Windows desktop entry point.

This launcher runs the existing offline Python music server in the background
and hosts the same HTML/CSS/JavaScript UI inside a native WebView2 window.

Windows build: double-click BUILD_WRLD_EXE.cmd to create dist/WRLD.exe.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from http.server import ThreadingHTTPServer

from player import Handler, CONFIG_DIR, rebuild
from app_version import APP_VERSION
import update_support

HOST = '127.0.0.1'
PREFERRED_PORT = 18765  # Keeps saved browser UI preferences on a stable local origin


def record_problem(exc: BaseException) -> Path | None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = CONFIG_DIR / 'native-launch-error.log'
        details = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        with log_path.open('a', encoding='utf-8') as log:
            log.write(f'\n[{datetime.now().isoformat(timespec="seconds")}]\n{details}\n')
        return log_path
    except Exception:
        return None


def alert_error(exc: BaseException):
    log = record_problem(exc)
    message = (f'WRLD could not start.\n\n{type(exc).__name__}: {exc}\n\n'
               'The native window requires Microsoft Edge WebView2 Runtime.\n'
               'https://developer.microsoft.com/en-us/microsoft-edge/webview2/')
    if log:
        message += f'\n\nError details: {log}'
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, 'WRLD — Startup error', 0x10)
        except Exception:
            pass
    print(message, file=sys.stderr)


def create_server() -> ThreadingHTTPServer:
    # Bind locally only. If an older copy is open, choose an unused port.
    try:
        server = ThreadingHTTPServer((HOST, PREFERRED_PORT), Handler)
    except OSError:
        server = ThreadingHTTPServer((HOST, 0), Handler)
    server.daemon_threads = True
    return server


def self_test() -> None:
    """Cross-platform test of native wrapper's server integration (no UI needed)."""
    rebuild()
    server = create_server()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f'http://{HOST}:{server.server_port}'
        def read_json(path):
            with urlopen(Request(base + path), timeout=10) as response:
                assert response.status == 200
                return json.loads(response.read())
        with urlopen(Request(base + '/'), timeout=10) as response:
            page = response.read().decode('utf-8')
            assert '<title>WRLD</title>' in page, 'The WRLD UI did not load'
            assert 'id="queueDrawer"' in page, 'Up Next queue was not included'
            assert 'id="settingsPanel"' in page, 'Playback Settings page was not included'
            assert 'id="tabHistory"' in page, '50-song History tab was not included'
        with urlopen(Request(base + '/favicon.ico'), timeout=10) as response:
            assert response.headers.get_content_type() == 'image/x-icon'
            assert response.read(4) == b'\x00\x00\x01\x00'
        data = read_json('/api/tracks')
        assert isinstance(data['tracks'], list)
        collections = read_json('/api/collections')
        assert isinstance(collections['liked'], list)
        assert isinstance(collections['playlists'], list)
        print(f'WRLD native server self-test PASSED. Tracks: {data["count"]}')
        print(f'URL: {base}')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


class NativeAPI:
    """Native window, folder picker, and controlled release update bridge."""

    def __init__(self):
        self._window_maximized = False

    def choose_folder(self) -> str:
        import webview
        win = webview.windows[0] if webview.windows else None
        if not win:
            return ''
        chosen = win.create_file_dialog(webview.FileDialog.FOLDER)
        return str(chosen[0]) if chosen else ''

    def cloud_info(self):
        from cloud_backend import cloud_status
        return cloud_status()

    def configure_cloud(self, token):
        from cloud_backend import set_token
        return set_token(token)

    def version_info(self):
        return {'version': APP_VERSION, 'repository': update_support.current_repo()}

    def configure_update_repo(self, repository):
        return update_support.configure_repo(repository)

    def check_for_updates(self):
        return update_support.check_update()

    def install_update(self):
        result = update_support.download_and_stage_update()
        # Wait until the response reaches the UI before closing the WebView.
        def close_after():
            import webview
            if webview.windows: webview.windows[0].destroy()
        threading.Timer(0.9, close_after).start()
        return result

    def window_action(self, action):
        import webview
        if not webview.windows: return False
        win = webview.windows[0]
        if action == 'minimize':
            win.minimize()
        elif action == 'maximize':
            if self._window_maximized:
                win.restore()
            else:
                win.maximize()
            self._window_maximized = not self._window_maximized
        elif action == 'fullscreen':
            win.toggle_fullscreen()
        elif action == 'close':
            win.destroy()
        else: return False
        return True


def run_desktop() -> None:
    if sys.platform != 'win32':
        raise RuntimeError('The Windows native build must be run on Windows.')
    # Always reuse the existing library scanner and persistent collections folder.
    rebuild()
    server = create_server()
    thread = threading.Thread(target=server.serve_forever, daemon=True,
                              name='WRLD-local-music-server')
    thread.start()
    address = f'http://{HOST}:{server.server_port}/'
    try:
        import webview
        # Restrict native drag initiation to the explicit top header regions.
        # Content controls, track rows, sliders and canvas must not move the app.
        webview.settings['DRAG_REGION_DIRECT_TARGET_ONLY'] = True
        # Use a standard Windows frame so every edge/corner can resize the window.
        # Size the initial window to the available desktop work area (excluding taskbar).
        import ctypes
        from ctypes import wintypes
        work_area = wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(work_area), 0):
            available_width = work_area.right - work_area.left
            available_height = work_area.bottom - work_area.top
        else:
            available_width = ctypes.windll.user32.GetSystemMetrics(0)
            available_height = ctypes.windll.user32.GetSystemMetrics(1)
        # Compact portrait window matching the requested narrow desktop footprint.
        window_width = min(340, max(320, available_width - 20))
        window_height = min(800, max(480, available_height - 20))
        webview.create_window(
            'WRLD', address, js_api=NativeAPI(), width=window_width, height=window_height,
            min_size=(320, 480), resizable=True, frameless=True,
            easy_drag=False, shadow=True,
            background_color='#050505', text_select=False, zoomable=False,
        )
        # Use the built-in Windows WebView2 renderer — no browser process window.
        # Keep UI preferences such as repeat mode and volume between launches.
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        webview.start(
            gui='edgechromium',
            private_mode=False,
            storage_path=str(CONFIG_DIR / 'webview-profile'),
            debug=False,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def main() -> int:
    if '--startup-probe' in sys.argv:
        # Fast packaging smoke test, without opening the music library or UI.
        # Run by both GitHub Actions and the update installer.
        import webview
        return 0
    if '--self-test' in sys.argv:
        self_test()
        return 0
    try:
        run_desktop()
        return 0
    except Exception as exc:
        alert_error(exc)
        return 1


if __name__ == '__main__':
    sys.exit(main())
