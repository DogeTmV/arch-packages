# rssledger

A local-first RSS/Atom reader that keeps your subscriptions, articles and read
state in a single JSON file you control.

## Inspiration

Inspired by **Google Reader**, the feed aggregator that was discontinued in
2013. This is an **original reimplementation, no upstream code/assets** were
used; it is an independent spiritual successor with its own name, design and
implementation built only on the Python 3 standard library.

## Install

```sh
# Arch Linux (from this repository's package)
makepkg -si

# Or just run it directly
./rssledger --help
```

Python 3 is the only dependency.

## Usage

```sh
# Subscribe and read feeds (file:// works fully offline)
rssledger add file:///path/to/feed.xml
rssledger add https://example.org/feed.rss
rssledger fetch                       # refresh every subscription
rssledger fetch ABC123                # refresh one feed

# Browse and mark articles
rssledger list                        # subscriptions with item counts
rssledger unread                      # list unread articles
rssledger read ITEMID                 # mark one as read
rssledger unread ITEMID               # mark it unread again
rssledger search "python"             # search titles/descriptions/links
rssledger stats

# Move subscriptions between installations
rssledger export-opml subs.opml
rssledger import-opml subs.opml
```

Global options: `--db PATH` selects a different state file; the
`RSSLEDGER_DB` environment variable is used when `--db` is absent. By default
state lives in `~/.local/share/rssledger/state.json`. `add` and `fetch` accept
`file://` URLs, and HTTP(S) fetches use `ETag`/`Last-Modified` plus a content
hash so unchanged feeds are skipped. Unreachable or malformed feeds produce a
warning on stderr and never abort the command.

Item IDs are stable SHA-1 abbreviations derived from the feed URL plus each
item's link (or title), so re-fetching never duplicates articles.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

The suite is entirely offline and includes RSS 2.0, Atom, malformed-feed,
OPML round-trip and ID-stability fixtures under `tests/fixtures/`.

## License

MIT — see [LICENSE](LICENSE). Original reimplementation, no upstream
code/assets.
