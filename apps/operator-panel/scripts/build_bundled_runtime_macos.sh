#!/usr/bin/env bash
set -euo pipefail

ARCH="${1:-$(uname -m)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
APP_DIR="${REPO_ROOT}/apps/operator-panel"
RUNTIME_DIR="${APP_DIR}/src-tauri/resources/binliquid-runtime"
DIST_DIR="${REPO_ROOT}/dist"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
WHEEL_PATH="${WHEEL_PATH:-}"
RUNTIME_PYTHON="${RUNTIME_DIR}/python/bin/python"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "[runtime] macOS only" >&2
  exit 2
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "[runtime] python binary not found: ${PYTHON_BIN}" >&2
  exit 3
fi

mkdir -p "${DIST_DIR}"

if [[ -z "${WHEEL_PATH}" ]]; then
  echo "[runtime] building binliquid wheel"
  (
    cd "${REPO_ROOT}"
    uv build --wheel --out-dir "${DIST_DIR}"
  )
  WHEEL_PATH="$(ls -t "${DIST_DIR}"/binliquid-*.whl | head -n 1)"
fi

if [[ ! -f "${WHEEL_PATH}" ]]; then
  echo "[runtime] wheel not found: ${WHEEL_PATH}" >&2
  exit 4
fi

echo "[runtime] target arch=${ARCH}"
if [[ "${ARCH}" != "arm64" && "${ARCH}" != "x86_64" ]]; then
  echo "[runtime] unsupported arch: ${ARCH} (expected arm64 or x86_64)" >&2
  exit 7
fi

PYTHON_RESOLVED="$(command -v "${PYTHON_BIN}")"
PYTHON_FILE_INFO="$(file "${PYTHON_RESOLVED}")"
echo "${PYTHON_FILE_INFO}"
if [[ "${PYTHON_FILE_INFO}" != *"${ARCH}"* && "${PYTHON_FILE_INFO}" != *"universal binary"* ]]; then
  echo "[runtime] python architecture does not match target arch=${ARCH}" >&2
  echo "[runtime] choose a ${ARCH}-compatible interpreter via PYTHON_BIN" >&2
  exit 8
fi

rm -rf "${RUNTIME_DIR}"
mkdir -p "${RUNTIME_DIR}"

"${PYTHON_BIN}" -m venv "${RUNTIME_DIR}/python"
"${RUNTIME_DIR}/python/bin/pip" install --upgrade pip wheel
"${RUNTIME_DIR}/python/bin/pip" install "${WHEEL_PATH}"

if [[ ! -x "${RUNTIME_PYTHON}" ]]; then
  echo "[runtime] invalid runtime: expected executable ${RUNTIME_PYTHON}" >&2
  echo "[runtime] placeholder-only runtime is not release-eligible" >&2
  exit 5
fi

if ! "${RUNTIME_PYTHON}" -m binliquid --version >/dev/null; then
  echo "[runtime] runtime validation failed: ${RUNTIME_PYTHON} -m binliquid --version" >&2
  exit 6
fi

BINLIQUID_VERSION="$("${RUNTIME_PYTHON}" -m binliquid --version)"
echo "${BINLIQUID_VERSION}"

cat > "${RUNTIME_DIR}/RUNTIME_MANIFEST.txt" <<EOF
arch=${ARCH}
python=${RUNTIME_PYTHON}
binliquid_version=${BINLIQUID_VERSION}
built_at_utc=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF

cat > "${RUNTIME_DIR}/README.txt" <<'EOF'
Generated runtime bundle for AegisOS Operator Panel.

Release gate:
1) python/bin/python is executable
2) python -m binliquid --version passes

Do not ship placeholder-only runtime contents.
EOF

echo "[runtime] bundled runtime ready: ${RUNTIME_DIR}"
