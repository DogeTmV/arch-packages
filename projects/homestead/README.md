# homestead

Build a small static personal homepage: a landing page, individual pages, a
static guestbook and a themeable stylesheet. Pages are written in a small
Markdown-ish dialect parsed by this project's own standard-library converter.

## Inspiration

Inspired by **GeoCities**, **Microsoft FrontPage** and **Netscape Composer** —
the era of hand-built personal homepages. This is an **original
reimplementation, no upstream code/assets**: no GeoCities, FrontPage or
Netscape code, templates, clip art, logos or trademarks are used. Generated
HTML and CSS come from the templates below.

## Install

```sh
pacman -S homestead
```

Or run the Python 3 standard-library script directly:

```sh
./homestead --help
```

## Usage

```sh
homestead init ~/my-site --title "Ada's Place" --author Ada
cat > ~/my-site/hello.md <<'EOF'
# Hello!

Welcome to my corner of the web.

- First link
- Second link

Read [the guestbook](guestbook.html) or see ![my cat](cat.png).
EOF
homestead add ~/my-site "Hello" --file ~/my-site/hello.md --date 2020-01-02
homestead list ~/my-site
homestead page ~/my-site hello
homestead theme ~/my-site brick
homestead build ~/my-site --out ~/my-site/site
```

Built files: `index.html`, one `<slug>.html` per page, `guestbook.html` and
`styles.css`. The three themes are `classic`, `minimal` and `brick`; themes
only change `styles.css`, never the generated HTML. The guestbook is a static
form with no server backend.

Supported markup: `#`–`######` headings, blank-line-separated paragraphs,
consecutive `- ` or `* ` bullet lists, `[label](url)` links and
`![alt](url)` images. HTML special characters are escaped.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

Tests build sites in temporary directories, run offline and do not write to
the home directory.

## Disclaimer

An original reimplementation, no upstream code/assets. GeoCities, Microsoft
FrontPage and Netscape Composer are trademarks of their respective owners;
this project is unaffiliated.

## License

MIT — see [LICENSE](LICENSE).
