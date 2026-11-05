#!/usr/bin/env bash
set -euo pipefail

APK="android/app/build/outputs/apk/debug/app-debug.apk"
PACKAGE="com.wrld.player.preview"
ACTIVITY="com.wrld.player.preview/com.wrld.player.MainActivity"
AAPT="${ANDROID_HOME}/build-tools/36.0.0/aapt"

echo "Checking the preview is a separate package that cannot replace normal WRLD"
"$AAPT" dump badging "$APK" | grep -q "package: name='com.wrld.player.preview'"
"$AAPT" dump badging "$APK" | grep -q "application-label:'WRLD Preview'"

echo "Installing isolated preview APK"
adb install -r "$APK"
adb shell pm grant "$PACKAGE" android.permission.READ_MEDIA_AUDIO || true
# The splash is a motion-driven feature. Test it with Android animation scales enabled.
adb shell settings put global window_animation_scale 1
adb shell settings put global transition_animation_scale 1
adb shell settings put global animator_duration_scale 1
adb logcat -c
adb shell am start -W -n "$ACTIVITY" --ez wrld_smoke_intro true
# The emulator-only test clicks Settings and replays the intro at 9.85s.
sleep 19
adb logcat -d -s WRLDIntroCheck:I > "$RUNNER_TEMP/intro-runtime-check.txt"
cat "$RUNNER_TEMP/intro-runtime-check.txt"
if ! grep -Fq 'launch: "running"' "$RUNNER_TEMP/intro-runtime-check.txt"; then
  echo "ERROR: Intro did not render at launch (or the overlay was not visible)."
  exit 1
fi
if ! grep -Fq 'replay: "running"' "$RUNNER_TEMP/intro-runtime-check.txt"; then
  echo "ERROR: Settings replay did not render animation frames."
  exit 1
fi
echo "Verified both launch and Settings replay render active particle animation."

check_alive() {
  if ! adb shell pidof "$PACKAGE" | tr -d '\r' | grep -Eq '[0-9]'; then
    echo "ERROR: WRLD Preview closed. Recent AndroidRuntime errors:"
    adb logcat -d -s AndroidRuntime:E | tail -n 150 || true
    exit 1
  fi
  echo "WRLD Preview process remains alive."
}
check_alive

echo "Verifying intro completes and preview survives leaving and returning"
adb shell input keyevent KEYCODE_HOME
sleep 2
adb shell am start -W -n "$ACTIVITY"
sleep 4
check_alive

adb shell pm list packages | tr -d '\r' > "$RUNNER_TEMP/installed-packages.txt"
grep -Fxq "package:$PACKAGE" "$RUNNER_TEMP/installed-packages.txt"
echo "WRLD Preview launch and resume passed."
