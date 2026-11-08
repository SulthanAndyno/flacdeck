"""Configuration management for FLAC SD Card Tools."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def get_default_base_dir() -> Path:
    """Detect /workspace/Music if present, otherwise fallback to standard Linux ~/Music."""
    workspace_music = Path("/workspace/Music")
    if workspace_music.exists():
        return workspace_music
    xdg_music = os.environ.get("XDG_MUSIC_DIR")
    if xdg_music:
        return Path(xdg_music).expanduser()
    return Path.home() / "Music"


DEFAULT_BASE_DIR = get_default_base_dir()


@dataclass(frozen=True)
class AppConfig:
    """Application paths and runtime settings."""

    songs_dir: Path = DEFAULT_BASE_DIR / "songs"
    library_dir: Path = DEFAULT_BASE_DIR / "library"
    done_dir: Path = DEFAULT_BASE_DIR / "done"
    no_lyrics_dir: Path = DEFAULT_BASE_DIR / "no-lyrics"
    covers_dir: Path = DEFAULT_BASE_DIR / "covers"
    lrclib_api: str = "https://lrclib.net/api/get"
    lrclib_search_api: str = "https://lrclib.net/api/search"
    request_timeout: int = 10
    embed_lyrics_tag: bool = True
    fallback_filename_parse: bool = True


def get_config_path() -> Path:
    """Return XDG config path for flac-sdcard-tools."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_config) if xdg_config else Path.home() / ".config"
    return base / "flac-sdcard-tools" / "config.toml"


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load configuration from TOML file or environment variables, falling back to defaults."""
    target_path = config_path or get_config_path()
    data: dict[str, object] = {}

    if target_path.exists():
        try:
            data = tomllib.loads(target_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    base_env = os.environ.get("FLAC_MUSIC_DIR")
    base_dir = Path(base_env) if base_env else DEFAULT_BASE_DIR

    songs_raw = data.get("songs_dir", os.environ.get("FLAC_SONGS_DIR", str(base_dir / "songs")))
    library_raw = data.get(
        "library_dir", os.environ.get("FLAC_LIBRARY_DIR", str(base_dir / "library"))
    )
    done_raw = data.get("done_dir", os.environ.get("FLAC_DONE_DIR", str(base_dir / "done")))
    no_lyrics_raw = data.get(
        "no_lyrics_dir", os.environ.get("FLAC_NO_LYRICS_DIR", str(base_dir / "no-lyrics"))
    )
    covers_raw = data.get("covers_dir", os.environ.get("FLAC_COVERS_DIR", str(base_dir / "covers")))

    timeout_raw = data.get("request_timeout", 10)
    timeout = int(timeout_raw) if isinstance(timeout_raw, (int, str)) else 10

    embed_raw = data.get("embed_lyrics_tag", True)
    fallback_raw = data.get("fallback_filename_parse", True)

    return AppConfig(
        songs_dir=Path(str(songs_raw)).expanduser(),
        library_dir=Path(str(library_raw)).expanduser(),
        done_dir=Path(str(done_raw)).expanduser(),
        no_lyrics_dir=Path(str(no_lyrics_raw)).expanduser(),
        covers_dir=Path(str(covers_raw)).expanduser(),
        request_timeout=timeout,
        embed_lyrics_tag=bool(embed_raw),
        fallback_filename_parse=bool(fallback_raw),
    )
