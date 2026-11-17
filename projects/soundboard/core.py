"""Pure logic for soundboard: player selection and play commands."""

import os
import shlex

VERSION = "0.1.0"
APP = "soundboard"

SLOT_COUNT = 8
DEFAULT_PLAYER = "ffplay"
PLAYER_ENV = "SOUNDBOARD_PLAYER"
FFPLAY_ARGS = ("-nodisp", "-autoexit", "-loglevel", "error")


def _path(value):
    if value is None or str(value) == "":
        raise ValueError("path must not be empty")
    return os.fspath(value)


def _parts(player):
    if isinstance(player, (list, tuple)):
        parts = [str(part) for part in player]
    else:
        parts = shlex.split(str(player))
    if not parts or not parts[0].strip():
        raise ValueError("player must not be empty")
    return parts


def resolve_player(cli_player=None, environ=None):
    """Pick the player from --player, SOUNDBOARD_PLAYER, or the ffplay default."""
    if environ is None:
        environ = os.environ
    if cli_player and str(cli_player).strip():
        return str(cli_player)
    from_env = environ.get(PLAYER_ENV, "")
    if from_env and str(from_env).strip():
        return from_env
    return DEFAULT_PLAYER


def build_play_command(player, path=None):
    """Build the argv list that plays *path*.

    ``player`` may be a command string (quoting is respected), an argv list,
    or ``None`` to use the default ffplay player.  For convenience, calling
    ``build_play_command(path)`` with a single argument also uses ffplay.
    The file must exist; missing files raise FileNotFoundError.
    """
    if path is None:
        path, player = player, DEFAULT_PLAYER
    if player is None:
        player = DEFAULT_PLAYER
    path = _path(path)
    if not os.path.isfile(path):
        raise FileNotFoundError("sound file not found: %s" % path)
    parts = _parts(player)
    if os.path.basename(parts[0]).lower() in ("ffplay", "ffplay.exe"):
        parts += list(FFPLAY_ARGS)
    return parts + [path]


def describe_command(argv):
    """Return a shell-quoted string for status messages (never executed)."""
    return " ".join(shlex.quote(str(part)) for part in argv)
