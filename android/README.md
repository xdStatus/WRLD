# WRLD Android — first playable beta (v0.1.14)

Native Android music playback with a monochrome WebView interface. The Windows
Python/WebView2 player and its releases remain unchanged.

## Features in the first Android beta

- Discovers audio indexed by Android MediaStore, including songs in your Music folder
- Plays local music using Media3 ExoPlayer and a MediaSessionService
- Plays in the background with Android lock-screen, notification and Bluetooth controls
- All songs, Liked Songs, History (up to 50), local playlists, Shuffle All, Settings, search, sorting, repeat Off/All/One
- Editable playback position, app volume (defaults to 10%), animated 999 logo and a lower-power twinkling starfield (no shooting comet)
- No music uploads, no ads and no account requirement

## How to try it

1. Open GitHub Actions in xdStatus/WRLD and verify **Build WRLD Android APK** succeeded.
2. Open the **android-v0.1.14** release and download **WRLD-Android-v0.1.14.apk** to your Android device.
3. Allow APK installation from your browser or file manager when Android prompts.
4. Open WRLD and grant **Music and audio** access.
5. Put music files in your phone's Music folder if the library is empty, then reopen/Rescan.

The APK is debug-signed for this first test build. Each GitHub Actions build uses
a temporary debug signing key, so you cannot reliably install future test APKs
over it. A persistent private Android signing key in GitHub Actions secrets
is needed before making an in-app Android updater. Do not put signing keys in
this public repository. A sideloaded update always needs an Android installation
confirmation.

Android playlists and Liked Songs are stored on the phone and are not synced
with Windows yet. The decorative mobile player is not an audio-reactive spectrum
visualizer in this first preview.

## Development

Open the android/ directory in Android Studio, or build using:

    gradle -p android :app:assembleDebug

Recommended: JDK 17, Gradle 8.11.1, Android SDK 36.
Android package: com.wrld.player, minSdk 26, targetSdk 35.

Architecture:
- MainActivity.kt: isolated asset-only WebView, permission/UI bridge, MediaController
- PlaybackService.kt: Media3 foreground playback and system media controls
- LibraryRepository.kt: MediaStore song metadata
- CollectionStore.kt: local favorites and playlists
- assets/index.html: offline mobile UI, starfield, 999 animation

The app only uses local files selected from MediaStore and does not request
the INTERNET permission. The Updates link opens the GitHub Releases page in
your phone's default browser, not an automatic installer.

Android music decoding supports formats supported by Android/Media3 and the
device's codecs; availability may differ for unusual audio formats.

## Android beta v0.1.4

The tap-to-summon comet Easter egg has been removed; the 999 digits still wave.
The starfield is capped at about 25 frames/second, with fewer stars and a
smaller canvas to reduce the GPU load on phones.

Because the early GitHub Actions beta APKs use temporary debug signing keys,
Android may reject installing v0.1.4 directly over v0.1.0. If Android displays
"App not installed" or a signature conflict, uninstall the old WRLD Android
beta first, then install v0.1.4. Uninstalling clears this app's Liked Songs and
playlists but does **not** delete music stored on the phone.

## Android beta v0.1.4 — immersive fullscreen

The app hides Android's top status/notification bar and bottom navigation bar
while WRLD is in the foreground (Android 8+). Swipe from the top or bottom
screen edge to temporarily reveal Android's normal system controls, including
notifications and navigation. When WRLD regains focus after system dialogs or
app switching, it restores fullscreen automatically. Lock-screen playback and
notifications outside the foreground app are unchanged.

This beta remains temporarily debug-signed by CI. An APK with a different
signature cannot update the installed beta; Android may require uninstalling
the old APK first. That only clears WRLD's app-specific likes/playlists, not
phone audio files.

## Android beta v0.1.4 — Shuffle All

Tap the **Shuffle All** button immediately below Search to start playing
all songs indexed on the phone in a randomized queue, regardless of the
active view, playlist, search terms, or sort option. This uses the existing
Media3 service so background, Bluetooth, and system playback controls work.
The button is disabled when no songs have been loaded.

Note: Beta APKs are still signed with temporary debug keys. Android may
require uninstalling the previous beta before installing this one; that clears
app-specific favorites/playlists but does not delete music files.

## Android beta v0.1.4 — launch-crash recovery

This build replaces the early WindowInsets-based immersive fullscreen setup with
deferred, guarded immersive flags after the view has attached. It preserves
Shuffle All and the lower-power background. This is intended to address reports
of V0.1.3 closing immediately on some Android phones; the exact device-specific
cause remains unconfirmed.

GitHub Actions now launches the APK on an Android 15 emulator, exercises
reopening after Home, and blocks publishing if the app quits unexpectedly.
Passing this emulator check is not a guarantee that every phone's Android skin
behaves the same way. If V0.1.4 still crashes on your device, try the verified
working v0.1.0 and collect a device crash log for investigation.

