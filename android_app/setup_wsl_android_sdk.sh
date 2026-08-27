#!/usr/bin/env bash
# Run with: wsl.exe -d Ubuntu-24.04 -u root -- bash /mnt/g/AI/日常/ClipboardPlus/android_app/setup_wsl_android_sdk.sh
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this script as root in WSL." >&2
  exit 1
fi

DEV_USER="zhumi"
SDK_ROOT="/opt/android-sdk"
NDK_VERSION="26.1.10909125"
JAVA_HOME_PATH="/usr/lib/jvm/java-17-openjdk-amd64"

chown -R "${DEV_USER}:${DEV_USER}" "${SDK_ROOT}"

runuser -u "${DEV_USER}" -- env \
  ANDROID_SDK_ROOT="${SDK_ROOT}" \
  JAVA_HOME="${JAVA_HOME_PATH}" \
  bash -lc "yes | '${SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager' --licenses >/tmp/zhumi-android-licenses.log"

runuser -u "${DEV_USER}" -- env \
  ANDROID_SDK_ROOT="${SDK_ROOT}" \
  JAVA_HOME="${JAVA_HOME_PATH}" \
  "${SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager" --install \
  "platform-tools" \
  "platforms;android-35" \
  "build-tools;35.0.0" \
  "ndk;${NDK_VERSION}" \
  "cmake;3.22.1"

cat >> "/home/${DEV_USER}/.profile" <<EOF

# Android SDK for 猪咪备忘录 APK builds
export ANDROID_SDK_ROOT=${SDK_ROOT}
export ANDROID_HOME=${SDK_ROOT}
export ANDROID_NDK_ROOT=${SDK_ROOT}/ndk/${NDK_VERSION}
export JAVA_HOME=${JAVA_HOME_PATH}
export PATH="\$PATH:\$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:\$ANDROID_SDK_ROOT/platform-tools"
EOF
chown "${DEV_USER}:${DEV_USER}" "/home/${DEV_USER}/.profile"

echo "Android SDK setup complete."
