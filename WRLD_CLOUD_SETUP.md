# WRLD Cloud — Cloudflare R2 private streaming

The music files are stored in the private Cloudflare R2 bucket `wrld-music`, not
on a Windows server. Both Android and Windows connect over HTTPS to the Worker
`https://wrld-cloud.zaavangonzaless.workers.dev`. Your computer may be off.

Cloudflare must have a Worker with the `MUSIC_BUCKET` R2 binding and a secret
named `WRLD_ACCESS_TOKEN`. The Worker source uses that secret to authenticate
requests to `/api/tracks` and `/api/stream/<encoded object key>`. The R2 bucket
must remain **private**. Test that visiting `/api/tracks` without a token
returns HTTP 401 Unauthorized. Do not publish the key in GitHub or share it.

## Android v0.1.13

Open WRLD → Settings → Music source → WRLD Cloud. Paste the *secret value*
(not the name `WRLD_ACCESS_TOKEN`) and tap Connect. Your key is encrypted
locally using Android Keystore. Music will stream through the existing
Media3 player and background session. Select "On this device" for local music.

## Windows v1.8.6

Open Settings → Music source, paste the same secret key, and choose
"Save key & connect". WRLD encrypts the key with Windows DPAPI for the
current Windows user. The local WebView never receives the saved key.
Choose "On this computer" to return to local playback.

No Tailscale, router port forwarding, or permanently running PC is needed.

## Next steps

Verify the one MP3 already uploaded appears in both cloud libraries, and
test play, pause, seeking, and background playback. Then upload more of
your music files that you are authorized to store and stream.

The private storage service may incur charges for storage and operations.
Cross-device playlists, likes, history and offline cloud downloads are not
yet implemented. Durations can be unknown in the cloud list until playback.

Android preview builds use temporary signing keys. Installing an update may
require uninstalling the older beta and clearing WRLD's in-app settings,
playlists and likes; your device's actual audio files remain untouched.
