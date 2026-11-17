"""Dependency-free logic for cutframe.

Video probing, ffmpeg/ffplay argument builders and validation all live here so
they can be tested without Qt or a display.
"""

import json
import math
import os
import subprocess

VERSION = "0.1.0"
OUTPUT_EXTS = {".mp4", ".mkv", ".mov"}


class MediaError(ValueError):
    """A user-facing media error (never a traceback)."""


def _number(value):
    """Format a number compactly for ffmpeg (``0``, ``1.5``, ...)."""
    number = float(value)
    return str(int(number)) if number.is_integer() else "%g" % number


def build_probe_command(path):
    """Return the ffprobe argv list used to inspect *path*."""
    return ["ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height:format=duration",
            "-of", "json", str(path)]


def parse_probe_output(raw):
    """Parse ffprobe JSON into ``(width, height, duration)``."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    try:
        data = json.loads(raw or "{}")
    except ValueError as exc:
        raise MediaError("ffprobe returned invalid JSON") from exc
    streams = data.get("streams") or []
    if not streams:
        raise MediaError("no video stream found")
    stream = streams[0]
    try:
        width = int(stream["width"])
        height = int(stream["height"])
    except (KeyError, TypeError, ValueError) as exc:
        raise MediaError("ffprobe did not report video dimensions") from exc
    try:
        duration = float((data.get("format") or {}).get("duration", 0.0))
    except (TypeError, ValueError):
        duration = 0.0
    return width, height, duration


def probe_video(path, runner=None):
    """Probe *path* with ffprobe via an injectable runner."""
    command = build_probe_command(path)
    run = runner or subprocess.run
    try:
        result = run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                     text=True, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise MediaError("ffprobe failed: %s" % exc) from exc
    return parse_probe_output(result.stdout)


def _validated_crop(crop):
    if not isinstance(crop, dict):
        raise MediaError("crop must be a dict with x, y, w and h")
    values = {}
    for key in ("x", "y", "w", "h"):
        if key not in crop:
            raise MediaError("crop is missing %r" % key)
        value = crop[key]
        if isinstance(value, bool) or not isinstance(value, int):
            raise MediaError("crop %s must be an integer" % key)
        if value < 0:
            raise MediaError("crop %s must be >= 0" % key)
        values[key] = value
    if values["w"] == 0 or values["h"] == 0:
        raise MediaError("crop w and h must be > 0")
    return values


def build_command(input_path, start, duration, crop, output_path):
    """Build an ffmpeg argv list for a cut and optional crop."""
    try:
        start, duration = float(start), float(duration)
    except (TypeError, ValueError) as exc:
        raise MediaError("start and length must be numbers") from exc
    if not (math.isfinite(start) and math.isfinite(duration)):
        raise MediaError("start and length must be finite numbers")
    if start < 0:
        raise MediaError("start must be >= 0")
    if duration <= 0:
        raise MediaError("length must be > 0")
    extension = os.path.splitext(str(output_path))[1].lower()
    if extension not in OUTPUT_EXTS:
        raise MediaError("output must end in .mp4, .mkv or .mov")

    command = ["ffmpeg", "-y", "-ss", _number(start), "-t", _number(duration),
               "-i", str(input_path)]
    if crop is not None:
        box = _validated_crop(crop)
        command += ["-vf", "crop=%d:%d:%d:%d"
                    % (box["w"], box["h"], box["x"], box["y"])]
    command += ["-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart",
                str(output_path)]
    return command


def build_preview_command(path, start):
    """Build an ffplay argv list for previewing *path* at *start* seconds."""
    try:
        start = float(start)
    except (TypeError, ValueError) as exc:
        raise MediaError("start must be a number") from exc
    if not math.isfinite(start) or start < 0:
        raise MediaError("start must be a finite number >= 0")
    return ["ffplay", "-ss", _number(start), "-i", str(path)]
