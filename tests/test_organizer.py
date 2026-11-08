"""Tests for organizing FLAC + LRC files into Artist/Album/NN - Title structure."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from flac_sdcard.organizer import organize_library


def test_organize_library_copies_flac_and_lrc(
    make_flac: Callable[..., Path], tmp_path: Path
) -> None:
    """Should organize FLAC and matching LRC into sanitized Artist/Album folders."""
    songs_dir = tmp_path / "songs"
    library_dir = tmp_path / "library"

    flac_file = make_flac(
        filename="Aqours - SKY JOURNEY.flac",
        artist="Aqours",
        album="ラブライブ! Sunshine!!: Vol.1?",
        title="SKY JOURNEY",
        tracknumber="3/12",
        subdir=songs_dir,
    )
    lrc_file = flac_file.with_suffix(".lrc")
    lrc_file.write_text("[00:00.50] SKY JOURNEY lyrics", encoding="utf-8")

    stats = organize_library(source_dir=songs_dir, library_dir=library_dir)
    assert stats.total == 1
    assert stats.copied_flac == 1
    assert stats.copied_lrc == 1

    expected_dir = library_dir / "Aqours" / "ラブライブ! Sunshine!!_ Vol.1_"
    expected_flac = expected_dir / "03 - SKY JOURNEY.flac"
    expected_lrc = expected_dir / "03 - SKY JOURNEY.lrc"

    assert expected_flac.exists()
    assert expected_lrc.exists()

    # Running again should skip existing FLAC
    stats_repeat = organize_library(source_dir=songs_dir, library_dir=library_dir)
    assert stats_repeat.skipped_flac == 1
    assert stats_repeat.copied_flac == 0
