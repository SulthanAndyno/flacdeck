"""Desktop notification helper for Linux (`notify-send`)."""

from __future__ import annotations

import shutil
import subprocess


def send_notification(title: str, message: str, urgency: str = "normal") -> bool:
    """Send a desktop notification via `notify-send` if available on the system."""
    notify_bin = shutil.which("notify-send")
    if not notify_bin:
        return False

    try:
        result = subprocess.run(
            [
                notify_bin,
                "--app-name=FlacDeck",
                f"--urgency={urgency}",
                "--icon=multimedia-player",
                title,
                message,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False
