# chathoard

`chathoard` is a small offline CLI that archives exported chat logs from long-gone
IM services into one searchable, taggable store. It understands classic
`[2020-01-02 10:11] Alice: hello` exports, IRC-style `<Alice> hello` lines, and
falls back to keeping unstructured lines verbatim.

## Inspiration

Inspired by the discontinued instant messengers **AIM**, **MSN Messenger**,
**Yahoo Messenger**, **Google Talk**, and IRC log folders. This is an
**original reimplementation, no upstream code/assets** are included: it is a
new, independent tool that only reads plain-text logs you already own.

## Install

Arch Linux:

```sh
sudo pacman -S chathoard
```

From source (Python 3 standard library only):

```sh
chmod +x chathoard
install -Dm755 chathoard ~/.local/bin/chathoard
```

## Usage

```sh
chathoard import ~/exports/aim.log --service aim
chathoard import ~/exports/chat.txt --format irc
chathoard list
chathoard show c-1a2b3c4d5e6f
chathoard search "hello there"
chathoard tag c-1a2b3c4d5e6f friends
chathoard tags
chathoard export ./archive --format html
chathoard export ./archive-md --format markdown
chathoard stats
```

The default store is `~/.local/share/chathoard/store.json`. Pass `--db PATH`
before or after the subcommand to use another file. Re-importing the same file
and service replaces that conversation instead of duplicating it.

Exports are self-contained (no external CSS, scripts or images) and
deterministic: the same store always produces byte-identical files.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

## Disclaimer

Not affiliated with AOL, Microsoft, Yahoo, Google, or any IRC project. No
upstream code, logos, trademarks or assets are bundled. Licensed under the MIT
License; see `LICENSE`.
