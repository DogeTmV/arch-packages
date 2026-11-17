#!/usr/bin/env bash
set -euo pipefail

# Runs as root inside archlinux:base-devel.  makepkg itself runs as "builder".
pacman -Syu --noconfirm --needed \
  python python-build python-installer python-setuptools python-wheel \
  python-av python-numpy pyside6 ffmpeg fish git

useradd -m builder

mkdir -p /work/.build /work/.stage/x86_64

# Seed the staging directory with whatever is currently published so that
# repo-add rebuilds a complete database, not just the newly built package.
if compgen -G "/work/public/x86_64/*" >/dev/null; then
  cp -a /work/public/x86_64/. /work/.stage/x86_64/
fi

# Keep ownership changes away from the checkout: the host runner still needs
# to read/write public/ and commit the result.
chown -R builder:builder /work/.build /work/.stage

su -s /bin/bash builder -c \
  "cd /work && PACKAGES='$PACKAGES' REPO_DB='$REPO_DB' ci/build-packages.sh"

cd /work/.stage/x86_64
ls -lh
