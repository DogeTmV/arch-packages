# cutframe

`cutframe` is a small, original minimal utility for cutting a segment out of a
video and optionally cropping it, through a compact PySide6 GUI. It probes the
source with `ffprobe`, exports with `ffmpeg` via `QProcess`, and reports status
in a single label.

Inspired by simple video trimmers (and, more generally, format converters and
the yt-dlp CLI), this is an original minimal utility — it is not a fork or
reimplementation of any other editor.

## Features

- Open a video; dimensions and duration are read from ffprobe JSON.
- Cut toggles a small Start/Length panel; Crop toggles an X/Y/W/H panel.
- Export builds an ffmpeg command using `-ss`/`-t` before `-i`, an optional
  `crop=w:h:x:y` video filter, then libx264/aac and `+faststart`.
- Output must be `.mp4`, `.mkv` or `.mov`; all arguments are built in `core.py`.
- Five visible controls: Open, Cut, Crop, Export and the status label.

## Usage

```
cutframe            # launch the GUI
cutframe --help     # print a short usage string
cutframe --version  # print "cutframe 0.1.0"
```

Run the tests from the project directory:

```
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
```

## License

MIT — see [LICENSE](LICENSE).
