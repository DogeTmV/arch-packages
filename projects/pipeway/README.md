# pipeway

Composable, file-based feed pipelines. Describe a list of small stages in JSON
and run them over RSS/Atom input or plain item dictionaries.

## Inspiration

Inspired by **Yahoo Pipes**, the visual feed-mashing service that was shut down
in 2015. This is an **original reimplementation, no upstream code/assets** were
used — a spiritual successor with an independent design and a Python 3 standard
library implementation.

## Install

```sh
makepkg -si     # Arch package from this repository
./pipeway --help
```

Only Python 3 is required.

## Usage

```sh
pipeway example > mypipe.json      # print a working example config
pipeway validate mypipe.json       # precise errors for bad stages/keys
pipeway run mypipe.json            # write result to stdout
pipeway run mypipe.json --input items.json --output result.json
```

Configs are a JSON object with a `stages` list (a bare list also works). Stages
run in order:

| Stage | Keys | Effect |
| --- | --- | --- |
| `fetch` | `url` | Read RSS/Atom from a URL (`file://` allowed) into items |
| `match` | `field`, `pattern` | Keep items whose field matches a regex |
| `exclude` | `field`, `pattern` | Drop items whose field matches a regex |
| `dedupe` | `field` | Keep the first item per field value |
| `sort` | `field`, `order` (`asc`/`desc`) | Sort items by a field |
| `limit` | `count` | Keep the first N items |
| `format` | `type` (`rss`/`json`/`text`), `title` | Render the final output |

`--input` accepts a JSON list of item dicts (or `{"items": [...]}`). Fetching
is entirely optional and network failures degrade to a warning on stderr, so
pipelines can be built and tested completely offline with local fixture files.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

The suite covers every stage, validation failures, all three output formats and
a complete offline pipeline.

## License

MIT — see [LICENSE](LICENSE). Original reimplementation, no upstream
code/assets.
