"""Rich + Typer CLI with Interactive Menu for FlacDeck on Linux."""

from __future__ import annotations

import contextlib
import shutil
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from flacdeck.config import load_config
from flacdeck.lyrics import process_lyrics_folder
from flacdeck.metadata import read_flac_metadata, verify_flac_integrity
from flacdeck.notify import send_notification
from flacdeck.organizer import organize_library
from flacdeck.sdcard import (
    detect_sdcards,
    safe_unmount_sdcard,
    sync_to_sdcard,
)

app = typer.Typer(
    name="flacdeck",
    help="Linux-native CLI toolkit for FLAC synced lyrics, library organization, and SD card sync.",
    add_completion=True,
)
console = Console()


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    """Jalankan menu interaktif secara otomatis jika dipanggil tanpa subcommand."""
    if ctx.invoked_subcommand is None:
        interactive_menu()


@app.command()
def menu() -> None:
    """Buka menu interaktif FlacDeck."""
    interactive_menu()


def interactive_menu() -> None:
    """Loop menu interaktif menggunakan Rich Prompt."""
    while True:
        cfg = load_config()
        songs_count = len(list(cfg.songs_dir.rglob("*.flac"))) if cfg.songs_dir.exists() else 0
        lib_count = len(list(cfg.library_dir.rglob("*.flac"))) if cfg.library_dir.exists() else 0
        sdcards = detect_sdcards()
        sd_info = (
            f"[bold green]{sdcards[0].label} ({sdcards[0].mountpoint})[/bold green]"
            if sdcards
            else "[dim]Tidak terpasang[/dim]"
        )

        console.print()
        caption_str = (
            f"Songs: [cyan]{songs_count}[/cyan] FLAC | "
            f"Library: [green]{lib_count}[/green] FLAC | SD Card: {sd_info}"
        )
        menu_table = Table(
            show_header=True,
            header_style="bold cyan",
            border_style="bright_blue",
            title="[bold white]FlacDeck v2.0 — Interactive Menu[/bold white]",
            caption=caption_str,
        )
        menu_table.add_column("No", justify="center", style="bold yellow", width=4)
        menu_table.add_column("Menu Aksi", style="bold white")
        menu_table.add_column("Deskripsi", style="dim")

        menu_table.add_row(
            "1", "Status & Cek SD Card", "Ringkasan koleksi FLAC/LRC & partisi SD Card"
        )
        menu_table.add_row("2", "Download Synced Lyrics", "Cari .lrc di LRCLIB + embed ke tag FLAC")
        menu_table.add_row("3", "Rapikan ke Library", "Copy ke library/Artis/Album/NN - Judul.flac")
        menu_table.add_row(
            "4", "Jalankan Full Pipeline", "Otomatis Download Lyrics -> Organize -> Notify"
        )
        menu_table.add_row(
            "5", "Sync ke SD Card", "Salin library ke SD Card via rsync (exFAT-safe)"
        )
        menu_table.add_row(
            "6", "Sync + Safe Unmount SD Card", "Salin library lalu sync & udisksctl unmount"
        )
        menu_table.add_row(
            "7", "Doctor & Audit FLAC", "Cek dependency Linux & validasi stream FLAC"
        )
        menu_table.add_row("0", "Keluar (Exit)", "Tutup menu interaktif")

        console.print(menu_table)

        try:
            choice = Prompt.ask(
                "\n[bold cyan]Pilih nomor menu[/bold cyan]",
                choices=["0", "1", "2", "3", "4", "5", "6", "7", "q"],
                default="1",
            )
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Keluar dari menu. Sampai jumpa![/dim]")
            break

        console.print()
        if choice in ("0", "q"):
            console.print("[dim]Keluar dari menu. Sampai jumpa![/dim]")
            break
        elif choice == "1":
            status()
        elif choice == "2":
            lyrics()
        elif choice == "3":
            organize()
        elif choice == "4":
            pipeline(notify=True)
        elif choice == "5":
            dry = Confirm.ask("Ingin simulasi (dry-run) terlebih dahulu?", default=False)
            with contextlib.suppress(typer.Exit):
                sdcard(dry_run=dry, unmount=False)
        elif choice == "6":
            with contextlib.suppress(typer.Exit):
                sdcard(dry_run=False, unmount=True)
        elif choice == "7":
            verify = Confirm.ask(
                "Sekalian uji keutuhan audio (`flac -t`) semua lagu?", default=False
            )
            doctor(verify_stream=verify)


