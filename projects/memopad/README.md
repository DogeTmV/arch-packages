# memopad

A quick memo database for the terminal: categorized notes, deterministic IDs,
timestamps, case-insensitive search, and JSON/CSV/text import and export.

## Inspiration

Inspired by the **Palm Pilot Memo Pad** application. This is an
**original reimplementation, no upstream code/assets**: no Palm OS code,
ROMs, synchronization protocols, databases or trademarks are used. Notes are
kept in a plain JSON file created by this tool.

## Install

```sh
pacman -S memopad
```

Or run the Python 3 standard-library script directly:

```sh
./memopad --help
```

## Usage

State lives in `~/.local/share/memopad/memopad.json`. Pass `--db PATH` before
or after any subcommand to use a different file.

```sh
memopad add "Buy turtle food" --category Errands
memopad add "Call Ada about the demo" --category Work
memopad list
memopad list --category Work --limit 5
memopad show 1
memopad edit 1 "Buy turtle food and lettuce"
memopad category 1 Home
memopad categories
memopad search TURTLE
memopad stats
memopad export notes.json --format json
memopad export notes.csv --format csv
memopad export notes.txt --format txt
memopad import notes.json
```

IDs are assigned sequentially and are never reused after deletion. `import`
accepts this tool's own JSON and CSV exports (round-trippable, including
commas, quotes and newlines inside memo text).

## Tests

```sh
python3 -m unittest discover -s tests -v
```

The tests use a temporary `--db`, run offline and never touch the home
directory.

## Disclaimer

An original reimplementation, no upstream code/assets. Palm is a trademark of
its respective owner; this project is unaffiliated.

## License

MIT — see [LICENSE](LICENSE).
