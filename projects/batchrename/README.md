# batchrename

A small batch renamer window: pick files, type a naming pattern, preview the
old -> new list, then rename.

## Inspiration

Inspired by simple one-purpose desktop tools: a single window that does one job
with a visible preview before anything changes. This is an **original minimal
utility** written from scratch in Python 3 with PySide6; it reuses no upstream
code, icons, formats or trademarks.

## Pattern tokens

| Token | Meaning |
| --- | --- |
| `{name}` | original file name without its extension |
| `{n}` | 1-based index |
| `{nn}` | 1-based index, zero-padded to two digits |
| `{ext}` | original extension without the dot |

The original extension is appended automatically unless `{ext}` appears in the
pattern. The **Start** spin box sets the first index. Duplicate destinations are
rejected before any file is touched.

## Usage

Launch `batchrename`, press **Add Files**, enter a pattern such as
`{name}_{nn}`, optionally change **Start**, press **Preview**, review the list,
then press **Rename**.

Command line options work without a display:

```sh
batchrename --help
batchrename --version
```

## Install

```sh
pacman -S batchrename
```

Or run `./batchrename` from this directory (requires Python 3 and PySide6).

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
