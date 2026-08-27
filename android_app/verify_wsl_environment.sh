#!/usr/bin/env bash
# Validates the installed Android environment without generating an APK.
set -euo pipefail

if [[ "$(uname -s)" != "Linux" && "$(uname -s)" != "Darwin" ]]; then
  echo "Run this preflight check from Linux or macOS." >&2
  exit 2
fi

source "${HOME}/.profile"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_TOOL="${PYSIDE_ANDROID_DEPLOY:-${HOME}/venvs/zhumi-android/bin/pyside6-android-deploy}"

test -x "${DEPLOY_TOOL}"
test -x "${ANDROID_SDK_ROOT}/platform-tools/adb"
test -x "${ANDROID_NDK_ROOT}/ndk-build"
test -f "${PYSIDE_ANDROID_WHEEL}"
test -f "${SHIBOKEN_ANDROID_WHEEL}"

cd "${PROJECT_ROOT}"
"${DEPLOY_TOOL}" \
  --config-file android_app/pysidedeploy.spec \
  --wheel-pyside "${PYSIDE_ANDROID_WHEEL}" \
  --wheel-shiboken "${SHIBOKEN_ANDROID_WHEEL}" \
  --sdk-path "${ANDROID_SDK_ROOT}" \
  --ndk-path "${ANDROID_NDK_ROOT}" \
  --dry-run \
  --force
