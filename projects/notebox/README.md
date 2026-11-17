# notebox

`notebox` is a local notebook CLI: quick notes with titles, tags, timestamps,
search, and one-file-per-note Markdown or self-contained HTML exports.

## Inspiration

Inspired by the discontinued **Google Notebook** service. This is an
**original reimplementation, no upstream code/assets** are included; it is a
new standard-library-only tool and contains no Google code, design, or assets.

## Install

Arch Linux:

```sh
sudo pacman -S notebox
```

From source:

```sh
chmod +x notebox
install -Dm755 notebox ~/.local/bin/notebox
```

## Usage

```sh
notebox add "remember" "the milk" --title "Errands" --tags home,errands
notebox add "draft body" --title "Idea"
notebox list --tag errands
notebox list --limit 10
notebox show n-0001
notebox edit n-0001 "updated" "body"
notebox tag n-0001 important later
notebox search milk
notebox import ./old-notes/
notebox export ./notes-export --format md
notebox export ./notes-html --format html
notebox stats
notebox rm n-0001
```

Import accepts a single `.md`, `.markdown` or `.txt` file, or a directory of
them. Markdown headings (`# Title`) and `Tags: a, b` lines are recognized.
Exports create one safely-named file per note plus an index.

The store defaults to `~/.local/share/notebox/notes.json`; use `--db PATH`
before or after the subcommand to change it.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

## Disclaimer

Not affiliated with Google. No upstream code, logos, trademarks or assets are
bundled. Licensed under the MIT License; see `LICENSE`.
