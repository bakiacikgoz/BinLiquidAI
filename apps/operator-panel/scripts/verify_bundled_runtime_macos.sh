#!/usr/bin/env bash
set -euo pipefail

ARCH="${1:-$(uname -m)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
RUNTIME_DIR="${REPO_ROOT}/apps/operator-panel/src-tauri/resources/binliquid-runtime"
MANIFEST="${RUNTIME_DIR}/RUNTIME_MANIFEST.txt"
RUNTIME_PYTHON="${RUNTIME_DIR}/python/bin/python"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "[runtime-verify] macOS only" >&2
  exit 2
fi

if [[ "${ARCH}" != "arm64" && "${ARCH}" != "x86_64" ]]; then
  echo "[runtime-verify] unsupported arch: ${ARCH}" >&2
  exit 3
fi

test -f "${MANIFEST}"
test -x "${RUNTIME_PYTHON}"
test -f "${RUNTIME_DIR}/config/balanced.toml"
test -f "${RUNTIME_DIR}/config/providers.example.toml"

"${RUNTIME_PYTHON}" -m imperaos --version >/dev/null
(
  cd /
  IMPERAOS_CONFIG_ROOT="${RUNTIME_DIR}/config" \
    IMPERAOS_PROVIDER_REGISTRY_PATH="${RUNTIME_DIR}/config/providers.example.toml" \
    "${RUNTIME_PYTHON}" -m imperaos operator capabilities --json >/dev/null
)
file "${RUNTIME_PYTHON}"

grep -q "^platform=macos$" "${MANIFEST}"
grep -q "^arch=${ARCH}$" "${MANIFEST}"
grep -q "^python=Python " "${MANIFEST}"
grep -q "^imperaos_version=" "${MANIFEST}"
grep -q "^wheel_sha256=[0-9a-f]\\{64\\}$" "${MANIFEST}"
grep -q "^git_head=" "${MANIFEST}"
grep -q "^built_at_utc=" "${MANIFEST}"

if grep -q "${HOME}" "${MANIFEST}"; then
  echo "[runtime-verify] manifest leaks user home path" >&2
  exit 4
fi

if [[ -z "$(find "${RUNTIME_DIR}/python" -maxdepth 4 -type f 2>/dev/null | head -n 1)" ]]; then
  echo "[runtime-verify] placeholder-only runtime is not release eligible" >&2
  exit 5
fi

RUNTIME_STATUS="$(git -C "${REPO_ROOT}" status --short -- "${RUNTIME_DIR}" | grep -v 'README.txt' || true)"
if [[ -n "${RUNTIME_STATUS}" ]]; then
  echo "[runtime-verify] runtime bundle has tracked or unignored git changes" >&2
  echo "${RUNTIME_STATUS}" >&2
  exit 6
fi

echo "[runtime-verify] bundled runtime verified for ${ARCH}"
