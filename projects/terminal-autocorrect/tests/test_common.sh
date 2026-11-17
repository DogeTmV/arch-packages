#!/usr/bin/env bash
# Tests for lib/common.sh: curated command list, overrides, and validation.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
ac_test_init
source "$AC_TEST_ROOT/lib/common.sh"

custom="$AC_TEST_TMP/common.txt"
printf '%s\n' '# a comment' 'ls' 'cd' 'ls' 'bad/name' '.hidden' '-option' '' > "$custom"
export AC_COMMON_FILE="$custom"

assert_eq 'comments, duplicates and invalid names are dropped' \
    $'cd\nls' "$(common_commands)"

if is_common_command 'ls'; then actual=0; else actual=1; fi
assert_eq 'ls is common' 0 "$actual"
if is_common_command 'grep'; then actual=0; else actual=1; fi
assert_eq 'grep is not in the custom common list' 1 "$actual"

unset AC_COMMON_FILE
export AC_ROOT="$AC_TEST_TMP/no-such-root"
fallback="$(common_commands)"
assert_true 'embedded fallback is available' '[[ -n "$fallback" ]]'
assert_contains 'fallback includes ls' 'ls' "$fallback"

ac_test_summary
