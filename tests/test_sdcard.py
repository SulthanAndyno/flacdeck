"""Tests for Linux `lsblk --json` parsing, `rsync` command builder, and `udisksctl` unmount."""

from __future__ import annotations

from pathlib import Path

from flac_sdcard.sdcard import (
    build_rsync_command,
    build_unmount_command,
    parse_lsblk_json,
)

SAMPLE_LSBLK_JSON = """
{
  "blockdevices": [
    {
      "name": "nvme0n1",
      "path": "/dev/nvme0n1",
      "size": "512G",
      "fstype": null,
      "label": null,
      "rm": false,
      "hotplug": false,
      "mountpoints": [null],
      "children": [
        {
          "name": "nvme0n1p1",
          "path": "/dev/nvme0n1p1",
          "size": "512M",
          "fstype": "vfat",
          "label": "EFI",
          "rm": false,
          "hotplug": false,
          "mountpoints": ["/boot/efi"]
        },
        {
          "name": "nvme0n1p2",
          "path": "/dev/nvme0n1p2",
          "size": "511.5G",
          "fstype": "ext4",
          "label": "ROOT",
          "rm": false,
          "hotplug": false,
          "mountpoints": ["/"]
        }
      ]
    },
    {
      "name": "mmcblk0",
      "path": "/dev/mmcblk0",
      "size": "64G",
      "fstype": null,
      "label": null,
      "rm": true,
      "hotplug": true,
      "mountpoints": [null],
      "children": [
        {
          "name": "mmcblk0p1",
          "path": "/dev/mmcblk0p1",
          "size": "64G",
          "fstype": "exfat",
          "label": "WALKMAN_SD",
          "rm": true,
          "hotplug": true,
          "mountpoints": ["/run/media/Shuu/WALKMAN_SD"]
        }
      ]
    }
  ]
}
"""


def test_parse_lsblk_json_ignores_efi_and_finds_sdcard() -> None:
    """Should ignore /boot/efi vfat partition and detect removable SD card."""
    devices = parse_lsblk_json(SAMPLE_LSBLK_JSON)
    assert len(devices) == 1
    sd = devices[0]
    assert sd.name == "mmcblk0p1"
    assert sd.path == "/dev/mmcblk0p1"
    assert sd.fstype == "exfat"
    assert sd.label == "WALKMAN_SD"
    assert sd.mountpoint == "/run/media/Shuu/WALKMAN_SD"
    assert sd.removable is True


def test_build_rsync_and_unmount_commands(tmp_path: Path) -> None:
    """Should build FAT32/exFAT-safe rsync command with trailing slashes."""
    lib = tmp_path / "library"
    sd = tmp_path / "sdcard" / "Music"

    cmd = build_rsync_command(lib, sd, dry_run=True)
    assert cmd[:5] == ["rsync", "-rtv", "--size-only", "--modify-window=2", "--dry-run"]
    assert cmd[-2].endswith("/library/")
    assert cmd[-1].endswith("/sdcard/Music/")

    unmount_cmd = build_unmount_command("/dev/mmcblk0p1")
    assert unmount_cmd == ["udisksctl", "unmount", "-b", "/dev/mmcblk0p1"]
