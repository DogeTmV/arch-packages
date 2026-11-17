# Shared Arch package repository

One GitHub Pages site and one pacman database for **all** DogeTmV projects.
Users add one `[dogetmv]` block once, then install any package with
`pacman -S <name>` and upgrade everything with `pacman -Syu`.

- Pages URL: `https://DogeTmV.github.io/arch-packages/`
- Repo DB name: `dogetmv` (so clients use `[dogetmv]` and the DB file is `dogetmv.db`)
- Hosted packages live in `public/x86_64/`

## Bundled source projects

Source trees kept alongside the package definitions live in `projects/`. The
`DISCONTINUED-SOFTWARE.md` research document lists the retired programs that
inspired the new tools; every successor is original code with no upstream
assets.

- [`projects/terminal-autocorrect`](projects/terminal-autocorrect/README.md) —
  conservative fish command typo correction with a recent-command cache,
  whole-system command discovery, usage-ranked suggestions, and a fish-native
  installer (`source install.fish`) that activates automatically.

Feed and data tools:

- [`projects/rssledger`](projects/rssledger/README.md) — local RSS/Atom reader with OPML import/export.
- [`projects/pipeway`](projects/pipeway/README.md) — composable feed/data pipelines with JSON configs.
- [`projects/desksearch`](projects/desksearch/README.md) — local full-text index with snippets and ranking.
- [`projects/chartlet`](projects/chartlet/README.md) — CSV-to-SVG bar, line, pie, and sparkline charts.
- [`projects/photoatlas`](projects/photoatlas/README.md) — photo index, duplicate finder, tags, and static galleries.

Communication and archive tools:

- [`projects/chathoard`](projects/chathoard/README.md) — unified chat-log archive, search, and export.
- [`projects/bookmarkdeck`](projects/bookmarkdeck/README.md) — bookmark manager with Netscape HTML import/export.
- [`projects/notebox`](projects/notebox/README.md) — tagged local notebook with Markdown/HTML export.
- [`projects/threadweave`](projects/threadweave/README.md) — mbox importer and threaded conversation browser.
- [`projects/knowbase`](projects/knowbase/README.md) — offline article encyclopedia with original sample content.

Retro desktop tools:

- [`projects/minamp`](projects/minamp/README.md) — playlist manager and playback front-end with M3U support.
- [`projects/cardstack`](projects/cardstack/README.md) — linked text card stacks with wiki links.
- [`projects/memopad`](projects/memopad/README.md) — memo database with categories and CSV/JSON round-trips.
- [`projects/snakecell`](projects/snakecell/README.md) — deterministic terminal Snake game.
- [`projects/starsaver`](projects/starsaver/README.md) — starfield, digital-rain, and pipes terminal screensavers.
- [`projects/homestead`](projects/homestead/README.md) — themed static personal-site generator.

Local services and planning:

- [`projects/contextcards`](projects/contextcards/README.md) — date-driven local context digest.
- [`projects/tripplan`](projects/tripplan/README.md) — offline itineraries with ICS export.
- [`projects/printbridge`](projects/printbridge/README.md) — authenticated loopback HTTP-to-`lp` print bridge.

Minimal GUI utilities (PySide6; media tools shell out to `ffmpeg`/`ffprobe` or
`yt-dlp` via argument lists, never a shell):

- [`projects/tapecut`](projects/tapecut/README.md) — one-button audio trimmer: open, set Start/Length, export.
- [`projects/toneshift`](projects/toneshift/README.md) — speed/pitch slider using chained `atempo` filters.
- [`projects/soundboard`](projects/soundboard/README.md) — eight click-to-play slots with right-click assign.
- [`projects/fileforge`](projects/fileforge/README.md) — small text/image/audio file converter.
- [`projects/ytdock`](projects/ytdock/README.md) — yt-dlp GUI with best/video/audio/small presets and a live log.
- [`projects/cutframe`](projects/cutframe/README.md) — video editor with Cut and Crop toggle panels.
- [`projects/hashcheck`](projects/hashcheck/README.md) — compute and verify MD5/SHA-1/SHA-256/SHA-512 hashes.
- [`projects/batchrename`](projects/batchrename/README.md) — pattern-based batch renamer with preview and collision checks.
- [`projects/jsonpolish`](projects/jsonpolish/README.md) — JSON format, minify, validate, and copy.

Run the whole bundled suite with `./ci/test-projects.sh --build`.

A pacman repo is just a directory plus a `<name>.db` file; nothing ties it to a
single source project. The repo name is effectively permanent because pacman
downloads `<section-name>.db` from the `Server` URL.

