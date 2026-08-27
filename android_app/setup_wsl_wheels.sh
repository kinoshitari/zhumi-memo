#!/usr/bin/env bash
# Run inside Ubuntu WSL as the zhumi user.
set -euo pipefail

WHEEL_DIR="${HOME}/android-wheels"
PYSIDE_WHEEL="pyside6-6.11.2-6.11.2-cp311-cp311-android_aarch64.whl"
SHIBOKEN_WHEEL="shiboken6-6.11.2-6.11.2-cp311-cp311-android_aarch64.whl"

mkdir -p "${WHEEL_DIR}"
QT_MIRROR="https://ftp.jaist.ac.jp/pub/qtproject/official_releases/QtForPython"

aria2c --continue=true --max-connection-per-server=16 --split=16 --min-split-size=1M \
  --dir "${WHEEL_DIR}" --out "${PYSIDE_WHEEL}" \
  "${QT_MIRROR}/pyside6/${PYSIDE_WHEEL}"
aria2c --continue=true --max-connection-per-server=8 --split=8 --min-split-size=1M \
  --dir "${WHEEL_DIR}" --out "${SHIBOKEN_WHEEL}" \
  "${QT_MIRROR}/shiboken6/${SHIBOKEN_WHEEL}"

echo "c5288e0740ad91d87d4cafa16132768c149c56521bf63c83c98404b865911678  ${WHEEL_DIR}/${PYSIDE_WHEEL}" | sha256sum -c -
echo "e99609b689d3df2ac97ffbe17df0ce8b1246b2c47b4d24f6fb73f1eaad4bd0f2  ${WHEEL_DIR}/${SHIBOKEN_WHEEL}" | sha256sum -c -

cat >> "${HOME}/.profile" <<EOF
export PYSIDE_ANDROID_WHEEL=${WHEEL_DIR}/${PYSIDE_WHEEL}
export SHIBOKEN_ANDROID_WHEEL=${WHEEL_DIR}/${SHIBOKEN_WHEEL}
EOF

sha256sum "${WHEEL_DIR}/${PYSIDE_WHEEL}" "${WHEEL_DIR}/${SHIBOKEN_WHEEL}"
