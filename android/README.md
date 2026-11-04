# WRLD Android — first playable beta (v0.1.1)

Native Android music playback with a monochrome WebView interface. The Windows
Python/WebView2 player and its releases remain unchanged.

## Features in the first Android beta

- Discovers audio indexed by Android MediaStore, including songs in your Music folder
- Plays local music using Media3 ExoPlayer and a MediaSessionService
- Plays in the background with Android lock-screen, notification and Bluetooth controls
- All songs, Liked Songs, local playlists, search, sorting, repeat Off/All/One
- Editable playback position, app volume (defaults to 10%), animated 999 logo and a lower-power twinkling starfield (no shooting comet)
- No music uploads, no ads and no account requirement

## How to try it

1. Open GitHub Actions in xdStatus/WRLD and verify **Build WRLD Android APK** succeeded.
2. Open the **android-v0.1.1** release and download **WRLD-Android-v0.1.1.apk** to your Android device.
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

## Android beta v0.1.1

The tap-to-summon comet Easter egg has been removed; the 999 digits still wave.
The starfield is capped at about 25 frames/second, with fewer stars and a
smaller canvas to reduce the GPU load on phones.

Because the early GitHub Actions beta APKs use temporary debug signing keys,
Android may reject installing v0.1.1 directly over v0.1.0. If Android displays
"App not installed" or a signature conflict, uninstall the old WRLD Android
beta first, then install v0.1.1. Uninstalling clears this app's Liked Songs and
playlists but does **not** delete music stored on the phone.
