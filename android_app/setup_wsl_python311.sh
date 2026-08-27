#!/usr/bin/env bash
# Run as root in Ubuntu WSL. PySide6 Android deployment currently needs Python <= 3.11.
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this script as root in WSL." >&2
  exit 1
fi

PYTHON_VERSION="3.11.16"
PYTHON_PREFIX="/opt/python-${PYTHON_VERSION%.*}"
PYTHON_TARBALL="Python-${PYTHON_VERSION}.tgz"
PYTHON_SHA256="6c0bd76ab0ec7d94ed400b1497f01ac6c7751c8822615ee0855a3eb2d893ea76"
DEV_USER="zhumi"
VENV_DIR="/home/${DEV_USER}/venvs/zhumi-android"

apt-get install -y \
  libbz2-dev libreadline-dev libsqlite3-dev liblzma-dev tk-dev uuid-dev \
  libgdbm-dev libnss3-dev libdb5.3-dev

if [[ ! -x "${PYTHON_PREFIX}/bin/python3.11" ]]; then
  workdir="$(mktemp -d)"
  trap 'rm -rf "${workdir}"' EXIT
  curl -fL --retry 3 -o "${workdir}/${PYTHON_TARBALL}" \
    "https://www.python.org/ftp/python/${PYTHON_VERSION}/${PYTHON_TARBALL}"
  echo "${PYTHON_SHA256}  ${workdir}/${PYTHON_TARBALL}" | sha256sum -c -
  tar -xzf "${workdir}/${PYTHON_TARBALL}" -C "${workdir}"
  pushd "${workdir}/Python-${PYTHON_VERSION}" >/dev/null
  ./configure --prefix="${PYTHON_PREFIX}" --with-ensurepip=install
  make -j"$(nproc)"
  make altinstall
  popd >/dev/null
fi

rm -rf "${VENV_DIR}"
runuser -u "${DEV_USER}" -- "${PYTHON_PREFIX}/bin/python3.11" -m venv "${VENV_DIR}"
runuser -u "${DEV_USER}" -- "${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel
runuser -u "${DEV_USER}" -- "${VENV_DIR}/bin/python" -m pip install \
  "PySide6==6.11.2" qtpip "buildozer==1.5.0" "cython==0.29.33"
runuser -u "${DEV_USER}" -- "${VENV_DIR}/bin/python" -m pip install -r \
  "${VENV_DIR}/lib/python3.11/site-packages/PySide6/scripts/requirements-android.txt"

cat >> "/home/${DEV_USER}/.profile" <<EOF
export PYSIDE_ANDROID_DEPLOY=${VENV_DIR}/bin/pyside6-android-deploy
EOF
chown "${DEV_USER}:${DEV_USER}" "/home/${DEV_USER}/.profile"

"${VENV_DIR}/bin/python" --version
"${VENV_DIR}/bin/pyside6-android-deploy" --help >/dev/null
echo "Python 3.11 Android deployment environment is ready."
