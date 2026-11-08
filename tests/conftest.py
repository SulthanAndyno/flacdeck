"""Pytest fixtures for generating real minimal FLAC files on Linux."""

from __future__ import annotations

import shutil
import subprocess
import wave
from collections.abc import Callable
from pathlib import Path

import pytest
from mutagen.flac import FLAC


def _create_minimal_wav(wav_path: Path) -> None:
    """Create a 0.1s silent 44.1kHz 16-bit mono WAV file."""
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b"\x00\x00" * 4410)


@pytest.fixture
def make_flac(tmp_path: Path) -> Callable[..., Path]:
    """Factory fixture that generates a real valid FLAC file with customizable Vorbis tags."""

    def _make(
        filename: str = "sample.flac",
        artist: str | None = "YOASOBI",
        album: str | None = "THE BOOK",
        title: str | None = "Yoru ni Kakeru",
        tracknumber: str | None = "1/9",
        subdir: Path | None = None,
    ) -> Path:
        target_dir = subdir or tmp_path
        target_dir.mkdir(parents=True, exist_ok=True)
        flac_path = target_dir / filename
        wav_path = target_dir / f".tmp_{filename}.wav"

        _create_minimal_wav(wav_path)
        flac_bin = shutil.which("flac")
        if not flac_bin:
            pytest.skip("`flac` CLI binary not installed on system")

        subprocess.run(
            [flac_bin, "--silent", "--force", str(wav_path), "-o", str(flac_path)],
            check=True,
        )
        wav_path.unlink(missing_ok=True)

        audio = FLAC(flac_path)
        if artist is not None:
            audio["ARTIST"] = artist
        if album is not None:
            audio["ALBUM"] = album
        if title is not None:
            audio["TITLE"] = title
        if tracknumber is not None:
            audio["TRACKNUMBER"] = tracknumber
        audio.save()
        return flac_path

    return _make
