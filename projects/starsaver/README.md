# starsaver

`starsaver` is a small deterministic terminal screensaver with three ASCII
modes: a drifting starfield, digital rain and growing pipes. Frames can be
rendered to stdout for tests and pipelines, or animated in a terminal with
optional ANSI colour and screen clearing.

## Inspiration

Inspired by classic X11/Windows screensavers such as starfield, digital rain
and pipes. This is an **original reimplementation, no upstream code/assets**:
the frame algorithms and glyphs here were written from scratch and nothing was
taken from those programs.

## Install

Arch Linux: build the sibling `packages/starsaver/PKGBUILD`, which installs
`/usr/bin/starsaver`.

From source: put `starsaver` on your `PATH` and make it executable. Python
3.8+ is required; there are no third-party dependencies.

## Usage

```sh
starsaver modes
starsaver run stars --duration 20 --fps 15 --seed 7
starsaver run rain --no-ansi --seed 3
starsaver render pipes --frames 5 --seed 123 --width 60 --height 20
```

`render` prints each frame as a rectangle of ASCII characters; frames are
separated by one blank line. Given the same mode, seed, size and frame count it
always produces identical output. `run` emits ANSI escapes by default;
`--no-ansi` produces plain text instead. Defaults are 80 columns by 24 rows,
seed 0, 5 seconds and 12 frames per second.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

## Disclaimer

Original reimplementation, no upstream code/assets. No affiliation with the
authors or owners of the classic screensavers.
