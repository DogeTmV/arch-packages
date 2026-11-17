#!/usr/bin/env bash
# Tests for install.sh and uninstall.sh using a private fish config dir.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
ac_test_init

installer="$AC_TEST_ROOT/install.sh"
uninstaller="$AC_TEST_ROOT/uninstall.sh"
config="$AC_TEST_TMP/xdg/fish"

AC_FISH_CONFIG_DIR="$config" bash "$installer" >/dev/null
AC_FISH_CONFIG_DIR="$config" bash "$installer" >/dev/null

assert_true 'bash helper installed' "[[ -f '$config/autocorrect/autocorrect.sh' ]]"
assert_true 'all libraries installed' \
    "[[ \$(find '$config/autocorrect/lib' -name '*.fish' -o -name '*.sh' | wc -l) -ge 6 ]]"
assert_true 'common-command list installed' \
    "[[ -f '$config/autocorrect/share/common-commands.txt' ]]"
assert_true 'dangerous-command list installed' \
    "[[ -f '$config/autocorrect/share/dangerous-commands.txt' ]]"
assert_true 'fish glue installed' \
    "[[ -f '$config/autocorrect/fish_integration.fish' ]]"
assert_true 'conf.d loader installed' \
    "[[ -f '$config/conf.d/autocorrect.fish' ]]"
assert_eq 'loader is written once' 1 \
    "$(grep -c 'fish_integration.fish' "$config/conf.d/autocorrect.fish")"

XDG_CONFIG_HOME="$AC_TEST_TMP/xdg" fish -c \
    'set -q __ac_script; and functions -q fish_command_not_found; and functions -q sudo; and functions -q __ac_record_command' \
    >/dev/null 2>&1
fish_status="$?"
assert_true 'fish autoloads every installed function' "[[ $fish_status -eq 0 ]]"

AC_FISH_CONFIG_DIR="$config" bash "$uninstaller" >/dev/null
assert_true 'uninstall removes the program directory' \
    "[[ ! -d '$config/autocorrect' ]]"
assert_true 'uninstall removes the loader' \
    "[[ ! -e '$config/conf.d/autocorrect.fish' ]]"
assert_true 'uninstall leaves conf.d intact' "[[ -d '$config/conf.d' ]]"

ac_test_summary
