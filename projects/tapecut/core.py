"""Pure logic for tapecut: ffprobe duration parsing and ffmpeg trim commands.

No Qt imports live here, so everything in this module is testable offline.
"""

import json
import math
import os
import shlex
import subprocess
import types

VERSION = "0.1.0"
APP = "tapecut"

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"
FFPLAY = "ffplay"

SUPPORTED_EXTS = ("wav", "mp3", "ogg", "m4a")

# Input/output codec families.  Stream copy is safe only inside one family.
_INPUT_FAMILY = {
    ".wav": "wav", ".wave": "wav",
    ".mp3": "mp3",
    ".ogg": "ogg", ".oga": "ogg",
    ".m4a": "mp4", ".mp4": "mp4", ".aac": "mp4",
}
_OUTPUT_FAMILY = {
    ".wav": "wav",
    ".mp3": "mp3",
    ".ogg": "ogg",
    ".m4a": "mp4",
}
_ENCODERS = {
    "wav": "pcm_s16le",
    "mp3": "libmp3lame",
    "ogg": "libvorbis",
    "mp4": "aac",
}


def _path(value, label):
    if value is None or str(value) == "":
        raise ValueError("%s must not be empty" % label)
    return os.fspath(value)


def _ext(path):
    return os.path.splitext(path)[1].lower()


def _number(value, label):
    if isinstance(value, bool):
        raise ValueError("%s must be a number, got %r" % (label, value))
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("%s must be a number, got %r" % (label, value)) from exc
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _fmt(value):
    return "%g" % value


def describe_command(argv):
    """Return a shell-quoted string for status messages (never executed)."""
    return " ".join(shlex.quote(str(part)) for part in argv)


def build_probe_command(path):
    """Build the ffprobe argv list used to read a file's duration."""
    return [FFPROBE, "-v", "error", "-show_entries", "format=duration",
            "-of", "json", _path(path, "path")]


def parse_duration_json(text):
    """Extract the duration in seconds from ffprobe's JSON output."""
    raw = None
    try:
        data = json.loads(text)
        raw = data["format"]["duration"]
        duration = float(raw)
    except (TypeError, ValueError, KeyError, AttributeError, IndexError) as exc:
        raise ValueError("cannot read duration from ffprobe JSON output") from exc
    if not math.isfinite(duration) or duration < 0:
        raise ValueError("invalid duration in ffprobe JSON output: %r" % (raw,))
    return duration


def _call_runner(runner, command):
    """Call an injected runner, tolerating simple fakes that take only argv."""
    try:
        result = runner(command, capture_output=True, text=True)
    except TypeError as exc:
        if "unexpected keyword argument" not in str(exc):
            raise
        result = runner(command)
    if isinstance(result, dict):
        result = types.SimpleNamespace(**result)
    return result


def probe_duration(path, runner=None):
    """Return the length of *path* in seconds, using ffprobe JSON output.

    ``runner`` is injectable for tests: it is called like ``subprocess.run``
    and must expose ``stdout``, ``stderr`` and ``returncode``.  All failures
    raise RuntimeError with a message naming the file and the cause.
    """
    path = _path(path, "path")
    command = build_probe_command(path)
    if runner is None:
        runner = subprocess.run
    try:
        result = _call_runner(runner, command)
    except OSError as exc:
        raise RuntimeError("cannot run ffprobe: %s" % exc) from exc
    if getattr(result, "returncode", 0) != 0:
        detail = str(getattr(result, "stderr", "") or "").strip()
        message = "ffprobe failed for %s" % path
        raise RuntimeError(message + (": " + detail if detail else ""))
    try:
        return parse_duration_json(getattr(result, "stdout", ""))
    except ValueError as exc:
        raise RuntimeError("cannot determine duration of %s: %s" % (path, exc)) from exc


def build_cut_command(input_path, start, duration, output_path, codec="copy"):
    """Build an ffmpeg argv list that trims *input_path* into *output_path*.

    ``start`` and ``duration`` are in seconds.  Output must be wav, mp3, ogg
    or m4a.  With the default ``codec='copy'`` a stream copy is used when the
    input and output share a codec family; otherwise a suitable encoder is
    selected.  An explicit codec name (or output extension) can also be given.
    """
    input_path = _path(input_path, "input path")
    output_path = _path(output_path, "output path")
    start_value = _number(start, "start")
    duration_value = _number(duration, "duration")
    if start_value < 0:
        raise ValueError("start must be >= 0, got %r" % (start,))
    if duration_value <= 0:
        raise ValueError("duration must be > 0, got %r" % (duration,))

    extension = _ext(output_path)
    if extension.lstrip(".") not in SUPPORTED_EXTS:
        raise ValueError(
            "unsupported output extension %r (supported: %s)"
            % (extension or "<none>", ", ".join(SUPPORTED_EXTS)))

    output_family = _OUTPUT_FAMILY[extension]
    input_family = _INPUT_FAMILY.get(_ext(input_path))
    encoder = None
    if codec is None or codec == "copy":
        if input_family != output_family:
            encoder = _ENCODERS[output_family]
    elif codec in SUPPORTED_EXTS or codec in _ENCODERS:
        encoder = _ENCODERS[codec.lstrip(".")] if codec in SUPPORTED_EXTS else _ENCODERS[codec]
    else:
        encoder = str(codec)

    command = [FFMPEG, "-y", "-ss", _fmt(start_value), "-i", input_path,
               "-t", _fmt(duration_value), "-vn"]
    if encoder is None:
        command += ["-c", "copy"]
    else:
        command += ["-c:a", encoder]
    command.append(output_path)
    return command


def build_play_command(path, player=FFPLAY):
    """Build a preview command for *path* (ffplay by default)."""
    parts = shlex.split(player) if isinstance(player, str) else list(player)
    if not parts:
        raise ValueError("player must not be empty")
    return parts + ["-nodisp", "-autoexit", "-loglevel", "error", _path(path, "path")]
