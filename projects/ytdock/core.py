"""Dependency-free logic for ytdock.

Builds yt-dlp argument lists, validates inputs and provides an injectable
download runner so no test ever needs the network.
"""

import os
import re
import subprocess

VERSION = "0.1.0"

# mode -> yt-dlp format selector
MODES = {
    "best": "bestvideo+bestaudio/best",
    "video": "best[ext=mp4]/best",
    "audio": "bestaudio/best",
    "small": "worstvideo+bestaudio/worst",
}

_DEFAULT_TEMPLATE = "%(title)s.%(ext)s"
_PROGRESS_RE = re.compile(r"\b(\d{1,3}(?:\.\d+)?)\s*%")


class DownloadError(ValueError):
    """A user-facing validation error."""


def validate(url, mode):
    """Validate the URL scheme and mode name, raising DownloadError."""
    if not isinstance(url, str) or not url.lower().startswith(("http://", "https://")):
        raise DownloadError("URL must start with http:// or https://")
    if mode not in MODES:
        raise DownloadError("unknown mode: %s (choose from %s)"
                            % (mode, ", ".join(MODES)))


def build_command(url, mode, outdir, template=_DEFAULT_TEMPLATE):
    """Return a yt-dlp argv list for *url* in *mode*."""
    validate(url, mode)
    command = ["yt-dlp", "-f", MODES[mode]]
    if mode == "audio":
        command += ["-x", "--audio-format", "mp3"]
    command += ["-o", os.path.join(str(outdir), template), url]
    return command


def run_download(runner, command):
    """Run *command* via an injectable callable (e.g. ``subprocess.run``).

    Keyword arguments request merged, text output so callers can display the
    log. Tests pass a stub runner or a fake yt-dlp script in a temp directory.
    """
    return runner(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                  text=True, check=False)


def parse_progress(line):
    """Return the percentage from a yt-dlp output line, or None."""
    match = _PROGRESS_RE.search(line or "")
    return float(match.group(1)) if match else None
