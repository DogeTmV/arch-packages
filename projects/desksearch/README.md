# desksearch

`desksearch` is a local full-text indexer for plain-text files. It builds a
JSON index of token positions and returns ranked results with highlighted
snippets. No daemon, no network, no third-party dependencies.

## Inspiration

Inspired by **Google Desktop Search** and **Beagle**, the discontinued desktop
search tools. This is an **original reimplementation, no upstream code/assets**
are used: a new, independent indexer written with the Python standard library.

## Install

Arch Linux:

```sh
sudo pacman -S desksearch
```

From source:

```sh
chmod +x desksearch
install -Dm755 desksearch ~/.local/bin/desksearch
```

## Usage

```sh
desksearch index ~/notes ~/projects --ext .txt,.md,.py
desksearch index ~/notes --max-bytes 1048576
desksearch search "meeting notes" --limit 10
desksearch search todo --path ~/notes
desksearch status
desksearch ignore '*.log'
desksearch list-ignores
desksearch clear
```

The index defaults to `~/.local/share/desksearch/index.json`; pass `--db PATH`
before or after the subcommand to use another file. `--db` on `index` works in
the same position.

Search terms are matched with AND logic (case-insensitively). Results are
ranked deterministically by term frequency and file recency, with matching
words wrapped in `<mark>...</mark>` inside each snippet. Binary files, empty
files, files over `--max-bytes`, and files matching ignore globs are skipped.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

## Disclaimer

Not affiliated with Google or the Beagle project. No upstream code, logos,
trademarks or assets are bundled. Licensed under the MIT License; see `LICENSE`.
