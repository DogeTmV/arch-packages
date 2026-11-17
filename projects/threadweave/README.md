# threadweave

`threadweave` imports an mbox mail archive and lets you browse it as threaded
conversations from the terminal. Messages and threads are normalized into a
single JSON store; no mail server or network connection is needed.

## Inspiration

Inspired by the discontinued **Google Wave** collaboration service and its
conversation threads. This is an **original reimplementation, no upstream
code/assets**: it is a local mbox reader written from scratch and shares no
code, assets or wire format with that product.

## Install

Arch Linux: build the sibling `packages/threadweave/PKGBUILD`, which installs
`/usr/bin/threadweave`.

From source: put `threadweave` on your `PATH` and make it executable. Python
3.8+ is required; the mbox and email parsers come from the standard library.

## Usage

```sh
threadweave import archive.mbox                    # writes ~/.local/share/threadweave/store.json
threadweave import archive.mbox --db ./store.json  # or choose a path
threadweave list --limit 10
threadweave show <thread-id>
threadweave show <thread-id> --format html
threadweave search "meeting notes"
threadweave export ./thread-pages
threadweave stats
```

Threads are formed by following `In-Reply-To`/`References` links when present
and otherwise by normalized subject (leading `Re:`, `Fwd:` and similar prefixes
are ignored). Malformed headers are tolerated. HTML output escapes message
text. Re-importing replaces the store rather than duplicating messages.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

Tests use the small mbox fixture in `tests/fixtures/` and never touch the
network or the real home directory store.

## Disclaimer

Original reimplementation, no upstream code/assets. Not affiliated with or
endorsed by Google.
