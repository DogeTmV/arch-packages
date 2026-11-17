# toneshift

`toneshift` is a minimal speed/pitch music editor GUI. Open a track, move one
slider between 0.5x and 2.0x, and export the result. Internally ffmpeg's
`atempo` filter is chained as many times as needed, so the core also supports
speeds outside the single-filter range.

## Inspiration

Inspired by the **speed and pitch slider on a cassette deck / turntable**: one
control that makes a track slower or faster. This is an **original minimal
utility** written from scratch with Python 3, PySide6 and ffmpeg. No upstream
code, logos or assets are used.

## Install

Arch Linux:

```sh
sudo pacman -S toneshift
```

From source:

```sh
chmod +x toneshift
./toneshift --help
```

Requires `python`, `pyside6` and `ffmpeg` (ffmpeg supplies `ffmpeg` and
`ffplay`).

## Usage

```sh
toneshift             # start the GUI
toneshift --help      # short usage string
toneshift --version   # toneshift 0.1.0
```

In the window:

- **Open…** chooses an audio file.
- The **slider** selects the speed from 0.5x to 2.0x; the label shows the
  current value.
- **Export** writes a `.wav`, `.mp3` or `.ogg` file with the audio filter
  `atempo=<rate>`. Because a single `atempo` only accepts 0.5-2.0, larger
  ratios are split into a chain — for example 2.5 becomes
  `atempo=1.25,atempo=2` and 0.25 becomes `atempo=0.5,atempo=0.5`.
- **Play / Stop** previews the original file with `ffplay`.

`core.normalize_rate()` validates a rate and clamps it to 0.5-2.0 with clear
errors for invalid values; `core.atempo_factors()` performs the chain
decomposition. All external commands are argument lists built in `core.py`.

## Tests

```sh
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
```

The suite is fully offline: it checks exact ffmpeg arguments and uses the
offscreen Qt platform for the GUI smoke test.

## License

MIT — see [LICENSE](LICENSE). Not affiliated with any hardware maker;
**original minimal utility**, no upstream code/assets.
