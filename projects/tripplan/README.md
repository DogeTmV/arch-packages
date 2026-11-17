# tripplan

An offline itinerary planner. Trips are plain JSON files, items are sorted by
date and time, and exports are available as Markdown, JSON or RFC 5545-style
ICS with stable UIDs and CRLF line endings.

## Inspiration

Inspired by **Google Trips**, the travel planning app that was discontinued in
2019. This is an **original reimplementation, no upstream code/assets** were
used: an independent spiritual successor with its own name, file format and
standard-library-only implementation.

## Install

```sh
# Arch Linux (from this repository's package)
makepkg -si

# Or run directly
./tripplan --help
```

Python 3 is the only dependency; no network access is ever required.

## Usage

```sh
tripplan new Kyoto --start 2026-04-01 --end 2026-04-05
tripplan add Kyoto "Fushimi Inari" --date 2026-04-02 --time 08:30 \
    --location "Fushimi" --type sight --notes "go early"
tripplan list
tripplan show Kyoto
tripplan show Kyoto --date 2026-04-02
tripplan rm Kyoto 1
tripplan export Kyoto trip.md --format md
tripplan export Kyoto trip.ics --format ics
tripplan export Kyoto trip.json --format json
tripplan import Copy trip.json
tripplan stats
```

Every command accepts `--dir PATH` to select a different trips directory. By
default trips live in `~/.local/share/tripplan/trips/`; `--version` prints the
version and invalid input exits non-zero with a message on stderr.

ICS exports include one `VEVENT` per dated item, a fixed `DTSTAMP` for
reproducibility, UID values derived from the trip name and item ID, escaped
text and 75-octet line folding. Timed items default to a one-hour duration;
date-only items are all-day events.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

The suite uses temporary directories and fixed dates, and checks CRLF,
escaping, folding, UID stability and the JSON round trip.

## License

MIT — see [LICENSE](LICENSE). Original reimplementation, no upstream
code/assets.
