#!/usr/bin/env bash
set -euo pipefail
APK="android/app/build/outputs/apk/debug/app-debug.apk"
PACKAGE="com.wrld.player"
ACTIVITY="$PACKAGE/.MainActivity"

# Never allow an unresponsive emulator/ADB connection to hang the workflow.
adb_ready() {
  timeout 45s adb wait-for-device &&
    timeout 20s adb shell getprop sys.boot_completed | tr -d '\r' | grep -qx 1
}

run_adb() {
  timeout 45s adb "$@"
}

echo "Waiting for Android emulator"
adb_ready || { echo "ERROR: Android emulator unavailable"; exit 1; }
echo "Installing generated WRLD Android APK"
run_adb install -r "$APK"
run_adb shell pm grant "$PACKAGE" android.permission.READ_MEDIA_AUDIO || true
# Prevent the Android 13+ notification permission dialog from obscuring launch.
run_adb shell pm grant "$PACKAGE" android.permission.POST_NOTIFICATIONS || true
run_adb logcat -c || true

launch() {
  run_adb shell am start -W -n "$ACTIVITY"
}

check_alive() {
  for attempt in 1 2 3 4 5; do
    if timeout 15s adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r' | grep -Eq '[0-9]'; then
      echo "WRLD process remains alive."
      return 0
    fi
    echo "WRLD process not detected (attempt $attempt/5); checking emulator"
    adb_ready || true
    sleep 3
  done
  echo "ERROR: WRLD did not remain running. Recent AndroidRuntime errors:"
  timeout 20s adb logcat -d -s AndroidRuntime:E 2>/dev/null | tail -n 150 || true
  exit 1
}

launch
sleep 10
check_alive

echo "Checking the app survives backgrounding and relaunch"
run_adb shell input keyevent KEYCODE_HOME
sleep 2
launch
sleep 6
check_alive
echo "Android APK launch smoke test passed."
