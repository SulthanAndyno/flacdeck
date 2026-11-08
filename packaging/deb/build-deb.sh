#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-2.0.0}"
PKG_NAME="flac-sdcard-tools"
ARCH="all"
BUILD_ROOT="dist/deb/${PKG_NAME}_${VERSION}_${ARCH}"

echo "==> Building Debian package ${PKG_NAME}_${VERSION}_${ARCH}.deb..."
rm -rf "${BUILD_ROOT}"
mkdir -p "${BUILD_ROOT}/DEBIAN"
mkdir -p "${BUILD_ROOT}/usr/local/bin"
mkdir -p "${BUILD_ROOT}/usr/lib/systemd/user"

cat > "${BUILD_ROOT}/DEBIAN/control" <<EOF
Package: ${PKG_NAME}
Version: ${VERSION}
Section: sound
Priority: optional
Architecture: ${ARCH}
Depends: python3 (>= 3.10), python3-mutagen, python3-requests, python3-rich, python3-typer, flac, rsync, util-linux, udisks2, libnotify-bin
Maintainer: SulthanAndyno <https://github.com/SulthanAndyno>
Description: Linux-native FLAC synced lyrics downloader, library organizer, and SD card sync tool
 Automates downloading synced LRC files from LRCLIB, organizing FLAC tracks into
 exFAT-safe Artist/Album directories, and syncing to removable SD cards via rsync + udisksctl.
EOF

cat > "${BUILD_ROOT}/usr/local/bin/flac-sdcard" <<'EOF'
#!/usr/bin/env python3
from flac_sdcard.cli import app
if __name__ == "__main__":
    app()
EOF
chmod 0755 "${BUILD_ROOT}/usr/local/bin/flac-sdcard"
install -m 0644 packaging/systemd/flac-sdcard-watcher.path "${BUILD_ROOT}/usr/lib/systemd/user/flac-sdcard-watcher.path"
install -m 0644 packaging/systemd/flac-sdcard-watcher.service "${BUILD_ROOT}/usr/lib/systemd/user/flac-sdcard-watcher.service"

if command -v dpkg-deb >/dev/null 2>&1; then
    dpkg-deb --build --root-owner-group "${BUILD_ROOT}"
    echo "==> Created dist/deb/${PKG_NAME}_${VERSION}_${ARCH}.deb"
else
    echo "Warning: dpkg-deb not installed on this host; directory structure staged at ${BUILD_ROOT}"
fi
