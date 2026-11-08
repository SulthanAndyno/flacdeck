"""Tests for LRCLIB lyrics fetching, search fallback, and folder processing."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock, patch

from flacdeck.config import AppConfig
from flacdeck.lyrics import get_synced_lyrics, process_lyrics_folder


def test_get_synced_lyrics_exact_and_fallback() -> None:
    """Should use exact match first and fallback to search API when exact returns 404."""
    cfg = AppConfig()

    mock_404 = MagicMock()
    mock_404.status_code = 404

    mock_search_200 = MagicMock()
    mock_search_200.status_code = 200
    mock_search_200.json.return_value = [
        {"trackName": "Starboy", "syncedLyrics": "[00:05.00] I'm tryna put you in the worst mood"}
    ]

    with patch("flacdeck.lyrics.requests.get", side_effect=[mock_404, mock_search_200]):
        lyrics = get_synced_lyrics("The Weeknd", "Starboy", config=cfg)
        assert lyrics == "[00:05.00] I'm tryna put you in the worst mood"


def test_process_lyrics_folder_saves_lrc_and_skips_existing(
    make_flac: Callable[..., Path], tmp_path: Path
) -> None:
    """Should write .lrc next to .flac and skip on subsequent runs."""
    songs_dir = tmp_path / "songs"
    flac_path = make_flac(
        filename="YOASOBI - Tabun.flac",
        artist="YOASOBI",
        title="Tabun",
        subdir=songs_dir,
    )
    cfg = AppConfig(songs_dir=songs_dir, embed_lyrics_tag=True)

    with patch(
        "flacdeck.lyrics.get_synced_lyrics",
        return_value="[00:01.00] Namida nagasu koto sura nai mama",
    ):
        stats1 = process_lyrics_folder(songs_dir, config=cfg)
        assert stats1.total == 1
        assert stats1.saved == 1
        assert flac_path.with_suffix(".lrc").exists()

        # Second run should skip existing .lrc
        stats2 = process_lyrics_folder(songs_dir, config=cfg)
        assert stats2.skipped == 1
        assert stats2.saved == 0
