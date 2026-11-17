#!/usr/bin/env bash
set -uo pipefail

# Run the unittest suite of every bundled project. With --build, also run
# makepkg for each package using the same local source tarball as CI.

root="$(cd "$(dirname "$0")/.." && pwd)"
build=0
[[ "${1:-}" == "--build" ]] && build=1

failed=0
for dir in "$root"/projects/*; do
  [[ -d "$dir" ]] || continue
  name="$(basename "$dir")"
  # Only bundled, packaged projects are in scope here. Unpackaged source trees
  # (for example the shell-only terminal-autocorrect) have their own runners.
  [[ -f "$root/packages/$name/PKGBUILD" ]] || continue
  [[ -d "$dir/tests" ]] || continue
  echo "== $name =="
  if [[ -f "$dir/tests/run_all.sh" ]]; then
    # Shell-only projects (for example terminal-autocorrect) use their own
    # test harness; unittest discover reports "NO TESTS RAN" for those.
    if ! (cd "$dir" && bash tests/run_all.sh); then
      failed=1
    fi
  elif ! (cd "$dir" && QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v); then
    failed=1
  fi
  if ((build)); then
    echo "== build $name =="
    if ! "$root/ci/build-local.sh" "$name" >/dev/null; then
      failed=1
      echo "build failed: $name" >&2
    fi
  fi
done

exit "$failed"
