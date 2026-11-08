#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SYSTEMD_USER_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

if [[ -d "/workspace/Music/songs" ]]; then
    WATCH_DIR="/workspace/Music/songs"
else
    WATCH_DIR="${HOME}/Music/songs"
    mkdir -p "${WATCH_DIR}"
fi

echo "==> Installing systemd user units to ${SYSTEMD_USER_DIR} (watching ${WATCH_DIR})..."
mkdir -p "${SYSTEMD_USER_DIR}"

cat > "${SYSTEMD_USER_DIR}/flac-sdcard-watcher.path" <<EOF
[Unit]
Description=Watch ${WATCH_DIR} for new FLAC files
Documentation=https://github.com/SulthanAndyno/flac-sdcard-tools

[Path]
PathChanged=${WATCH_DIR}
Unit=flac-sdcard-watcher.service

[Install]
WantedBy=default.target
EOF

cp -v "${PROJECT_ROOT}/packaging/systemd/flac-sdcard-watcher.service" "${SYSTEMD_USER_DIR}/"

if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload
    systemctl --user enable --now flac-sdcard-watcher.path
    echo "==> flac-sdcard-watcher.path enabled and active!"
else
    echo "Warning: systemctl not found. Units copied but not enabled."
fi
