#!/usr/bin/env bash
# Install terminal-autocorrect into a fish configuration directory.
# Override AC_FISH_CONFIG_DIR (or XDG_CONFIG_HOME) to install elsewhere.

set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
config_dir="${AC_FISH_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/fish}"
target="$config_dir/autocorrect"

mkdir -p "$target/lib" "$target/share" "$config_dir/conf.d"

install -m 755 "$root/autocorrect.sh" "$target/autocorrect.sh"
install -m 644 "$root/fish_integration.fish" "$target/fish_integration.fish"
for lib in "$root"/lib/*.sh; do
    install -m 644 "$lib" "$target/lib/"
done
for data in "$root"/share/*; do
    install -m 644 "$data" "$target/share/"
done

loader="$config_dir/conf.d/autocorrect.fish"
tmp_loader="$(mktemp)"
printf '# Installed by terminal-autocorrect; remove this file to disable.\nsource "%s/fish_integration.fish"\n' \
    "$target" > "$tmp_loader"
if [[ -f "$loader" ]] && cmp -s "$tmp_loader" "$loader"; then
    rm -f "$tmp_loader"
else
    mv "$tmp_loader" "$loader"
fi

printf 'Installed to %s\n' "$config_dir"
printf 'Restart fish, or run: source "%s"\n' "$loader"
