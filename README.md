# FLAC SD Card Tools v2.0 (Linux Edition)

[![Linux CI Pipeline](https://github.com/SulthanAndyno/flac-sdcard-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/SulthanAndyno/flac-sdcard-tools/actions/workflows/ci.yml)
[![Build & Release Linux Packages](https://github.com/SulthanAndyno/flac-sdcard-tools/actions/workflows/release.yml/badge.svg)](https://github.com/SulthanAndyno/flac-sdcard-tools/actions/workflows/release.yml)

Toolkit CLI berbasis Linux untuk mengotomatisasi pengelolaan koleksi musik **FLAC**, mulai dari pengunduhan *synced lyrics* (`.lrc`) via LRCLIB, perapihan struktur folder yang aman untuk filesystem **FAT32/exFAT**, pemantauan otomatis berbasis **Systemd User Watcher**, hingga sinkronisasi dan *safe unmount* **SD Card** menggunakan `lsblk`, `rsync`, dan `udisksctl`.

---

## Arsitektur & Peningkatan (v1 -> v2)

| Fitur | Versi Lama (`v1`) | Versi Baru (`v2.0 Linux Edition`) |
|---|---|---|
| **Antarmuka** | 2 script terpisah (`getlyrics`, `organize_music`) dengan path *hardcoded* | Unified CLI `flac-sdcard` berbasis **Typer + Rich** + konfigurasi fleksibel (`config.toml` / env vars) + tetap mendukung command lama |
| **Pencarian Lirik** | Hanya *exact match* `/api/get` | *Exact match* + otomatis *fallback* ke `/api/search` + embed ke Vorbis tag `LYRICS` di dalam file FLAC |
| **Metadata & Validasi** | Gagal jika tag `ARTIST`/`TITLE` kosong | Auto-fallback parser dari nama file (`Artis - Judul.flac`) + validasi stream audio menggunakan `flac -t` |
| **Sinkronisasi SD Card** | Ketik manual `lsblk`, `rsync`, `sync`, `udisksctl` | Subcommand `flac-sdcard sdcard` otomatis mendeteksi partisi removable (`lsblk --json`), mengabaikan `/boot/efi`, menjalankan `rsync` exFAT-safe, dan `sync` + `udisksctl unmount -b` |
| **Otomatisasi Linux** | Manual setiap ada lagu baru | **Systemd User Path Watcher** (`flac-sdcard-watcher.path`) + notifikasi desktop via `notify-send` |
| **CI/CD & Packaging** | Tidak ada | **GitHub Actions** (Ruff, Mypy, ShellCheck, Pytest + real FLAC generator, auto-release `.deb`, `PKGBUILD` Arch Linux, & Standalone Binary) |

---

## Instalasi di Linux

### 1. Menggunakan `uv` (Direkomendasikan untuk Development)
```bash
cd /workspace/Projects/flac-sdcard-tools
uv sync --all-extras --dev
uv run flac-sdcard --help
```

### 2. Instalasi Global User (`~/.local/bin`)
```bash
uv tool install --editable /workspace/Projects/flac-sdcard-tools
```

### 3. Arch Linux (`PKGBUILD`)
```bash
cd packaging/arch
makepkg -si
```

---

## Penggunaan CLI (`flac-sdcard`)

### 1. Cek Status Koleksi & Deteksi SD Card
```bash
flac-sdcard status
```
Menampilkan jumlah file `.flac` dan `.lrc` di folder `songs/`, `library/`, `done/`, serta daftar SD Card yang sedang terpasang.

### 2. Audit Dependency Linux & Kesehatan Tag/Stream FLAC
```bash
flac-sdcard doctor --verify-stream
```
Memeriksa keberadaan `flac`, `metaflac`, `rsync`, `lsblk`, `udisksctl`, `notify-send`, serta menguji apakah ada file FLAC yang kekurangan tag atau rusak.

### 3. Ambil Synced Lyrics (`.lrc` + Embed Tag)
```bash
flac-sdcard lyrics
```

### 4. Rapikan ke `library/Artis/Album/NN - Judul.flac`
```bash
flac-sdcard organize
# Atau simulasi tanpa menyalin file:
flac-sdcard organize --dry-run
```

### 5. Jalankan Pipeline Sekaligus (Lyrics + Organize + Desktop Notification)
```bash
flac-sdcard pipeline --notify
```

### 6. Sinkronisasi & Safe Unmount SD Card Otomatis
```bash
# Simulasi (dry-run) terlebih dahulu:
flac-sdcard sdcard --dry-run

# Sinkronisasi ke SD Card yang terdeteksi otomatis, lalu langsung safe unmount:
flac-sdcard sdcard --unmount
```

---

## Otomatisasi Background dengan Systemd User Watcher

Agar setiap kali kamu memindahkan file `.flac` baru ke `/workspace/Music/songs` sistem langsung mengunduh lirik, merapikan ke `library/`, dan memunculkan notifikasi desktop:

```bash
./scripts/install-systemd.sh
systemctl --user status flac-sdcard-watcher.path
```

---

## Konfigurasi Opsional (`~/.config/flac-sdcard-tools/config.toml`)

Secara bawaan tool ini membaca `/workspace/Music/{songs,library,done,no-lyrics,covers}`. Kamu bisa mengubahnya lewat `~/.config/flac-sdcard-tools/config.toml`:

```toml
songs_dir = "/workspace/Music/songs"
library_dir = "/workspace/Music/library"
done_dir = "/workspace/Music/done"
no_lyrics_dir = "/workspace/Music/no-lyrics"
covers_dir = "/workspace/Music/covers"
request_timeout = 10
embed_lyrics_tag = true
fallback_filename_parse = true
```

---

## Pipeline CI/CD (GitHub Actions)

1. **`.github/workflows/ci.yml`**:
   - **Linting & Static Analysis**: `ruff check`, `ruff format --check`, `mypy` (strict mode), dan `shellcheck` untuk seluruh script Bash.
   - **Automated Linux Testing**: Menjalankan `pytest` pada matriks Python 3.10–3.12 di Ubuntu runner. Test suite secara dinamis men-generate file audio `.flac` asli menggunakan binary `flac`, menguji sanitasi karakter ilegal exFAT (`<>:"/\|?*`), memverifikasi parser JSON `lsblk`, serta menjalankan simulasi E2E `rsync`.
2. **`.github/workflows/release.yml`**:
   - Saat *push tag* `v*` (misal `v2.0.0`), otomatis membangun paket **Debian/Ubuntu (`.deb`)**, **Python Wheel & Source Tarball**, **Standalone Linux Binary (`flac-sdcard-linux-x86_64`)**, serta menyertakan **`PKGBUILD` Arch Linux** dan `SHA256SUMS` ke halaman **GitHub Releases**.
