# jsonpolish

A one-window JSON formatter: paste JSON, pretty-print it, minify it, copy the
result or clear the editor.

## Inspiration

Inspired by simple one-purpose desktop tools: a single small window that does
one job and never talks to the network. This is an **original minimal utility**
written from scratch in Python 3 with PySide6; it reuses no upstream code,
icons, formats or trademarks.

## Usage

Launch `jsonpolish`, paste JSON into the large editor and press **Format**
(2-space indent) or **Minify** (no optional whitespace). **Copy** puts the
current text on the clipboard, and **Clear** empties the editor. The status
line reports validity or the JSON parse error. Unicode is preserved as typed.

Command line options work without a display:

```sh
jsonpolish --help
jsonpolish --version
```

## Install

```sh
pacman -S jsonpolish
```

Or run `./jsonpolish` from this directory (requires Python 3 and PySide6).

## Tests

```sh
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
```

Tests use no files or network access.

## License

MIT — see [LICENSE](LICENSE).
