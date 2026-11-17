# cardstack

A small terminal tool for keeping stacks of text cards, with numeric card IDs,
labelled links, wiki-style `[[Card Title]]` references, full-text search and
static HTML/Markdown export.

## Inspiration

Inspired by **Apple HyperCard** and its idea of linked stacks of cards. This is
an **original reimplementation, no upstream code/assets**: it does not use any
HyperCard code, stacks, icons, file formats or trademarks. The on-disk format is
plain JSON designed for this project.

## Install

```sh
pacman -S cardstack
```

Or run the script directly from this directory with Python 3.9+ (standard
library only):

```sh
./cardstack --help
```

## Usage

State lives in `~/.local/share/cardstack/stacks/<stack>.json`. Add `--dir PATH`
before or after any subcommand to use another directory (handy for tests).

```sh
cardstack new notes --title "Field Notes"
cardstack add notes --title "Welcome" --text 'See [[Ideas]] for more.'
cardstack add notes --title "Ideas" --text 'Turtle-inspired thoughts.'
cardstack list notes
cardstack show notes 1
cardstack edit notes 1 --text 'Updated text with [[Ideas]].'
cardstack link notes 1 2 --label "related"
cardstack links notes 1
cardstack find turtle --stack notes
cardstack export notes ./public --format html
cardstack export notes ./markdown --format markdown
cardstack rm notes 2
cardstack stacks
```

Cards are addressed by their stable numeric ID or by title. Removing a card
never reuses its ID. Wikilinks are resolved to local `card-<id>.html` or
`card-<id>.md` files during export; unresolved links are exported as plain
text.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

Tests use a temporary `--dir`, need no network and do not touch the home
directory.

## Disclaimer

An original reimplementation, no upstream code/assets. HyperCard is a
trademark of its respective owner; this project is unaffiliated.

## License

MIT — see [LICENSE](LICENSE).
