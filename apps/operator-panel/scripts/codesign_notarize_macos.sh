#!/usr/bin/env bash
set -euo pipefail

APP_PATH="${1:?usage: codesign_notarize_macos.sh <App.app> <artifact.dmg>}"
DMG_PATH="${2:?usage: codesign_notarize_macos.sh <App.app> <artifact.dmg>}"

: "${SIGNING_IDENTITY:?SIGNING_IDENTITY is required}"
: "${APPLE_ID:?APPLE_ID is required}"
: "${APPLE_TEAM_ID:?APPLE_TEAM_ID is required}"
: "${APPLE_APP_PASSWORD:?APPLE_APP_PASSWORD is required}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "[release] macOS only" >&2
  exit 2
fi

if [[ ! -d "${APP_PATH}" ]]; then
  echo "[release] app not found: ${APP_PATH}" >&2
  exit 3
fi

if [[ ! -f "${DMG_PATH}" ]]; then
  echo "[release] dmg not found: ${DMG_PATH}" >&2
  exit 4
fi

echo "[release] codesigning app"
codesign --force --deep --options runtime --timestamp --sign "${SIGNING_IDENTITY}" "${APP_PATH}"
codesign --verify --deep --strict --verbose=2 "${APP_PATH}"

echo "[release] codesigning dmg"
codesign --force --timestamp --sign "${SIGNING_IDENTITY}" "${DMG_PATH}"
codesign --verify --verbose=2 "${DMG_PATH}"

echo "[release] notarizing dmg"
xcrun notarytool submit "${DMG_PATH}" \
  --apple-id "${APPLE_ID}" \
  --team-id "${APPLE_TEAM_ID}" \
  --password "${APPLE_APP_PASSWORD}" \
  --wait

echo "[release] stapling"
xcrun stapler staple "${APP_PATH}"
xcrun stapler validate "${APP_PATH}"
xcrun stapler staple "${DMG_PATH}"
xcrun stapler validate "${DMG_PATH}"

echo "[release] local quarantine/spctl check"
QUARANTINE_TAG="0081;$(date +%s);AegisOS;"
xattr -w com.apple.quarantine "${QUARANTINE_TAG}" "${APP_PATH}"
spctl --assess --type execute --verbose=4 "${APP_PATH}"

echo "[release] PASS: codesign + notarize + staple + quarantine check"
echo "[release] NOTE: clean-machine Gatekeeper check is still required as final manual gate."
