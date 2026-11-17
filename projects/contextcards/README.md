# contextcards

A local context dashboard. Define small rules and import local calendar,
weather or commute events from JSON; `show` renders a quiet, deterministic
digest for a chosen date. Nothing ever contacts the network.

## Inspiration

Inspired by **Google Now**, the context-aware assistant cards product that was
discontinued in 2018. This is an original reimplementation, no upstream code/assets
were used: an independent spiritual successor with its own name, rule format and
standard-library-only implementation.

## Install

```sh
# Arch Linux (from this repository's package)
makepkg -si

# Or run directly
./contextcards --help
```

Python 3 is the only dependency.

## Usage

```sh
contextcards rule trash --title "Bin day" --body "Put bins out" \
    --weekday THU --tag home
contextcards rule tax --title "Tax reminder" --body "File the forms" \
    --date 2026-04-03
contextcards list
```

Events come from a local JSON file (a list, or `{"events": [...]}`):

```json
[
  {"kind": "commute", "title": "Bridge closure", "body": "Allow 20 extra minutes",
   "date": "2026-04-02", "time": "08:00", "tag": "traffic"}
]
```

```sh
contextcards feed events.json
contextcards show                         # today's digest
contextcards show --date 2026-04-02
contextcards show --date 2026-04-02 --format html
contextcards rm trash
contextcards export backup.json
contextcards import backup.json
```

A rule matches when every condition it specifies is satisfied: an exact
`--date`, a matching `--weekday`, and a `--tag` that is also present on an
active event. Imported events whose date or weekday matches the digest day
become cards themselves. Cards are ordered by time, then title, then body, so
repeated renders are identical. Text output is a short plain digest; HTML
output escapes all user-provided text.

Every command accepts `--dir PATH` for the state directory. By default state
lives in `~/.local/share/contextcards/state.json`; `--version` prints the
version and invalid input exits non-zero with a message on stderr.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

The suite uses a fixed date and temporary directories, and checks rule
selection, deterministic ordering, HTML escaping and export/import.

## License

MIT — see [LICENSE](LICENSE). Original reimplementation, no upstream
code/assets.
