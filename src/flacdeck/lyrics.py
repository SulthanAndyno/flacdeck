"""Synced lyrics fetcher from LRCLIB with search fallback and FLAC tag embedding."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from rich.console import Console

from flacdeck.config import AppConfig
from flacdeck.metadata import embed_lyrics_in_flac, read_flac_metadata


@dataclass
class LyricsStats:
    """Summary counters for a lyrics download batch."""

    total: int = 0
    saved: int = 0
    skipped: int = 0
    not_found: int = 0
    no_metadata: int = 0
    errors: int = 0


def fetch_lrclib_exact(
    artist: str,
    title: str,
    api_url: str = "https://lrclib.net/api/get",
    timeout: int = 10,
) -> dict[str, Any] | None:
    """Query LRCLIB exact endpoint for artist and track title."""
    try:
        response = requests.get(
            api_url,
            params={"artist_name": artist, "track_name": title},
            headers={"User-Agent": "flacdeck/2.0.0 (Linux)"},
            timeout=timeout,
        )
        if response.status_code != 200:
            return None
        payload = response.json()
        return payload if isinstance(payload, dict) else None
    except requests.RequestException:
        return None


def fetch_lrclib_search_fallback(
    artist: str,
    title: str,
    search_url: str = "https://lrclib.net/api/search",
    timeout: int = 10,
) -> dict[str, Any] | None:
    """Fallback to LRCLIB search endpoint when exact match misses."""
    try:
        response = requests.get(
            search_url,
            params={"q": f"{artist} {title}"},
            headers={"User-Agent": "flacdeck/2.0.0 (Linux)"},
            timeout=timeout,
        )
        if response.status_code != 200:
            return None
        results = response.json()
        if not isinstance(results, list):
            return None
        for item in results:
            if isinstance(item, dict) and item.get("syncedLyrics"):
                return item
        return None
    except requests.RequestException:
        return None


def get_synced_lyrics(
    artist: str,
    title: str,
    config: AppConfig,
    use_search_fallback: bool = True,
) -> str | None:
    """Retrieve synced LRC string from LRCLIB using exact match + optional search fallback."""
    exact = fetch_lrclib_exact(
        artist=artist,
        title=title,
        api_url=config.lrclib_api,
        timeout=config.request_timeout,
    )
    if exact and exact.get("syncedLyrics"):
        return str(exact["syncedLyrics"])

    if use_search_fallback:
        fallback = fetch_lrclib_search_fallback(
            artist=artist,
            title=title,
            search_url=config.lrclib_search_api,
            timeout=config.request_timeout,
        )
        if fallback and fallback.get("syncedLyrics"):
            return str(fallback["syncedLyrics"])

    return None


def process_lyrics_folder(
    folder: Path,
    config: AppConfig,
    console: Console | None = None,
    force: bool = False,
) -> LyricsStats:
    """Scan folder for FLAC files and download synced .lrc files."""
    out = console or Console()
    stats = LyricsStats()

    if not folder.exists():
        out.print(f"[red]Folder tidak ditemukan:[/red] {folder}")
        return stats

    flac_files = sorted(folder.rglob("*.flac"))
    stats.total = len(flac_files)

    if not flac_files:
        out.print("[yellow]Tidak ada file FLAC ditemukan.[/yellow]")
        return stats

    out.print(f"Ditemukan [bold cyan]{stats.total}[/bold cyan] file FLAC di [dim]{folder}[/dim]\n")

    for flac_file in flac_files:
        lrc_file = flac_file.with_suffix(".lrc")

        if lrc_file.exists() and not force:
            out.print(f"[dim]SKIP[/dim]    {flac_file.name}")
            stats.skipped += 1
            continue

        try:
            meta = read_flac_metadata(
                flac_file,
                fallback_filename=config.fallback_filename_parse,
            )
        except Exception as err:
            out.print(f"[red]ERROR[/red]   {flac_file.name}: {err}")
            stats.errors += 1
            continue

        if not meta.has_required_tags:
            out.print(f"[yellow]NO META[/yellow] {flac_file.name}")
            stats.no_metadata += 1
            continue

        out.print(f"[cyan]SEARCH[/cyan]  {meta.raw_artist} - {meta.raw_title}")
        synced_lyrics = get_synced_lyrics(
            artist=meta.raw_artist,
            title=meta.raw_title,
            config=config,
        )

        if not synced_lyrics:
            out.print("  [yellow]-> Synced lyrics tidak ditemukan[/yellow]")
            stats.not_found += 1
            continue

        try:
            lrc_file.write_text(synced_lyrics, encoding="utf-8")
            if config.embed_lyrics_tag:
                embed_lyrics_in_flac(flac_file, synced_lyrics)
            out.print(f"  [green]-> SAVED[/green]  {lrc_file.name}")
            stats.saved += 1
        except OSError as err:
            out.print(f"  [red]-> Gagal menyimpan LRC: {err}[/red]")
            stats.errors += 1

    return stats
