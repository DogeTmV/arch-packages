# soundboard

`soundboard` is a minimal click-to-play soundboard: eight large numbered
slots. Right-click a slot to assign an audio file, left-click to play it, and
press Stop to cut the current sound short.

## Inspiration

Inspired by **hardware soundboards and button boxes** used by radio hosts and
live performers: one big button per sound. This is an **original minimal
utility** written from scratch with Python 3, PySide6 and ffmpeg's `ffplay`.
No upstream code, logos or assets are used.

## Install

Arch Linux:

```sh
sudo pacman -S soundboard
```

From source:

```sh
chmod +x soundboard
./soundboard --help
```

Requires `python`, `pyside6` and `ffmpeg` (ffmpeg supplies `ffplay` by
default).

## Usage

```sh
soundboard                       # start the GUI with ffplay
soundboard --player mpv          # use a different player
soundboard --help
soundboard --version             # soundboard 0.1.0
```

Set `SOUNDBOARD_PLAYER` to choose a default player without a flag; `--player`
takes precedence. A player command with spaces is split with shell-style
quoting rules (for example `--player 'mpv --no-config'`). Custom players
receive just the file path; `ffplay` additionally gets
`-nodisp -autoexit -loglevel error`.

- **Right-click** a numbered slot to assign an audio file.
- **Left-click** a slot to play it; click another slot to switch sounds.
- **Stop** kills the current playback process.

`core.SLOT_COUNT = 8`, and `core.build_play_command(player, path)` validates
that the file exists and returns an argument list (never a shell string).

## Tests

```sh
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
```

The suite is fully offline: it never launches a real player and uses the
offscreen Qt platform for the GUI smoke test.

## License

MIT — see [LICENSE](LICENSE). Not affiliated with any hardware maker;
**original minimal utility**, no upstream code/assets.
