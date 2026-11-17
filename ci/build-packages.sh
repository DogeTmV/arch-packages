#!/usr/bin/env bash
set -euo pipefail

REPO_DB="${REPO_DB:-dogetmv}"
PACKAGES="${PACKAGES:-all}"
DEST="/work/.stage/x86_64"
BUILD="/work/.build"

mkdir -p "$DEST"

selected=()
if [[ "$PACKAGES" == "all" ]]; then
  for pkgbuild in /work/packages/*/PKGBUILD; do
    [[ -f "$pkgbuild" ]] || continue
    selected+=("$(basename "$(dirname "$pkgbuild")")")
  done
elif [[ "$PACKAGES" != "none" ]]; then
  IFS=',' read -r -a selected <<< "$PACKAGES"
fi

for name in "${selected[@]}"; do
  srcdir="$BUILD/$name"
  rm -rf "$srcdir"
  mkdir -p "$srcdir"
  cp "/work/packages/$name/PKGBUILD" "$srcdir/PKGBUILD"
  echo "Building $name..."
  (cd "$srcdir" && makepkg --noconfirm --clean)
  for pkg in "$srcdir"/*.pkg.tar.zst; do
    [[ -f "$pkg" ]] || continue
    cp -f "$pkg" "$DEST/"
  done
done

cd "$DEST"
mapfile -t packages < <(find . -maxdepth 1 -name '*.pkg.tar.zst' -printf '%f\n' | sort)
if (( ${#packages[@]} == 0 )); then
  echo "No packages available for the repository" >&2
  exit 1
fi

repo-add --remove "${REPO_DB}.db.tar.gz" "${packages[@]}"
rm -f "${REPO_DB}.db.tar.gz.old" "${REPO_DB}.files.tar.gz.old"

# GitHub Pages artifacts do not preserve symlinks reliably, so replace
# repo-add's db/files symlinks with real files.
for suffix in db files; do
  if [[ -L "${REPO_DB}.${suffix}" ]]; then
    rm "${REPO_DB}.${suffix}"
  fi
  cp -f "${REPO_DB}.${suffix}.tar.gz" "${REPO_DB}.${suffix}"
done
