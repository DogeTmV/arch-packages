#!/usr/bin/env bash
# Test the fish-native installer: one source command installs and activates.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
ac_test_init

config="$AC_TEST_TMP/fish-config"
out="$(fish --no-config -c \
    "set -gx AC_FISH_CONFIG_DIR '$config'; source '$AC_TEST_ROOT/install.fish'; echo MARKER_DONE; functions -q fish_command_not_found; and echo MARKER_HOOK; functions -q sudo; and echo MARKER_SUDO; functions -q __ac_record_command; and echo MARKER_RECORDER; echo MARKER_SCRIPT=\$__ac_script" 2>&1)"

assert_contains 'fish installer reports activation' 'installed and activated in this fish session' "$out"
assert_contains 'source command completes' 'MARKER_DONE' "$out"
assert_contains 'not-found hook is active in same shell' 'MARKER_HOOK' "$out"
assert_contains 'sudo wrapper is active in same shell' 'MARKER_SUDO' "$out"
assert_contains 'command recorder is active in same shell' 'MARKER_RECORDER' "$out"
assert_contains 'script path is configured in same shell' 'MARKER_SCRIPT=' "$out"

assert_true 'program directory was created' "[[ -d '$config/autocorrect' ]]"
assert_true 'loader was created' "[[ -f '$config/conf.d/autocorrect.fish' ]]"
assert_true 'fish installer was copied' "[[ -f '$config/autocorrect/install.fish' ]]"

ac_test_summary
