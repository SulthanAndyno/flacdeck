"""Music library organizer (`Artist/Album/NN - Title.flac` + `.lrc`)."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from flacdeck.metadata import read_flac_metadata


@dataclass
class OrganizeStats:
    """Summary counters for library organization."""

    total: int = 0
    copied_flac: int = 0
    skipped_flac: int = 0
    copied_lrc: int = 0
    missing_lrc: int = 0
    errors: int = 0


def organize_library(
    source_dir: Path,
    library_dir: Path,
    fallback_filename: bool = True,
    dry_run: bool = False,
    console: Console | None = None,
) -> OrganizeStats:
    """Organize FLAC and LRC files from source_dir into library_dir/Artist/Album/."""
    out = console or Console()
    stats = OrganizeStats()

    if not source_dir.exists():
        out.print(f"[red]Source folder tidak ditemukan:[/red] {source_dir}")
        return stats

    if not dry_run:
        library_dir.mkdir(parents=True, exist_ok=True)

    flac_files = sorted(source_dir.rglob("*.flac"))
    stats.total = len(flac_files)

    if not flac_files:
        out.print("[yellow]Tidak ada file FLAC ditemukan untuk dirapikan.[/yellow]")
        return stats

    for flac_file in flac_files:
        try:
            meta = read_flac_metadata(flac_file, fallback_filename=fallback_filename)
            album_folder = library_dir / meta.artist / meta.album
            if not dry_run:
                album_folder.mkdir(parents=True, exist_ok=True)

            base_filename = f"{meta.track_number} - {meta.title}"
            dest_flac = album_folder / f"{base_filename}.flac"

            if dest_flac.exists():
                out.print(f"[dim]SKIP[/dim]   {meta.artist} / {meta.album} / {dest_flac.name}")
                stats.skipped_flac += 1
            else:
                if not dry_run:
                    shutil.copy2(flac_file, dest_flac)
                out.print(f"[green]COPY[/green]   {meta.artist} / {meta.album} / {dest_flac.name}")
                stats.copied_flac += 1

            source_lrc = flac_file.with_suffix(".lrc")
            if source_lrc.exists():
                dest_lrc = album_folder / f"{base_filename}.lrc"
                if not dest_lrc.exists():
                    if not dry_run:
                        shutil.copy2(source_lrc, dest_lrc)
                    stats.copied_lrc += 1
            else:
                stats.missing_lrc += 1

        except Exception as err:
            out.print(f"[red]ERROR[/red]  {flac_file.name}: {err}")
            stats.errors += 1

    return stats
