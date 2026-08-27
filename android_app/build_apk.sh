#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" && "$(uname -s)" != "Darwin" ]]; then
  echo "Qt pyside6-android-deploy currently requires a Linux or macOS host." >&2
  exit 2
fi

if [[ -f "${HOME}/.profile" ]]; then
  # Loads ANDROID_* and the downloaded Qt-for-Python wheel paths set up by
  # setup_wsl_android_sdk.sh and setup_wsl_wheels.sh.
  source "${HOME}/.profile"
fi

: "${PYSIDE_ANDROID_WHEEL:?Set PYSIDE_ANDROID_WHEEL to the aarch64 PySide6 Android wheel}"
: "${SHIBOKEN_ANDROID_WHEEL:?Set SHIBOKEN_ANDROID_WHEEL to the aarch64 Shiboken6 Android wheel}"
: "${ANDROID_SDK_ROOT:?Set ANDROID_SDK_ROOT}"
: "${ANDROID_NDK_ROOT:?Set ANDROID_NDK_ROOT}"

cd "$(dirname "$0")/.."
DEPLOY_TOOL="${PYSIDE_ANDROID_DEPLOY:-${HOME}/venvs/zhumi-android/bin/pyside6-android-deploy}"
if [[ ! -x "${DEPLOY_TOOL}" ]]; then
  DEPLOY_TOOL="$(command -v pyside6-android-deploy || true)"
fi
if [[ -z "${DEPLOY_TOOL}" || ! -x "${DEPLOY_TOOL}" ]]; then
  echo "pyside6-android-deploy is not installed. Activate the Android virtual environment first." >&2
  exit 3
fi

"${DEPLOY_TOOL}" \
  --config-file android_app/pysidedeploy.spec \
  --name "ZhumiMemo" \
  --wheel-pyside "$PYSIDE_ANDROID_WHEEL" \
  --wheel-shiboken "$SHIBOKEN_ANDROID_WHEEL" \
  --sdk-path "$ANDROID_SDK_ROOT" \
  --ndk-path "$ANDROID_NDK_ROOT" \
  --extra-modules Core,Gui,Widgets \
  --keep-deployment-files \
  -f
