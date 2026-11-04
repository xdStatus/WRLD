# WRLD Cloud — private Windows PC streaming setup

WRLD Cloud turns your Windows PC into a personal music server for Android.
No music is uploaded to a third-party cloud provider. Stream only files you
are authorized to store and stream. This MVP is intentionally private and
read-only: there are no public user accounts or public music catalog.

## Windows setup

1. Update the installed **WRLD Windows** app to **v1.8.5** using
   **Updates → Check Now → Update & Restart**, or get the published WRLD.exe.
2. Install the official Tailscale app for Windows and sign in to your account:
   https://tailscale.com/download
3. Leave the Windows WRLD app open; it starts a small, **read-only** server on
   **127.0.0.1:18766** while the app is running. If WRLD is closed, streaming
   stops until you reopen it.
4. Open **Windows Terminal (Admin)** and run:
   
   ```powershell
   tailscale serve --bg 18766
   tailscale serve status
   ```

   Enable tailnet HTTPS certificates if Tailscale prompts. The status output
   displays a private HTTPS URL similar to
   `https://your-pc.your-tailnet.ts.net`. Copy *your actual* address.
   Never use the `tailscale funnel` command or router port-forwarding.

## Android setup

1. Install Tailscale for Android and sign in to the **same private tailnet**.
2. Update **WRLD Android** to **v0.1.12**.
3. In WRLD open **Settings → Music source → WRLD Cloud**.
4. Paste the URL reported by `tailscale serve status`, e.g.
   `https://your-pc.your-tailnet.ts.net`, then tap **Connect**.
5. The library should show the songs on the PC. Tap a song to stream it.
   Up Next, background playback, seeking, likes, and local Android playlists
   continue to operate. Use **On this device** to return to local tracks.

## Important details and troubleshooting

- **Keep Windows awake** and both devices connected to Tailscale. Streaming
  requires the PC and an internet connection; sleep/offline devices cannot play.
- Streaming from your PC consumes the PC's upstream internet bandwidth and the
  Android phone's network data. Performance depends on both connections.
- **No public exposure.** The server binds only to 127.0.0.1 and only serves
  `/cloud/tracks` metadata and `/cloud/media/<song-id>` file streams.
  It rejects modifying requests and does not expose the Windows admin API.
  Tailscale Serve handles HTTPS and private tailnet access. Limit which devices
  have access to your tailnet; all authorized devices may be able to access the
  streaming endpoint depending on your Tailscale access policy.
- In a browser, `https://your-pc.your-tailnet.ts.net/cloud/tracks` on an
  authenticated Tailscale device should show a JSON library. If you see a
  certificate/connection error, check Tailscale Serve and its HTTPS settings.
- If WRLD Cloud fails to connect, first verify Windows WRLD is running,
  `tailscale serve status` shows the 18766 proxy, and both devices are online.
- This MVP has **no offline cloud caching**, cross-device likes/playlists/history
  synchronization, or perfect gapless streaming guarantee. Songs remain on PC.
- The URL entered in Android is saved to private app preferences locally. No
  password or Tailscale access token is saved by WRLD.
- To turn off private sharing, run `tailscale serve off` on Windows.
- Android beta APKs are still signed with temporary CI keys; uninstalling an
  older version first may clear WRLD app data but never deletes device audio.