The early APKs remain signed with separate temporary keys; installing this
update may require uninstalling the old beta first.

## Android beta v0.1.5 — progress bar and history

The seek bar now matches the desktop WRLD ColorOS-inspired style: a slim dim
rail, pale gradient fill, small luminous playhead, and an expanded track with
a scrub-position tooltip on touch. The existing Media3 seeking logic remains.

History is a fourth tab. It is saved on the phone by the Media3 playback service,
so songs played through Shuffle All, regular playback and background media
controls are included. It shows **at most 50 distinct songs**, most recently
played first. Replaying a song moves it to the front. Song history stays local
and isn't uploaded or synchronized with Windows. Uninstalling WRLD clears it.

The CI workflow validates the WebView JavaScript and launches the APK on an
Android emulator before publishing. APK signing is still temporary; installing
a different beta may require uninstalling the current one first.

## Android beta v0.1.6 — matching ColorOS volume bar

The bottom-right Volume slider shares the same soft gray track, bright
white gradient fill and glowing playhead as the progress scrubber. On touch,
the track expands and shows a floating volume percentage. The accessible
native HTML range remains the touch/keyboard input and still controls the
Media3 app volume (0–100%); the default remains 10%.

Only Android files have changed. This beta uses temporary debug APK signing,
so you may need to uninstall the old beta before installing the new APK.
Music files on the phone will not be deleted, but uninstalling the beta
clears its locally stored playlists, favorites and history.

## Android beta v0.1.7 — Settings and About

Android WRLD now has a fifth tab, **Settings**. It provides:

- **Fade in** (default off): native Media3 service increases volume smoothly at
  the beginning of a song rather than abruptly starting at full volume.
- **Fade out** (default off): lowers the volume during the last seconds of a
  song where its duration is known. Fades use an envelope; this is not
  simultaneous two-song crossfading.
- **Fade duration:** 0.5 to 5 seconds, with 2 seconds as the default.
- **Gapless playback** (default on): continuous playlist transitions when
  supported by the source format/device. With the setting off, WRLD uses a
  short 400ms automatic pause at song boundaries.
- **Library rescan** to refresh the on-device song list, and an **About**
  section with the app version, offline privacy description and GitHub Releases.

The options and existing app-volume preference are stored locally on the phone.
Effects are applied in the MediaSessionService, including background and
Bluetooth playback, and do not require WRLD to stay open on screen. The
volume slider displays the user's configured app volume, not the temporary
volume reduction created by fades.

