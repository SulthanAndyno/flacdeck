"""Tests for exFAT sanitization, track formatting, and FLAC metadata extraction."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from mutagen.flac import FLAC

from flacdeck.metadata import (
    clean_name,
    embed_lyrics_in_flac,
    format_track,
    parse_filename_fallback,
    read_flac_metadata,
    verify_flac_integrity,
)


def test_clean_name_exfat_sanitization() -> None:
    """Illegal exFAT/FAT32 characters and trailing dots/spaces must be sanitized."""
    raw = 'AC/DC: Back*In?Black "Live" <2026>|Test'
    assert clean_name(raw) == "AC_DC_ Back_In_Black _Live_ _2026__Test"
    assert clean_name("Album Name...   ") == "Album Name"
    assert clean_name("   ...   ") == "Unknown"


def test_format_track_variations() -> None:
    """Track numbers should normalize to 2-digit zero-padded strings."""
    assert format_track("1") == "01"
    assert format_track("07") == "07"
    assert format_track("3/12") == "03"
    assert format_track("") == "00"
    assert format_track("A1") == "00"


def test_parse_filename_fallback() -> None:
    """Filename stems in 'Artist - Title' format should split cleanly."""
    artist, title = parse_filename_fallback("The Weeknd - After Hours")
    assert artist == "The Weeknd"
    assert title == "After Hours"

    no_artist, just_title = parse_filename_fallback("Track Without Separator")
    assert no_artist == ""
    assert just_title == "Track Without Separator"


def test_read_flac_metadata_and_fallback(make_flac: Callable[..., Path]) -> None:
    """FLAC files with missing tags should fall back to filename when enabled."""
    flac_file = make_flac(
        filename="ClariS - Hitorigoto.flac",
        artist=None,
        album=None,
        title=None,
        tracknumber="2",
    )

    meta_with_fb = read_flac_metadata(flac_file, fallback_filename=True)
    assert meta_with_fb.has_required_tags is True
    assert meta_with_fb.artist == "ClariS"
    assert meta_with_fb.title == "Hitorigoto"
    assert meta_with_fb.album == "Unknown Album"
    assert meta_with_fb.track_number == "02"

    meta_no_fb = read_flac_metadata(flac_file, fallback_filename=False)
    assert meta_no_fb.has_required_tags is False


def test_embed_lyrics_and_verify_integrity(make_flac: Callable[..., Path]) -> None:
    """Embedding synced lyrics should persist in Vorbis comments and keep FLAC valid."""
    flac_file = make_flac(filename="valid.flac")
    lrc_text = "[00:01.00] Hello Linux World"

    assert embed_lyrics_in_flac(flac_file, lrc_text) is True
    audio = FLAC(flac_file)
    assert audio["LYRICS"][0] == lrc_text
    assert verify_flac_integrity(flac_file) is True
