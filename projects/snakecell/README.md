# snakecell

A Snake game for the terminal with a completely headless, seeded and unit
testable game core. Play interactively with curses, or produce a deterministic
ASCII board and score for scripts and CI with `--demo`.

## Inspiration

Inspired by **Nokia Snake**, the little game bundled with classic Nokia
phones. This is an **original reimplementation, no upstream code/assets**: no
Nokia code, sprites, sounds, fonts or trademarks are included. The board is
drawn with plain ASCII characters.

## Install

```sh
pacman -S snakecell
```

The package installs `/usr/bin/snakecell` and its game logic module at
`/usr/lib/snakecell/snake_core.py`. The executable finds the module in the
installed layout, so `snakecell --demo` works from any directory, including
`/usr/bin`. From a source checkout, Python 3.9+ (standard library only) is
enough:

```sh
./snakecell --help
```

## Usage

```sh
# Reproducible non-interactive run (no TTY, no curses import)
snakecell --demo --seed 42 --steps 30
snakecell --demo --seed 42 --steps 30 --width 12 --height 10

# Interactive game: WASD or arrow keys, q or Esc to quit
snakecell --seed 7 --width 24 --height 18 --speed 90

snakecell --version
```

Board characters: `O` head, `o` body, `*` food, `.` empty, `#` wall. The
same seed always produces the same food placement and demo result.

## Library API

`snake_core.Grid(width, height, seed)` exposes `direction`, `snake`, `food`,
`score`, `steps` and `game_over`, plus `change_direction(name)`, `step()` and
`serialize_board()`. All game rules (turning, wall/self collision, food) live
there; the CLI is just a presentation layer.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

Tests cover turning, collisions, food consumption, seed determinism, the
headless CLI and the installed `/usr/bin` + `../lib` layout. They run offline
without a TTY.

## Disclaimer

An original reimplementation, no upstream code/assets. Nokia and Snake are
trademarks of their respective owners; this project is unaffiliated.

## License

MIT — see [LICENSE](LICENSE).
