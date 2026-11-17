# minamp

A compact, playlist-driven audio front-end. It keeps an ordered playlist with
stable IDs, builds player commands without launching anything by default, and
stores everything in a JSON state file.

## Inspiration

Inspired by **Winamp**, the classic media player discontinued in the 2010s.
This is an **original reimplementation, no upstream code/assets** were used —
an independent spiritual successor with its own name and a Python 3 standard
library implementation (no skins, no proprietary formats, no upstream code).

## Install

```sh
makepkg -si
./minamp --help
```

Python 3 is the only dependency; playback itself requires a player such as
`mpv` only when you run without `--dry-run`.

## Usage

```sh
minamp add ~/Music/album --recursive    # add audio files (by extension)
minamp list                             # show ids, titles and paths
minamp rm 3                             # remove a track by id
minamp clear
minamp repeat all                       # off | all | one
minamp shuffle                          # toggle shuffle
minamp play 2 --dry-run                 # print the command, never launch audio
minamp play --player 'mpv --no-config'  # override the player template
minamp now
minamp config --player 'mpv --no-video'
minamp export playlist.m3u
minamp import playlist.m3u
```

Global `--db PATH` selects another state file (also accepted after the
subcommand); otherwise state lives in `~/.local/share/minamp/state.json`.
`--dry-run` prints a quoted `DRY-RUN:` command so tests and scripts never
start a player. Repeat mode controls the built queue: `off` plays from the
chosen track to the end, `all` wraps around, and `one` plays only that track;
shuffle uses a seeded permutation for reproducible dry-runs. The default
player template is `mpv`; a `{file}` placeholder in a custom template produces
one command per queued file. M3U import/export round-trips `#EXTM3U` and
`#EXTINF` metadata.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

The offline suite uses fake audio files and dry-runs only — it never launches
a media player or accesses the network.

## License

MIT — see [LICENSE](LICENSE). Original reimplementation, no upstream
code/assets.