@app.command()
def status(
    songs_dir: Annotated[
        Path | None, typer.Option("--songs-dir", "-s", help="Override songs folder")
    ] = None,
    library_dir: Annotated[
        Path | None, typer.Option("--library-dir", "-l", help="Override library folder")
    ] = None,
) -> None:
    """Tampilkan ringkasan status folder musik dan deteksi SD Card di Linux."""
    cfg = load_config()
    s_dir = songs_dir or cfg.songs_dir
    l_dir = library_dir or cfg.library_dir

    table = Table(title="Status Koleksi Musik FLAC", show_header=True, header_style="bold cyan")
    table.add_column("Folder", style="bold")
    table.add_column("Path", style="dim")
    table.add_column("FLAC", justify="right", style="green")
    table.add_column("LRC", justify="right", style="yellow")

    for label, path in [
        ("Songs (Staging)", s_dir),
        ("Library (Organized)", l_dir),
        ("Done (Archive)", cfg.done_dir),
    ]:
        if path.exists():
            flacs = len(list(path.rglob("*.flac")))
            lrcs = len(list(path.rglob("*.lrc")))
            table.add_row(label, str(path), str(flacs), str(lrcs))
        else:
            table.add_row(label, f"{path} (belum ada)", "0", "0")

    console.print(table)

    sdcards = detect_sdcards()
    if sdcards:
        sd_table = Table(
            title="SD Card / Removable Drive Terdeteksi (lsblk)",
            header_style="bold green",
        )
        sd_table.add_column("Device")
        sd_table.add_column("Label")
        sd_table.add_column("Size", justify="right")
        sd_table.add_column("FS Type")
        sd_table.add_column("Mountpoint")
        for dev in sdcards:
            sd_table.add_row(dev.path, dev.label, dev.size, dev.fstype, dev.mountpoint)
        console.print(sd_table)
    else:
        console.print("[dim]Tidak ada SD Card / removable media yang ter-mount saat ini.[/dim]")


@app.command()
def doctor(
    songs_dir: Annotated[
        Path | None, typer.Option("--songs-dir", "-s", help="Override songs folder")
    ] = None,
    verify_stream: Annotated[
        bool, typer.Option("--verify-stream", help="Uji integritas stream FLAC dengan `flac -t`")
    ] = False,
) -> None:
    """Periksa ketersediaan Linux system tools & audit tag metadata FLAC."""
    cfg = load_config()
    s_dir = songs_dir or cfg.songs_dir

    tools_table = Table(title="Linux System Dependencies Check", header_style="bold magenta")
    tools_table.add_column("Binary", style="bold")
    tools_table.add_column("Fungsi")
    tools_table.add_column("Status")

    required_bins = [
        ("flac", "Verifikasi stream audio FLAC (`flac -t`)"),
        ("metaflac", "Inspeksi & manipulasi Vorbis comment tag"),
        ("rsync", "Sinkronisasi efisien ke SD card FAT32/exFAT"),
        ("lsblk", "Deteksi otomatis partisi & mountpoint SD card"),
        ("udisksctl", "Safe unmount tanpa perlu sudo"),
        ("notify-send", "Notifikasi desktop untuk systemd watcher"),
    ]

    for binary, desc in required_bins:
        found = shutil.which(binary)
        status_str = f"[green]OK ({found})[/green]" if found else "[yellow]MISSING[/yellow]"
        tools_table.add_row(binary, desc, status_str)

    console.print(tools_table)

    if not s_dir.exists():
        console.print(f"[yellow]Folder songs tidak ditemukan: {s_dir}[/yellow]")
        return

    flacs = sorted(s_dir.rglob("*.flac"))
    console.print(f"\nMemeriksa [bold]{len(flacs)}[/bold] file FLAC di [cyan]{s_dir}[/cyan]...")

    missing_tags = 0
    corrupt_files = 0
    for f in flacs:
        meta = read_flac_metadata(f, fallback_filename=False)
        if not meta.has_required_tags:
            missing_tags += 1
            console.print(f"  [yellow]TAG INCOMPLETE[/yellow] {f.name}")
        if verify_stream and not verify_flac_integrity(f):
            corrupt_files += 1
            console.print(f"  [red]CORRUPT STREAM[/red] {f.name}")

    if missing_tags == 0 and corrupt_files == 0:
        console.print("[bold green]Semua file FLAC memiliki metadata lengkap & sehat![/bold green]")
    else:
        console.print(
            f"[yellow]Ringkasan Audit:[/yellow] {missing_tags} tag kurang lengkap, "
            f"{corrupt_files} stream bermasalah."
        )


