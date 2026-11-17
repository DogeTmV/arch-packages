#!/usr/bin/env bash
set -euo pipefail

# Build one package from a bundled projects/<name> source tree on the host.
# Mirrors what ci/build-packages.sh does inside the Arch container.

name="${1:-}"
if [[ -z "$name" ]]; then
  echo "Usage: $0 <package-name>" >&2
  exit 2
fi

root="$(cd "$(dirname "$0")/.." && pwd)"
pkgbuild="$root/packages/$name/PKGBUILD"
if [[ ! -f "$pkgbuild" ]]; then
  echo "No PKGBUILD found for $name" >&2
  exit 1
fi

build="$(mktemp -d)"
trap 'rm -rf "$build"' EXIT

cp "$pkgbuild" "$build/PKGBUILD"
if [[ -d "$root/projects/$name" ]]; then
  tar -czf "$build/local-source.tar.gz" -C "$root/projects" "$name"
fi

echo "Building $name in $build"
(cd "$build" && makepkg --noconfirm --clean)
ls -lh "$build"/*.pkg.tar.zst
