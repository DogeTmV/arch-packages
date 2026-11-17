# bookmarkdeck

`bookmarkdeck` is a local bookmark manager. It imports classic Netscape
bookmark HTML (folders become tags), stores everything in one JSON file, and
can export valid Netscape bookmark HTML again.

## Inspiration

Inspired by **Netscape Navigator** bookmarks and **del.icio.us** tagging. This
is an **original reimplementation, no upstream code/assets** are used: it is a
fresh implementation of the familiar bookmark-file idea with the Python
standard library only.

## Install

Arch Linux:

```sh
sudo pacman -S bookmarkdeck
```

From source:

```sh
chmod +x bookmarkdeck
install -Dm755 bookmarkdeck ~/.local/bin/bookmarkdeck
```

## Usage

```sh
bookmarkdeck import ~/Downloads/bookmarks.html
bookmarkdeck add https://example.org --title "Example" --tags news,reference
bookmarkdeck list --tag Work
bookmarkdeck search example
bookmarkdeck tag b-1a2b3c4d5e6f work important
bookmarkdeck open b-1a2b3c4d5e6f --dry-run
bookmarkdeck export ./bookmarks-out.html
bookmarkdeck stats
```

`open --dry-run` prints `xdg-open <url>` instead of launching a browser.
Imported folders and `TAGS="a,b"` attributes both become tags; exporting
writes those tags back so an import/export round trip preserves them.

The store defaults to `~/.local/share/bookmarkdeck/bookmarks.json`; override it
with `--db PATH` before or after the subcommand.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

## Disclaimer

Not affiliated with Netscape, AOL, Yahoo, or del.icio.us. No upstream code,
logos, trademarks or assets are bundled. Licensed under the MIT License; see
`LICENSE`.