@app.command()
def lyrics(
    songs_dir: Annotated[
        Path | None, typer.Option("--songs-dir", "-s", help="Folder sumber file FLAC")
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Download ulang walaupun file .lrc sudah ada")
    ] = False,
) -> None:
    """Ambil synced lyrics (.lrc) dari LRCLIB dengan fallback pencarian otomatis."""
    cfg = load_config()
    target_folder = songs_dir or cfg.songs_dir

    console.print(
        Panel.fit(
            f"[bold cyan]FLAC Synced Lyrics Downloader[/bold cyan]\nFolder: {target_folder}",
            border_style="cyan",
        )
    )
    stats = process_lyrics_folder(target_folder, config=cfg, console=console, force=force)
    console.print(
        f"\n[bold]Selesai:[/bold] Saved={stats.saved}, Skipped={stats.skipped}, "
        f"NotFound={stats.not_found}, NoMeta={stats.no_metadata}, Errors={stats.errors}"
    )


@app.command()
def organize(
    songs_dir: Annotated[
        Path | None, typer.Option("--songs-dir", "-s", help="Folder sumber FLAC")
    ] = None,
    library_dir: Annotated[
        Path | None, typer.Option("--library-dir", "-l", help="Folder target library")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-n", help="Simulasi tanpa menyalin file")
    ] = False,
) -> None:
    """Rapikan FLAC + LRC ke struktur `library/Artis/Album/NN - Judul.flac`."""
    cfg = load_config()
    s_dir = songs_dir or cfg.songs_dir
    l_dir = library_dir or cfg.library_dir

    console.print(
        Panel.fit(
            f"[bold green]Music Library Organizer[/bold green]\n"
            f"Source : {s_dir}\n"
            f"Target : {l_dir}\n"
            f"Dry Run: {dry_run}",
            border_style="green",
        )
    )
    stats = organize_library(
        source_dir=s_dir,
        library_dir=l_dir,
        fallback_filename=cfg.fallback_filename_parse,
        dry_run=dry_run,
        console=console,
    )
    console.print(
        f"\n[bold]Selesai:[/bold] Copied FLAC={stats.copied_flac}, "
        f"Skipped FLAC={stats.skipped_flac}, Copied LRC={stats.copied_lrc}, "
        f"No LRC={stats.missing_lrc}, Errors={stats.errors}"
    )


