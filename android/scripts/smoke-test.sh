#!/usr/bin/env bash
set -euo pipefail
APK="android/app/build/outputs/apk/debug/app-debug.apk"
PACKAGE="com.wrld.player"
ACTIVITY="com.wrld.player/.MainActivity"

echo "Installing generated WRLD Android APK"
adb install -r "$APK"
adb shell pm grant "$PACKAGE" android.permission.READ_MEDIA_AUDIO || true
adb logcat -c
adb shell am start -W -n "$ACTIVITY"
sleep 10

check_alive() {
  if ! adb shell pidof "$PACKAGE" | tr -d '\r' | grep -Eq '[0-9]'; then
    echo "ERROR: WRLD closed after startup. Recent AndroidRuntime errors:"
    adb logcat -d -s AndroidRuntime:E | tail -n 150 || true
    exit 1
  fi
  echo "WRLD process remains alive."
}
check_alive

echo "Checking the app survives backgrounding and relaunch"
adb shell input keyevent KEYCODE_HOME
sleep 2
adb shell am start -W -n "$ACTIVITY"
sleep 6
check_alive
echo "Android APK launch smoke test passed."
