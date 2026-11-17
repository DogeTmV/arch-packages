# fileforge

`fileforge` is a small, original minimal utility that converts files through a
compact PySide6 GUI. It handles plain-text style formats entirely in the
Python standard library and delegates image/audio conversions to `ffmpeg`.

Inspired by general-purpose format converters and the `ffmpeg` CLI, this is an
original minimal utility — it is not a fork or reimplementation of any other
project. (The wider family of tools is inspired by the yt-dlp CLI and simple
video trimmers, but this utility is deliberately standalone.)

## Features

- Text conversions: txt → md, md → html, html → txt, txt → json/csv,
  json/csv → txt and csv ↔ json, all with clear, user-facing errors.
- Image conversions between png/jpg/jpeg/webp/gif using ffmpeg with an
  even-dimension scale filter.
- Audio conversions between wav/mp3/ogg/m4a using per-format codecs.
- GUI with five controls: Open, a read-only path label, a target-format
  combo, Convert and a status label.

All external commands are built as argument lists in `core.py`; the GUI never
uses a shell.

## Usage

```
fileforge            # launch the GUI
fileforge --help     # print a short usage string
fileforge --version  # print "fileforge 0.1.0"
```

Run the tests from the project directory:

```
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
```

## License

MIT — see [LICENSE](LICENSE).
