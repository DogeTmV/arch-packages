# chartlet

`chartlet` converts CSV files into small, self-contained SVG charts using only
the Python 3 standard library. It draws bar charts, line charts, pie charts and
sparklines with axes, gridlines, legends and UTF-8 label support.

## Inspiration

Inspired by the discontinued **Google Chart API**, which let people generate
charts from simple data requests. This is an **original reimplementation, no
upstream code/assets**: nothing from that service was copied, and the output is
plain SVG generated locally with `xml.etree.ElementTree`.

## Install

Arch Linux: build the sibling `packages/chartlet/PKGBUILD` (for example with
`makepkg`), which installs `/usr/bin/chartlet`.

From source: copy `chartlet` to a directory on your `PATH` and make it
executable. Python 3.8+ is required; there are no third-party dependencies.

## Usage

```sh
chartlet bar data.csv bars.svg --x name --y value --title "Sales" --color 3568b4
chartlet line data.csv line.svg --x day --y temp --width 900 --height 400
chartlet pie data.csv pie.svg --label fruit --value count --title "Fruit mix"
chartlet sparkline data.csv spark.svg --value value
```

CSV input needs a header row. Numeric columns are validated per row: an invalid
value produces an error naming the row and column, and no SVG is written.
Column flags accept a header name or a 1-based column index. When omitted, the
last column is used as the numeric series and the first remaining column as
labels. `chartlet --help` and `chartlet --version` are always available.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

## Disclaimer

Original reimplementation, no upstream code/assets. This project is not
affiliated with or endorsed by Google.
