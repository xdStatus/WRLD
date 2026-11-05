# WRLD Android — permanent signing and update installation

Starting with Android `v0.1.15`, public APK releases must be signed with one
permanent certificate. **Do not publish the debug APK**: GitHub-hosted runners
generate a fresh, incompatible debug key.

## Owner setup (required once)

1. Save **WRLD-Android-permanent-signing.p12** (the private signing key) in a
   secure place off the GitHub repository, with a separate backed-up copy.
2. Open the private companion file **WRLD-Android-GitHub-secrets-PRIVATE.txt**
   supplied to the project owner. It contains the base64 key and password.
   Do **not** commit or paste the private text into an issue or chat.
3. In GitHub, open `xdStatus/WRLD → Settings → Secrets and variables → Actions`.
   Add the following **repository secrets**, using the values from that file:
   - `WRLD_ANDROID_KEYSTORE_BASE64`
   - `WRLD_ANDROID_STORE_PASSWORD`
   - `WRLD_ANDROID_KEY_ALIAS` (value: `wrld`)
4. Open **Actions → Build WRLD Android APK → Run workflow** on `main`.
   If the three secrets are absent, the workflow intentionally fails the
   signing stage and **does not publish** an unsigned or transient-key APK.
5. The workflow checks the key's certificate against
   `android/signing-cert.sha256`, compiles a signed **release** APK, verifies
   the APK's signature and publishes `android-v0.1.15` with a SHA-256 checksum.
   The public certificate fingerprint is safe to commit; the private key
   and password are **not**.

The pinned certificate digest in `android/signing-cert.sha256` corresponds
to the supplied original keystore. If signing does not match, investigate
and recover that original key; do not overwrite the pinned digest to
accommodate a new temporary key.

## Migrating from Android v0.1.14

Android only accepts an in-place update if the new APK has the same package
ID and a compatible signing certificate, with a nondecreasing version code.
Earlier Android beta APKs were debug-signed using temporary CI keys, which
are no longer available. The new permanent-key v0.1.15 will generally **not**
install over v0.1.14 as a direct update. This signing transition may require
one **uninstall and reinstall**.

**Uninstalling can erase the previous app's local likes, playlists, listening
history, settings and stored WRLD Cloud token.** Before choosing to migrate,
make a record of anything important and keep the access token in your own
secure password manager. Your phone's original audio files and Cloudflare R2
bucket are unaffected. You may keep using v0.1.14 without migrating immediately.

Once v0.1.15 is installed with the permanent certificate, subsequent releases
signed by that **same** key and using the unchanged `com.wrld.player` package
ID can be installed over it without erasing app data.

## In-app updates

WRLD Settings → Updates → **Check for Android updates** asks the native app
to query GitHub's official release API. If a newer Android APK exists,
**Download Android v…** opens that exact release file in your browser.
Android will request installation confirmation; WRLD does not silently
install packages. Network requests and APK links are handled natively, not
through the offline-only WebView's JavaScript bridge.

The update button cannot bypass Android's signing requirements. If Android
rejects an update with a signature conflict, **do not uninstall automatically**.
Check which version you have installed and decide whether the one-time
migration is worth the possible local data loss.

## Future releases

- Keep the original `.p12` and signing password, never rotate them casually.
- Bump both `versionCode` and `versionName`.
- Adjust the release tag and artifact names in `.github/workflows/android.yml`.
- Use the **permanently signed release** APK, never a debug APK.
- Confirm the fingerprint and installation check before sharing a download.
