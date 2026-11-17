"""Pure logic for toneshift: rate validation and ffmpeg speed commands."""

import math
import os
import shlex

VERSION = "0.1.0"
APP = "toneshift"

FFMPEG = "ffmpeg"
FFPLAY = "ffplay"

ATEMPO_MIN = 0.5
ATEMPO_MAX = 2.0
_EPS = 1e-12

SUPPORTED_EXTS = ("wav", "mp3", "ogg")
_ENCODERS = {
    ".wav": "pcm_s16le",
    ".mp3": "libmp3lame",
    ".ogg": "libvorbis",
}


def _path(value, label):
    if value is None or str(value) == "":
        raise ValueError("%s must not be empty" % label)
    return os.fspath(value)


def _checked_rate(rate):
    if isinstance(rate, bool):
        raise ValueError("rate must be a positive number, got %r" % (rate,))
    try:
        value = float(rate)
    except (TypeError, ValueError) as exc:
        raise ValueError("rate must be a positive number, got %r" % (rate,)) from exc
    if not math.isfinite(value):
        raise ValueError("rate must be a finite number, got %r" % (rate,))
    if value <= 0:
        raise ValueError("rate must be greater than 0, got %r" % (rate,))
    return value


def _fmt(value):
    return "%g" % value


def normalize_rate(rate):
    """Validate *rate* and clamp it to atempo's 0.5-2.0 single-filter range.

    Rates outside the range are valid input (they are split into several
    atempo filters by :func:`atempo_factors`); this returns the clamped value
    used by the GUI slider.  Invalid rates raise ValueError with a clear
    message.
    """
    value = _checked_rate(rate)
    return min(ATEMPO_MAX, max(ATEMPO_MIN, value))


def atempo_factors(rate):
    """Split *rate* into factors that each lie in [0.5, 2.0].

    ``atempo`` accepts only 0.5-2.0, so e.g. 2.5 becomes ``1.25 * 2.0`` and
    0.25 becomes ``0.5 * 0.5``.  The original value (after each split) is
    placed first, matching the way the multiplication is usually written.
    """
    value = _checked_rate(rate)
    if ATEMPO_MIN - _EPS <= value <= ATEMPO_MAX + _EPS:
        return [value]

    factors = []
    if value > ATEMPO_MAX + _EPS:
        while value > ATEMPO_MAX + _EPS:
            value /= ATEMPO_MAX
            factors.append(ATEMPO_MAX)
    else:
        while value < ATEMPO_MIN - _EPS:
            value /= ATEMPO_MIN
            factors.append(ATEMPO_MIN)
    factors.insert(0, min(ATEMPO_MAX, max(ATEMPO_MIN, value)))
    return factors


def build_filter_chain(rate):
    """Return e.g. ``atempo=1.25,atempo=2`` for the requested speed."""
    return ",".join("atempo=" + _fmt(factor) for factor in atempo_factors(rate))


def describe_command(argv):
    """Return a shell-quoted string for status messages (never executed)."""
    return " ".join(shlex.quote(str(part)) for part in argv)


def build_speed_command(input_path, rate, output_path):
    """Build an ffmpeg argv list that changes the speed of *input_path*.

    Only wav, mp3 and ogg output is supported.  The audio filter chain uses
    one or more ``atempo`` filters so any positive rate can be expressed.
    """
    input_path = _path(input_path, "input path")
    output_path = _path(output_path, "output path")
    _checked_rate(rate)
    extension = os.path.splitext(output_path)[1].lower()
    if extension not in _ENCODERS:
        raise ValueError(
            "unsupported output extension %r (supported: %s)"
            % (extension or "<none>", ", ".join(SUPPORTED_EXTS)))

    return [
        FFMPEG, "-y", "-i", input_path,
        "-filter:a", build_filter_chain(rate),
        "-vn", "-c:a", _ENCODERS[extension],
        output_path,
    ]


def build_play_command(path, player=FFPLAY):
    """Build a preview command for *path* (ffplay by default)."""
    parts = shlex.split(player) if isinstance(player, str) else list(player)
    if not parts:
        raise ValueError("player must not be empty")
    return parts + ["-nodisp", "-autoexit", "-loglevel", "error", _path(path, "path")]
