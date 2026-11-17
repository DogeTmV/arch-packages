# knowbase

`knowbase` is an offline encyclopedia and browser. Articles are plain UTF-8
JSON files with `title`, `body`, `tags` and `see_also` fields, so a collection
can be edited by hand, versioned, and read without any service running.

## Inspiration

Inspired by the discontinued **Microsoft Encarta** encyclopedia. This is an
**original reimplementation, no upstream code/assets**: the bundled sample
articles were written from scratch for this project, and no Encarta text,
images, UI or proprietary format is used.

## Install

Arch Linux: build the sibling `packages/knowbase/PKGBUILD`, which installs
`/usr/bin/knowbase` and the sample article data under `/usr/share/knowbase`.

From source: place `knowbase` on your `PATH` and keep its `share/` directory
next to it. Python 3.8+ is required; there are no third-party dependencies.

## Usage

```sh
knowbase init ~/notes/kb --sample          # --sample is optional
knowbase add ~/notes/kb "Tides" --body article.txt --tags ocean,moon --see "Maps"
printf 'Text from stdin\n' | knowbase add ~/notes/kb "New article" --body -
knowbase list ~/notes/kb --tag ocean
knowbase show ~/notes/kb "Tides"
knowbase search ~/notes/kb "moon pulls"
knowbase random ~/notes/kb
knowbase stats ~/notes/kb
knowbase export ~/notes/kb ~/site --format html
knowbase rm ~/notes/kb "New article"
```

`--body -` reads the body from standard input. `init --sample` installs eight
short original general-knowledge articles. `export` writes one HTML or Markdown
file per article, escaping HTML bodies safely. All commands return a non-zero
status with a useful message on stderr for invalid input.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

## Disclaimer

Original reimplementation, no upstream code/assets. Not affiliated with or
endorsed by Microsoft.
