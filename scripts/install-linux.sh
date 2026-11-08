#!/usr/bin/env bash
set -euo pipefail

# Universal Linux dependency & CLI installer for flacdeck
# Supports: Arch/Manjaro (pacman), Ubuntu/Debian/Pop!_OS (apt),
#           Fedora/RHEL (dnf), openSUSE (zypper), Alpine (apk)

echo "==> Detecting Linux distribution & package manager..."

install_system_deps() {
    if command -v pacman >/dev/null 2>&1; then
        echo "==> Detected Arch-based distro (pacman)"
        sudo pacman -S --needed --noconfirm flac rsync util-linux udisks2 libnotify python
    elif command -v apt-get >/dev/null 2>&1; then
        echo "==> Detected Debian/Ubuntu-based distro (apt)"
        sudo apt-get update
        sudo apt-get install -y flac rsync util-linux udisks2 libnotify-bin python3 python3-venv python3-pip
    elif command -v dnf >/dev/null 2>&1; then
        echo "==> Detected Fedora/RHEL-based distro (dnf)"
        sudo dnf install -y flac rsync util-linux udisks2 libnotify python3 python3-pip
    elif command -v zypper >/dev/null 2>&1; then
        echo "==> Detected openSUSE (zypper)"
        sudo zypper install -y flac rsync util-linux udisks2 libnotify-tools python3 python3-pip
    elif command -v apk >/dev/null 2>&1; then
        echo "==> Detected Alpine Linux (apk)"
        sudo apk add flac rsync util-linux udisks2 libnotify python3 py3-pip
    else
        echo "Warning: Package manager not recognized. Please install manually: flac, rsync, lsblk, udisksctl, notify-send"
    fi
}

install_system_deps

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if command -v uv >/dev/null 2>&1; then
    echo "==> Installing flacdeck CLI via uv..."
    uv tool install --editable "${PROJECT_ROOT}" --force
elif command -v pipx >/dev/null 2>&1; then
    echo "==> Installing flacdeck CLI via pipx..."
    pipx install --editable "${PROJECT_ROOT}" --force
else
    echo "==> Installing flacdeck CLI into user virtualenv (~/.local/bin)..."
    mkdir -p "${HOME}/.local/share/flacdeck-venv" "${HOME}/.local/bin"
    python3 -m venv "${HOME}/.local/share/flacdeck-venv"
    "${HOME}/.local/share/flacdeck-venv/bin/pip" install --upgrade "${PROJECT_ROOT}"
    ln -sf "${HOME}/.local/share/flacdeck-venv/bin/flacdeck" "${HOME}/.local/bin/flacdeck"
fi

echo "==> Done! Run 'flacdeck' to open the interactive menu."
