#!/usr/bin/env bash
# Remove terminal-autocorrect from a fish configuration directory.
# Only the files created by install.sh are removed.

set -euo pipefail

config_dir="${AC_FISH_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/fish}"
rm -rf "$config_dir/autocorrect"
rm -f "$config_dir/conf.d/autocorrect.fish"
printf 'Removed terminal-autocorrect from %s\n' "$config_dir"