## Users: one-time setup

Add this to `/etc/pacman.conf`:

```ini
[dogetmv]
SigLevel = Optional TrustAll
Server = https://DogeTmV.github.io/arch-packages/$arch
```

Then:

```bash
sudo pacman -Syu
sudo pacman -S ralsei-cut
```

`Optional TrustAll` is used because the repo is unsigned. Future projects need
no further client configuration.

## First-time GitHub setup

This directory is ready to push as its own public repository named
`arch-packages`:

```bash
cd /home/doge/arch-packages
git init -b main
git add -A
git commit -m "Initial shared pacman repository"
gh repo create DogeTmV/arch-packages --public --source=. --remote=origin
gh api --method POST repos/DogeTmV/arch-packages/pages -f build_type=workflow
git push -u origin main
gh run watch
```

If `gh api` says Pages is already enabled, ignore the 409. After the run
finishes, verify:

```bash
curl -I https://DogeTmV.github.io/arch-packages/x86_64/dogetmv.db
curl -I https://DogeTmV.github.io/arch-packages/x86_64/ralsei-cut-1.0.0-1-x86_64.pkg.tar.zst
```

Both should return `HTTP/2 200`.

## Adding another project

Projects whose source lives in this repo are the simplest case. Put the source
tree in `projects/<name>/` and use this `packages/<name>/PKGBUILD`:

```bash
# Maintainer: DogeTmV
pkgname=my-app
pkgver=0.1.0
pkgrel=1
pkgdesc='Short description'
arch=('any')
url='https://github.com/DogeTmV/arch-packages'
license=('MIT')
depends=('python')
source=("local-source.tar.gz")
sha256sums=('SKIP')

package() {
  cd "$pkgname"
  install -Dm755 "$pkgname" "$pkgdir/usr/bin/$pkgname"
  install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
```

The workflow tars `projects/<name>` into `local-source.tar.gz` next to the
PKGBUILD before invoking `makepkg`, and a push that touches either `projects/`
or `packages/` triggers a rebuild. You can test the same flow locally with
`./ci/build-local.sh <name>`.

For a project with its own release tags, use the tag archive as the source:

```bash
# Maintainer: DogeTmV
pkgname=my-app
pkgver=2.1.0
pkgrel=1
pkgdesc='Short description'
arch=('x86_64')
url='https://github.com/DogeTmV/my-app'
license=('MIT')
depends=('python')
makedepends=('python-build' 'python-installer' 'python-setuptools' 'python-wheel')
source=("$pkgname-$pkgver.tar.gz::https://github.com/DogeTmV/my-app/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
  cd "$pkgname-$pkgver"
  python -m build --wheel --no-isolation
}

package() {
  cd "$pkgname-$pkgver"
  python -m installer --destdir="$pkgdir" dist/*.whl
}
```

Replace the `build()`/`package()` bodies if the project is not a Python
package. Use a real SHA-256 instead of `SKIP` when you want reproducible
builds: `curl -L <source-url> | sha256sum`.

Finally, push to `main`:

```bash
git add packages/my-app/PKGBUILD projects/my-app
git commit -m "Add my-app"
git push
```

The workflow detects which `packages/*` directories changed, builds only
those in an Arch container, copies the resulting `.pkg.tar.zst` into the
staged repo, rebuilds `dogetmv.db` from every package present (removing stale
versions), commits the result into `public/`, and deploys `public/` to Pages.

You can also force a specific build from the Actions tab with
**Run workflow → packages**, entering `all`, `none`, or a comma-separated list
such as `ralsei-cut,my-app`.

## Notes about Ralsei Cut

The `v1.0.0` tag in `DogeTmV/ralsei-cut` still points at the initial commit,
before the CI fixes, so `packages/ralsei-cut/PKGBUILD` currently downloads the
exact fixed commit (`a52beb…`) that produced the published binary. When you cut
a proper next release, switch that PKGBUILD to the tag URL shown in its
comment, bump `pkgver`, and let the workflow republish.

## Migrating existing users

Tell users to replace their old `[ralsei-cut]` block in `/etc/pacman.conf`
with the single `[dogetmv]` block above and run `sudo pacman -Syu`. The old
per-project Pages repo in `DogeTmV/ralsei-cut` can then be left alone or its
publish workflow disabled; it is not needed anymore.

## Signing later

Generate one GPG key in this repo, add `repo-add --sign`, and import the public
key in clients. Then every project is signed at once and users can replace
`Optional TrustAll` with `Required DatabaseOptional`.
