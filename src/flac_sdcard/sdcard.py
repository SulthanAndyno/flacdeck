"""Linux block device discovery (`lsblk`), `rsync` SD card sync, and `udisksctl` safe unmount."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SYSTEM_MOUNT_PREFIXES = ("/boot", "/efi", "/snap")
SUPPORTED_SD_FSTYPES = {"vfat", "exfat", "fat32"}


@dataclass(frozen=True)
class BlockDevice:
    """Representation of a mounted removable/SD block device on Linux."""

    name: str
    path: str
    size: str
    fstype: str
    label: str
    mountpoint: str
    removable: bool


def parse_lsblk_json(raw_json: str) -> list[BlockDevice]:
    """Parse `lsblk --json` output and return candidate SD card / removable partitions."""
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        return []

    blockdevices = data.get("blockdevices", [])
    if not isinstance(blockdevices, list):
        return []

    candidates: list[BlockDevice] = []

    def _visit(node: dict[str, Any], parent_rm: bool = False) -> None:
        name = str(node.get("name") or "")
        path = str(node.get("path") or (f"/dev/{name}" if name else ""))
        size = str(node.get("size") or "")
        fstype = str(node.get("fstype") or "").lower()
        label = str(node.get("label") or "")
        is_rm = bool(node.get("rm")) or bool(node.get("hotplug")) or parent_rm

        mountpoint = ""
        mp_list = node.get("mountpoints")
        if isinstance(mp_list, list) and mp_list:
            first_mp = mp_list[0]
            if first_mp:
                mountpoint = str(first_mp)
        elif node.get("mountpoint"):
            mountpoint = str(node.get("mountpoint"))

        is_system_mount = mountpoint == "/" or any(
            mountpoint.startswith(prefix) for prefix in SYSTEM_MOUNT_PREFIXES
        )
        is_media_mount = mountpoint.startswith(("/run/media/", "/media/", "/mnt/"))

        if (
            mountpoint
            and not is_system_mount
            and (is_media_mount or (is_rm and fstype in SUPPORTED_SD_FSTYPES))
        ):
            candidates.append(
                BlockDevice(
                    name=name,
                    path=path,
                    size=size,
                    fstype=fstype or "unknown",
                    label=label or name,
                    mountpoint=mountpoint,
                    removable=is_rm,
                )
            )

        children = node.get("children")
        if isinstance(children, list):
            for child in children:
                if isinstance(child, dict):
                    _visit(child, parent_rm=is_rm)

    for dev in blockdevices:
        if isinstance(dev, dict):
            _visit(dev)

    return candidates


def detect_sdcards() -> list[BlockDevice]:
    """Run `lsblk --json` on Linux to discover mounted SD cards / removable drives."""
    lsblk_bin = shutil.which("lsblk")
    if not lsblk_bin:
        return []

    result = subprocess.run(
        [
            lsblk_bin,
            "--json",
            "-o",
            "NAME,PATH,SIZE,FSTYPE,LABEL,RM,HOTPLUG,MOUNTPOINT,MOUNTPOINTS",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []

    return parse_lsblk_json(result.stdout)


def build_rsync_command(
    library_dir: Path,
    target_dir: Path,
    dry_run: bool = False,
    delete: bool = False,
) -> list[str]:
    """Construct an exFAT/FAT32-safe `rsync` command for syncing the music library."""
    src_str = f"{library_dir.resolve()}/"
    dst_str = f"{target_dir.resolve()}/"

    cmd = [
        "rsync",
        "-rtv",
        "--size-only",
        "--modify-window=2",
    ]
    if dry_run:
        cmd.append("--dry-run")
    if delete:
        cmd.append("--delete")

    cmd.extend([src_str, dst_str])
    return cmd


def sync_to_sdcard(
    library_dir: Path,
    target_dir: Path,
    dry_run: bool = False,
    delete: bool = False,
) -> int:
    """Execute `rsync` to copy organized library files to the SD card target directory."""
    if not library_dir.exists():
        raise FileNotFoundError(f"Library directory does not exist: {library_dir}")

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    cmd = build_rsync_command(
        library_dir=library_dir,
        target_dir=target_dir,
        dry_run=dry_run,
        delete=delete,
    )
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


def build_unmount_command(device_path: str) -> list[str]:
    """Build the `udisksctl unmount -b <device>` command."""
    return ["udisksctl", "unmount", "-b", device_path]


def safe_unmount_sdcard(device_path: str) -> tuple[bool, str]:
    """Flush filesystem buffers (`os.sync`) and safely unmount block device via `udisksctl`."""
    os.sync()

    udisks_bin = shutil.which("udisksctl")
    if not udisks_bin:
        return False, "udisksctl tidak ditemukan di sistem."

    cmd = build_unmount_command(device_path)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    output = (result.stdout or result.stderr).strip()
    return result.returncode == 0, output