@app.command()
def pipeline(
    songs_dir: Annotated[
        Path | None, typer.Option("--songs-dir", "-s", help="Folder sumber FLAC")
    ] = None,
    library_dir: Annotated[
        Path | None, typer.Option("--library-dir", "-l", help="Folder target library")
    ] = None,
    notify: Annotated[
        bool, typer.Option("--notify", help="Kirim notifikasi desktop via notify-send")
    ] = False,
) -> None:
    """Jalankan pipeline otomatis (Ambil Lirik -> Rapikan ke Library -> Notifikasi)."""
    cfg = load_config()
    s_dir = songs_dir or cfg.songs_dir
    l_dir = library_dir or cfg.library_dir

    lrc_stats = process_lyrics_folder(s_dir, config=cfg, console=console)
    org_stats = organize_library(
        source_dir=s_dir,
        library_dir=l_dir,
        fallback_filename=cfg.fallback_filename_parse,
        console=console,
    )

    summary = (
        f"Lirik baru: {lrc_stats.saved} | Lagu dirapikan: {org_stats.copied_flac} "
        f"(Total: {org_stats.total} FLAC)"
    )
    console.print(Panel(summary, title="Pipeline Selesai", border_style="bold green"))

    if notify:
        send_notification("FlacDeck", summary)


@app.command()
def sdcard(
    mountpoint: Annotated[
        Path | None,
        typer.Option("--mount", "-m", help="Path mountpoint SD Card (otomatis jika dikosongkan)"),
    ] = None,
    subdir: Annotated[
        str, typer.Option("--subdir", help="Subfolder tujuan di dalam SD Card")
    ] = "Music",
    library_dir: Annotated[
        Path | None, typer.Option("--library-dir", "-l", help="Folder library sumber")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-n", help="Simulasi rsync tanpa menulis ke SD Card")
    ] = False,
    unmount: Annotated[
        bool,
        typer.Option("--unmount", "-u", help="Otomatis sync + udisksctl unmount setelah selesai"),
    ] = False,
) -> None:
    """Deteksi SD Card otomatis, jalankan rsync exFAT-safe, dan dukung safe unmount."""
    cfg = load_config()
    l_dir = library_dir or cfg.library_dir

    selected_dev = None
    if mountpoint is None:
        devices = detect_sdcards()
        if not devices:
            console.print(
                "[red]Tidak ada SD Card / removable media yang terdeteksi lewat `lsblk`.[/red]\n"
                "Colok SD Card terlebih dahulu atau gunakan `--mount /path/ke/sdcard`."
            )
            raise typer.Exit(code=1)
        selected_dev = devices[0]
        target_mount = Path(selected_dev.mountpoint)
        console.print(
            f"[green]SD Card terdeteksi:[/green] {selected_dev.label} "
            f"({selected_dev.path}, {selected_dev.size}, {selected_dev.fstype}) -> {target_mount}"
        )
    else:
        target_mount = mountpoint

    target_dir = target_mount / subdir if subdir else target_mount
    console.print(
        f"Sinkronisasi [cyan]{l_dir}[/cyan] -> [bold yellow]{target_dir}[/bold yellow]..."
    )

    rc = sync_to_sdcard(library_dir=l_dir, target_dir=target_dir, dry_run=dry_run)
    if rc != 0:
        console.print(f"[red]rsync gagal dengan kode exit {rc}[/red]")
        raise typer.Exit(code=rc)

    console.print("[bold green]Sinkronisasi rsync selesai![/bold green]")

    if unmount and not dry_run:
        if selected_dev is None:
            devices = detect_sdcards()
            for dev in devices:
                if Path(dev.mountpoint) == target_mount:
                    selected_dev = dev
                    break

        if selected_dev:
            console.print(f"Melakukan flush buffer (`sync`) & unmount `{selected_dev.path}`...")
            ok, msg = safe_unmount_sdcard(selected_dev.path)
            if ok:
                console.print(f"[bold green]SD Card aman dicabut![/bold green] ({msg})")
            else:
                console.print(f"[red]Gagal unmount:[/red] {msg}")
                raise typer.Exit(code=1)
        else:
            console.print(
                "[yellow]Device block tidak terdeteksi otomatis untuk unmount. "
                "Jalankan `sync && udisksctl unmount -b /dev/<sdX1>` secara manual.[/yellow]"
            )


if __name__ == "__main__":
    app()
