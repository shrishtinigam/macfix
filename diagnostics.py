"""OS interactions, isolated from rules. No repair commands are executed."""

import subprocess
import sys


class ClipboardError(RuntimeError):
    """Clipboard is unavailable or could not be read."""


def read_clipboard() -> str:
    if sys.platform != "darwin":
        raise ClipboardError("--clipboard requires macOS and pbpaste. Pass the error as quoted text instead.")
    try:
        result = subprocess.run(
            ["/usr/bin/pbpaste"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=True, timeout=5,
        )
    except FileNotFoundError as exc:
        raise ClipboardError("pbpaste was not found. Pass the error as quoted text instead.") from exc
    except subprocess.TimeoutExpired as exc:
        raise ClipboardError("Reading the clipboard timed out. Try again or pass quoted text.") from exc
    except (subprocess.CalledProcessError, OSError) as exc:
        raise ClipboardError("Could not read the clipboard. Pass the error as quoted text instead.") from exc
    if not result.stdout.strip():
        raise ClipboardError("The clipboard contains no text. Copy an error message first.")
    return result.stdout.strip()


class CaptureError(RuntimeError):
    """Screen capture or preview failed."""


def capture_screen(path):
    """Return False when the user cancels. Destination must be a new temp path."""
    from pathlib import Path
    if sys.platform != 'darwin':
        raise CaptureError('--capture requires macOS. Use --image with an existing screenshot.')
    try:
        result = subprocess.run(['/usr/sbin/screencapture', '-i', '-s', '-x', '-t', 'png', str(path)],
                                capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        raise CaptureError('Screen capture failed or timed out. Check Screen Recording permission for your terminal, or use --image.') from None
    if result.returncode != 0:
        raise CaptureError('Screen capture failed. Check Screen Recording permission for your terminal, or use --image.')
    return Path(path).is_file() and Path(path).stat().st_size > 0


def preview_capture(path):
    try:
        subprocess.run(['/usr/bin/open', '-a', 'Preview', str(path)],
                       capture_output=True, check=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        raise CaptureError('Could not open the screenshot preview. Nothing was sent. Use --image after reviewing a saved screenshot.') from None
