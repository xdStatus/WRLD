# WRLD Android — first playable beta (v0.1.5)

Native Android music playback with a monochrome WebView interface. The Windows
Python/WebView2 player and its releases remain unchanged.

## Features in the first Android beta

- Discovers audio indexed by Android MediaStore, including songs in your Music folder
- Plays local music using Media3 ExoPlayer and a MediaSessionService
- Plays in the background with Android lock-screen, notification and Bluetooth controls
- All songs, Liked Songs, History (up to 50), local playlists, Shuffle All, search, sorting, repeat Off/All/One
- Editable playback position, app volume (defaults to 10%), animated 999 logo and a lower-power twinkling starfield (no shooting comet)
- No music uploads, no ads and no account requirement

## How to try it

1. Open GitHub Actions in xdStatus/WRLD and verify **Build WRLD Android APK** succeeded.
2. Open the **android-v0.1.5** release and download **WRLD-Android-v0.1.5.apk** to your Android device.
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
