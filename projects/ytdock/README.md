# ytdock

`ytdock` is a small, original minimal utility that wraps the yt-dlp CLI in a
compact PySide6 GUI: enter a URL, pick a mode, choose an output folder and
download while watching a merged stdout/stderr log. Cancel terminates the
running process.

Inspired by the yt-dlp CLI (and, more generally, simple video trimmers and
format converters), this is an original minimal utility — it is not a fork or
reimplementation of yt-dlp or any other project.

## Features

- Modes: `best` (bestvideo+bestaudio/best), `video`, `audio` (extracts MP3 with
  `-x --audio-format mp3`) and `small` (worstvideo+bestaudio/worst).
- All download commands are built as argument lists in `core.py`; the GUI uses
  `QProcess` with merged channels and never shells out.
- `run_download` accepts an injectable runner, so tests use a fake yt-dlp
  script in a temporary directory and never touch the network.
- Controls: URL line edit, mode combo, Choose Folder, Download, Cancel and a
  read-only log pane.

## Usage

```
ytdock            # launch the GUI
ytdock --help     # print a short usage string
ytdock --version  # print "ytdock 0.1.0"
```

Run the tests from the project directory:

```
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
```

## License

MIT — see [LICENSE](LICENSE).
