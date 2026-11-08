"""FLAC metadata inspection, sanitization for exFAT/FAT32, and tag helpers."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from mutagen.flac import FLAC

EXFAT_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass(frozen=True)
class TrackMetadata:
    """Normalized FLAC track metadata safe for exFAT/FAT32 filesystems."""

    artist: str
    album: str
    title: str
    track_number: str
    raw_artist: str
    raw_title: str
    has_required_tags: bool


def clean_name(name: str) -> str:
    """Clean characters that are illegal on FAT32/exFAT filesystems."""
    cleaned = name.strip()
    cleaned = EXFAT_ILLEGAL_CHARS.sub("_", cleaned)
    cleaned = cleaned.rstrip(" .")
    return cleaned if cleaned else "Unknown"


def format_track(track: str) -> str:
    """Normalize track number strings (e.g. '1', '01', '3/12') into 2-digit format."""
    if not track:
        return "00"

    match = re.match(r"^\s*(\d+)", track)
    if not match:
        return "00"

    number = int(match.group(1))
    return f"{number:02d}"


def parse_filename_fallback(stem: str) -> tuple[str, str]:
    """Parse 'Artist - Title' from a filename stem when tags are missing."""
    if " - " in stem:
        parts = stem.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()
    return "", stem.strip()


def read_flac_metadata(file_path: Path, fallback_filename: bool = True) -> TrackMetadata:
    """Read metadata from a FLAC file with optional filename fallback."""
    audio = FLAC(file_path)

    artist_list = audio.get("artist", [""])
    album_list = audio.get("album", [""])
    title_list = audio.get("title", [""])
    track_list = audio.get("tracknumber", [""])

    raw_artist = str(artist_list[0]).strip() if artist_list else ""
    raw_album = str(album_list[0]).strip() if album_list else ""
    raw_title = str(title_list[0]).strip() if title_list else ""
    raw_track = str(track_list[0]).strip() if track_list else ""

    if fallback_filename and (not raw_artist or not raw_title):
        fb_artist, fb_title = parse_filename_fallback(file_path.stem)
        if not raw_artist and fb_artist:
            raw_artist = fb_artist
        if not raw_title and fb_title:
            raw_title = fb_title

    has_required = bool(raw_artist and raw_title)

    artist = clean_name(raw_artist) if raw_artist else "Unknown Artist"
    album = clean_name(raw_album) if raw_album else "Unknown Album"
    title = clean_name(raw_title) if raw_title else clean_name(file_path.stem)
    track_number = format_track(raw_track)

    return TrackMetadata(
        artist=artist,
        album=album,
        title=title,
        track_number=track_number,
        raw_artist=raw_artist,
        raw_title=raw_title,
        has_required_tags=has_required,
    )


def embed_lyrics_in_flac(file_path: Path, synced_lyrics: str) -> bool:
    """Embed synced lyrics into the FLAC VORBIS_COMMENT 'LYRICS' tag."""
    try:
        audio = FLAC(file_path)
        audio["LYRICS"] = synced_lyrics
        audio.save()
        return True
    except Exception:
        return False


def verify_flac_integrity(file_path: Path) -> bool:
    """Verify FLAC stream integrity using system `flac -t` or Mutagen fallback."""
    flac_bin = shutil.which("flac")
    if flac_bin:
        result = subprocess.run(
            [flac_bin, "-t", "--silent", str(file_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0

    try:
        audio = FLAC(file_path)
        return bool(audio.info.total_samples >= 0)
    except Exception:
        return False
