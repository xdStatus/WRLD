"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "../..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");
const ui = read("android/app/src/main/assets/index.html");
const activity = read("android/app/src/main/java/com/wrld/player/MainActivity.kt");
const checker = read("android/app/src/main/java/com/wrld/player/AndroidUpdateChecker.kt");
const service = read("android/app/src/main/java/com/wrld/player/PlaybackService.kt");
const gradle = read("android/app/build.gradle.kts");
const workflow = read(".github/workflows/android.yml");
const fingerprint = read("android/signing-cert.sha256").trim();

assert.match(fingerprint, /^[a-f0-9]{64}$/, "Public certificate fingerprint must be SHA-256");
assert.match(gradle, /versionName = "0\.1\.20"/);
assert.match(gradle, /versionCode = 21/);
assert.match(gradle, /WRLD_KEYSTORE_PATH/);
assert.match(gradle, /signingConfig = signingConfigs\.getByName\("wrldRelease"\)/);

assert.match(checker, /https:\/\/api\.github\.com\/repos\/xdStatus\/WRLD\/releases\?per_page=100/);
assert.match(checker, /https:\/\/github\.com\/xdStatus\/WRLD\/releases\/download/);
assert.match(checker, /android-v/);
assert.match(checker, /optString\("tag_name"\)/);
assert.match(checker, /assets\.length\(\)/);
assert.match(checker, /hasVerifiedAsset/);
assert.match(checker, /latestVersion > installed/);

assert.match(activity, /@JavascriptInterface fun checkForUpdates\(\)/);
assert.match(activity, /@JavascriptInterface fun downloadUpdate\(\)/);
assert.match(activity, /AndroidUpdateChecker\.check\(current\)/);
assert.match(activity, /verifiedUpdateUrl = result\.downloadUrl/);
assert.match(activity, /startsWith\("https:\/\/github\.com\/xdStatus\/WRLD\/releases\/download\/android-v"\)/);
assert.match(activity, /Intent\(Intent\.ACTION_VIEW, android\.net\.Uri\.parse\(url\)\)/);
assert.match(activity, /receiveAppVersion/);
assert.match(activity, /receiveUpdateStatus/);

assert.match(ui, /data-check-updates="1"/);
assert.match(ui, /data-download-update="1"/);
assert.match(ui, /receiveUpdateStatus:function\(data\)/);
assert.match(ui, /call\("checkForUpdates"\)/);
assert.match(ui, /call\("downloadUpdate"\)/);

assert.match(workflow, /Verify Android update feature integration/);
assert.match(workflow, /secrets\.WRLD_ANDROID_KEYSTORE_BASE64/);
assert.match(workflow, /secrets\.WRLD_ANDROID_STORE_PASSWORD/);
assert.match(workflow, /secrets\.WRLD_ANDROID_KEY_ALIAS/);
assert.match(workflow, /apksigner/);
assert.match(workflow, /assembleRelease/);
assert.match(workflow, /android\/signing-cert\.sha256/);
assert.match(workflow, /android-v0\.1\.20/);
assert.doesNotMatch(workflow, /cp android\/app\/build\/outputs\/apk\/debug\/app-debug\.apk android\/dist/,
  "NEVER publish ephemeral debug APKs");
assert.match(service, /wrld-listening/);
assert.match(service, /SystemClock\.elapsedRealtime\(\)/);
assert.match(service, /activePlayer\?\.isPlaying == true/);
assert.match(service, /putLong\("totalMs", listeningMs\)/);
assert.match(activity, /requestListeningTime\(\)/);
assert.match(activity, /receiveListeningTime/);
assert.match(ui, /Total listening time:/);
assert.match(ui, /fmtListening\(app\.listeningMs\)/);
assert.match(ui, /cloud-status\.is-connected/);
assert.match(ui, /cloudConnected\(\)/);
console.log("Android update checks: trusted GitHub releases, in-app controls, fixed APK signature, protected CI.");
