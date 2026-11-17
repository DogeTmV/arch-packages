# hashcheck

A tiny desktop window for computing a file's MD5, SHA-1, SHA-256 or SHA-512
digest and checking it against an expected value.

## Inspiration

Inspired by simple one-purpose desktop tools: one small window, one obvious job,
no account, no network and no configuration file. This is an **original minimal
utility** written from scratch in Python 3 with PySide6; it reuses no upstream
code, icons, formats or trademarks.

## Usage

Launch `hashcheck`, choose a file, pick an algorithm, press **Compute**, paste
an expected digest into the field and press **Verify**. The result label shows
the computed digest or `Match` / `Mismatch`. Whitespace and letter case in the
expected digest are ignored.

Command line options work without a display:

```sh
hashcheck --help
hashcheck --version
```

## Install

```sh
pacman -S hashcheck
```

Or run `./hashcheck` from this directory (requires Python 3 and PySide6).

## Tests

```sh
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
```

Tests use only temporary files and need no network access.

## License

MIT — see [LICENSE](LICENSE).

## Appearance

The interface uses a shared dark theme with drawn vector icons (no external
icon theme required). A matching branded icon is installed for desktop menus.
