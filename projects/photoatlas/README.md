# photoatlas

A read-only photo indexer and static gallery generator. It catalogues local
files, detects true duplicates, keeps tags in a JSON index and writes a
self-contained HTML gallery.

## Inspiration

Inspired by **Picasa**, the photo organiser discontinued in 2016. This is an
**original reimplementation, no upstream code/assets** were used — an
independent spiritual successor written with the Python 3 standard library.

## Install

```sh
makepkg -si
./photoatlas --help
```

Python 3 is the only dependency.

## Usage

```sh
photoatlas index ~/Pictures                 # build/refresh the index
photoatlas list                             # list indexed files
photoatlas duplicates                       # group identical files
photoatlas tag ~/Pictures/beach.jpg travel  # add a tag
photoatlas find travel                      # find files with a tag
photoatlas stats
photoatlas gallery ~/Public/gallery --title "My Album"
```

`--db PATH` selects a different index file (also accepted before the
subcommand); otherwise state is stored in
`~/.local/share/photoatlas/index.json`. The source photos are **never
modified** — indexing only reads them, and the gallery contains relative links
plus inline CSS with no external assets.

Each entry records path, size, mtime, a 64 KiB partial hash and the full
SHA-256. Duplicate detection is two-phase: files are grouped by the fast
partial hash, then confirmed by comparing full hashes, so large files sharing
only a prefix are not falsely reported as duplicates. JPEG SOF markers are
parsed directly for dimensions; other formats are still indexed with unknown
dimensions.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

The offline suite builds temporary fake images, checks two-phase duplicate
detection, tag lookup, stats and the generated gallery HTML.

## License

MIT — see [LICENSE](LICENSE). Original reimplementation, no upstream
code/assets.
