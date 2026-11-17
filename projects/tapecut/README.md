# tapecut

`tapecut` is a minimal audio trimmer GUI: pick a file, set a start time and a
length, then export the clip. It is a one-button tape deck in spirit — a small
window with only the controls you actually need.

## Inspiration

Inspired by the **one-button tape deck** of classic portable cassette
players: press once, record a passage, stop. This is an **original minimal
utility** written from scratch with Python 3, PySide6 and ffmpeg. No upstream
code, logos or assets are used.

## Install

Arch Linux:

```sh
sudo pacman -S tapecut
```

From source:

```sh
chmod +x tapecut
./tapecut --help
```

Requires `python`, `pyside6` and `ffmpeg` (ffmpeg supplies `ffmpeg`, `ffprobe`
and `ffplay`).

## Usage

```sh
tapecut              # start the GUI
tapecut --help       # short usage string
tapecut --version    # tapecut 0.1.0
```

In the window:

- **Open…** chooses an audio file; its duration is read with `ffprobe`.
- **Start** and **Length** are seconds (spinboxes).
- **Export** writes a `.wav`, `.mp3`, `.ogg` or `.m4a` clip. When input and
  output share a codec family the audio is stream-copied; otherwise an
  appropriate encoder is chosen automatically.
- **Play / Stop** previews the file with `ffplay` (click again to stop).

The status label reports the duration, export progress and errors. All
external commands are built as argument lists in `core.py`; no shell strings
are used.

## Tests

```sh
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
```

The suite is fully offline: it uses a fake ffprobe runner for duration parsing
and an offscreen Qt platform for the GUI smoke test.

## License

MIT — see [LICENSE](LICENSE). Not affiliated with any cassette player maker;
**original minimal utility**, no upstream code/assets.

## Appearance

The interface uses a shared dark theme with drawn vector icons (no external
icon theme required). A matching branded icon is installed for desktop menus.
