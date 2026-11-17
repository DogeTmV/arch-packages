# Shared Arch package repository

One GitHub Pages site and one pacman database for **all** DogeTmV projects.
Users add one `[dogetmv]` block once, then install any package with
`pacman -S <name>` and upgrade everything with `pacman -Syu`.

- Pages URL: `https://DogeTmV.github.io/arch-packages/`
- Repo DB name: `dogetmv` (so clients use `[dogetmv]` and the DB file is `dogetmv.db`)
- Hosted packages live in `public/x86_64/`

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

1. Create `packages/<name>/PKGBUILD` in this repo. For a project with release
   tags, use the tag archive as the source:

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

2. Push to `main`:

   ```bash
   git add packages/my-app/PKGBUILD
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