The APK is compiled, JavaScript-validated and launched in the Android emulator
before publication. The beta uses temporary per-build signing, so installation
may require uninstalling an older version first (clearing app-specific settings,
liked songs and playlists, but **never** the phone's music files).

## Android beta v0.1.8 — fix Settings bleed and manage Up Next

The global infinite-scroll handler could append a stale list of songs below
Settings/About and Playlists. It now only runs on song-list tabs; changing to
Settings/Playlists clears the previous song-list pagination state. Scrolling
the Settings page cannot add tracks under About anymore.

Tap the **currently playing song** in the bottom player to open **Up Next**.
WRLD shows the playing track followed by the queued tracks. Tap an upcoming
song to jump to it, or tap × to remove just that upcoming entry. These changes
are made in the existing Media3 MediaController queue, so they also apply while
listening in the background. Removing a queued entry does **not** delete the
music file or modify any playlist. The current song is protected from removal.
Long queues load incrementally inside the sheet to keep scrolling responsive.

APK signing is still temporary in this preview. Android may require removing
the previous app before installing; this clears local WRLD data but not songs.

## Android beta v0.1.9 — fluid ColorOS-like navigation

The Up Next queue now slides up with a spring-like easing curve while its
backdrop fades in. Closing it reverses the animation. Because the overlay
remains mounted, fast taps don't flash a fully rendered sheet.

All Songs, Liked, History, Playlists and Settings now use a shared sliding
indicator and a short fade/vertical motion transition. Quick consecutive tab
taps cancel stale transitions, so the selected tab remains authoritative.
The scroll handler pauses while a view is changing. When motion reduction is
enabled in Android accessibility settings, these animations are disabled.
The existing 999 logo, 25FPS lightweight starfield, queue controls and music
playback behavior remain unchanged.

## Android beta v0.1.10 — Up Next as one continuous player drawer

**Up Next now lives inside the bottom player**, directly underneath the
progress bar. Tap the current-song area or the small handle beneath the
timeline, or swipe the handle upward. The bottom player grows upward to
uncover the queue in a single animated height change; the playback controls
and volume stay anchored to the bottom. Tapping the handle again, swiping it
downward, or pressing the × control collapses the queue into the player.

There is no separate bottom-sheet popup, overlay or backdrop fade. The
underlying app tabs and audio logic are unchanged. Android reduced-motion
preferences turn off the height animation. Upcoming tracks remain removable
without deleting audio files, and the existing long-queue pagination stays.

## Android beta v0.1.11 — brighter natural twinkling

The existing sky is a little brighter overall: most stars retain an independent,
soft luminosity pulse but fewer disappear into the dark background. A small
subset of the stars sometimes shine near-white for under a second, with a
brief, restrained cross sparkle at the peak. Each bright moment is separated
by randomized several-second gaps; there are no synchronized flashes.

The star count, capped canvas resolution and approximately 25 FPS animation
remain unchanged. No meteors or shooting stars were restored. Playback,
settings, interface controls, the integrated queue, and Windows builds remain
untouched. The app still uses temporary debug APK signing keys, so installing
this build over an older beta may require uninstalling it first; music files
are not deleted, but saved app preferences/playlists/likes may be cleared.

## Android beta v0.1.13 — WRLD Cloud (personal Windows server)

WRLD can now stream from the music collection on your own Windows computer
without copying the songs onto Android. Settings → Music source → WRLD Cloud
accepts the PC's private HTTPS Tailscale Serve address, then downloads a
read-only metadata list and plays streams through Media3 ExoPlayer, retaining
background playback, Bluetooth controls and the integrated Up Next queue.
Music sources can be switched between **On this device** and **WRLD Cloud**.

Both Windows and Android must be connected to your own Tailscale tailnet; the
Windows machine must remain awake with WRLD running. The app only accepts a
trusted HTTPS *.ts.net hostname as its cloud endpoint; untrusted HTTP links
and redirects are not accepted for metadata. No Google Drive or public server
is involved. The local server is read-only and exposes only song metadata and
music-file streams. See WRLD_CLOUD_SETUP.md in the repository for setup.

This first streaming milestone does not sync playlists/likes/history across
Windows and Android, nor cache offline cloud tracks. They remain device-local.
The Windows desktop app itself still plays music locally as before.

Debug APK signing remains temporary; switching APK versions may require
uninstalling WRLD, which clears app-specific preferences, liked songs and
playlists but does not delete your music files.

## Android v0.1.13 — Cloudflare R2 streaming

WRLD Cloud now streams from the private Cloudflare Worker and R2 storage,
not a Windows/Tailscale server. Enter a secret Worker access key once in
Settings; the token is encrypted with Android Keystore and used for Media3
background audio requests. No public R2 bucket, phone Tailscale app or
running PC required. Local playback is still supported. See
WRLD_CLOUD_SETUP.md for current steps. Older PC-server information above is
retained for historical version notes only.


## Android beta v0.1.14 — mobile reverse sorting

The All songs and Liked songs views now share a compact sort dropdown and
40-pixel touch-friendly reverse-direction arrow. Choose Title, Length,
Date added or Artist, then tap the arrow to reverse the ordering without
reopening a menu. The icon smoothly flips while honoring Android's reduced
motion preference. Natural numeric title sorting puts "Song 2" before
"Song 10"; missing cloud duration metadata stays at the bottom in either
direction. The selected sort and direction are saved in WebView local storage.

History remains newest-played-first, and manual playlist track order remains
unchanged. No desktop-style A–Z sidebar/navigation is included on mobile.

This release does not alter Cloudflare R2 streaming, Android music playback,
the Android intro, or any Windows code. As with previous Android betas, the
APK is debug-signed with a temporary key. If Android rejects an over-install
because of a signature mismatch, uninstalling the prior beta can remove
its stored likes, playlists, history, settings, and private cloud access key.
Avoid uninstalling unless prepared to reconfigure them. Device music files
and R2 data are not affected.

## Android v0.1.15 (pending signing) — desktop Magicule Singularity on mobile

The Android WebView now includes the monochrome WRLD Magicule Singularity
startup sequence from Windows 1.8.34. A fresh set of **350 white magicules**
arrives from outside the display on curved paths, settles into the WRLD
lettering, and hovers in the particle-only shape for **700 ms** before the
font becomes visible through a soft illuminated mask. The letters then
reconstruct the small WRLD wordmark in the Android header. The previous
animated 999 header emblem is replaced with the WRLD wordmark for continuity.

Mobile rendering uses a capped canvas pixel ratio and frame rate to reduce
load. The intro is always touch-through, cleans itself up on app backgrounding,
honors reduced-motion preferences and has a hard timeout. Android Settings
includes **Preview Magicule Singularity** for replaying the randomized
animation. The music library, playback service, WRLD Cloud connection, and
desktop intro are otherwise untouched.

This work is committed to the unreleased 0.1.15 source. The build pipeline
intentionally refuses to publish an APK until the owner's permanent
GitHub Actions signing secrets are configured and the signing certificate
is verified. Do not install a new temporary debug-signed APK over your
working 0.1.14 beta merely to preview the animation. See
[SIGNING_SETUP.md](SIGNING_SETUP.md) for the one-time migration instructions.
