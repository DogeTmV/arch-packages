# Fish-native installer for terminal-autocorrect.
#
# Usage:
#   source /path/to/terminal-autocorrect/install.fish
#
# This installs the program with install.sh and immediately activates the
# hooks in the *current* fish session. There is no separate "launch" step and
# no need to edit config.fish by hand. New fish shells load it automatically
# through conf.d/autocorrect.fish.

set -l source_dir (path resolve (path dirname (status filename)))

# Resolve the same config directory install.sh uses, then pass it explicitly
# so both sides agree even when XDG_CONFIG_HOME is unusual.
set -l config_dir "$AC_FISH_CONFIG_DIR"
if test -z "$config_dir"
    if set -q XDG_CONFIG_HOME
        set config_dir "$XDG_CONFIG_HOME/fish"
    else
        set config_dir "$HOME/.config/fish"
    end
end

set -lx AC_FISH_CONFIG_DIR "$config_dir"
bash "$source_dir/install.sh"
if test $status -ne 0
    echo "terminal-autocorrect installation failed" >&2
    return $status
end

# Activate right now, not only after a restart.
source "$config_dir/conf.d/autocorrect.fish"

echo "terminal-autocorrect installed and activated in this fish session"
echo "config: $config_dir"
