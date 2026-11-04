# WRLD automated desktop updates

WRLD's built-in Update button installs a published Windows release; it does not generate new code.

## Publishing an updated app

1. Make the desired source changes in this repository.
2. Bump `APP_VERSION` in `app_version.py` (for example, 1.8.1 -> 1.8.2) and commit it to `main`.
3. GitHub Actions builds `WRLD.exe`, generates its SHA-256 checksum, creates the version tag automatically, and publishes a release. No separate tag or manual Release step is required.
4. In an already installed WRLD app, open **Updates -> Check Now -> Update & Restart**.

Assistant-side GitHub access can prepare and commit changed source directly, when connected and permitted.

## Notes

- Versions must be unique. A version with an existing published release is skipped.
- Windows compilation and automatic replacement need to succeed in GitHub Actions and on Windows, respectively.
- Avoid adding songs, music folders, build outputs, or personal files to this public repository.
- Existing local playlists and preferences are stored in `%APPDATA%\WRLDPlayer`; the updater must not delete them.
- Users remain in control of applying updates from the WRLD UI.

## Recovery and validation (1.8.3+)

Before shutting down the existing player, the updater now runs the downloaded
EXE with `--startup-probe`. GitHub runs the same smoke test before publishing.
After replacing the EXE, the helper repeats the probe and restores
`WRLD.previous.exe` automatically if the new EXE fails.

If an earlier update is already broken, rename its `WRLD.exe` to
`WRLD.broken.exe`, then rename `WRLD.previous.exe` to `WRLD.exe`.
No music or playlist data is lost; settings are kept in `%APPDATA%\\WRLDPlayer`.
Do not disable security protection to get the app running; inspect Protection History.

## WRLD Windows v1.8.4 — Android experience on desktop

The Windows app now includes Shuffle All, up to 50 most recently played distinct
songs, a Settings tab (independent fade-in/out, 0.5–5-second fade duration,
optional gapless playback, About and library rescan), and a responsive
ColorOS-inspired animated tab indicator.

Click the bottom player title or the small grip below the progress bar to
expand **Up Next** from inside the player. The queue reveals upcoming songs
between the progress bar and playback buttons as the dock grows upward; click
an upcoming song to play it or remove it with × without changing files or
playlists. The existing audio visualizer, repeat mode, playlists and desktop
ColorOS seek/volume sliders remain.

Windows uses an HTML audio element, so gapless **on** does not add an artificial
pause but cannot guarantee sample-accurate gapless playback on every codec.
Gapless **off** adds ~400 ms between songs. History and audio preferences are
stored locally in WebView2's persistent profile; changing that profile can
clear them, but the Windows updater retains the profile as before.

Bumping app_version.py triggers the Windows GitHub Actions pipeline. It checks
JavaScript syntax and probes the packaged EXE before publishing a versioned
release. Use Updates → Check Now → Update & Restart inside the installed app.

## Windows 1.8.5 — private WRLD Cloud

Opening WRLD.exe now also starts a read-only library/streaming endpoint on
127.0.0.1:18766. Its native server never binds to a public or LAN interface.
Use Tailscale Serve to expose it privately to your own devices over HTTPS.
The existing Windows release updater continues to preserve local collections.
See WRLD_CLOUD_SETUP.md for instructions and restrictions.
