#!/usr/bin/env bash
# Tests for lib/candidates.sh: discovery, filtering, dedupe, and overrides.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
ac_test_init
source "$AC_TEST_ROOT/lib/candidates.sh"

check_valid() {
    local name="$1" expected="$2"
    if is_valid_command_name "$name"; then actual=0; else actual=1; fi
    assert_eq "valid name '$name'" "$expected" "$actual"
}

check_valid 'ls' 0
check_valid 'git+' 0
check_valid 'a_b' 0
check_valid '.hidden' 1
check_valid '-option' 1
check_valid 'bad name' 1
check_valid '' 1

make_bin ls grep
printf '#!/bin/sh\n' > "$AC_TEST_BIN/.hidden"
printf '#!/bin/sh\n' > "$AC_TEST_BIN/bad name"
chmod +x "$AC_TEST_BIN/.hidden" "$AC_TEST_BIN/bad name"

mkdir -p "$AC_TEST_TMP/bin2"
printf '#!/bin/sh\n' > "$AC_TEST_TMP/bin2/ls"
printf '#!/bin/sh\n' > "$AC_TEST_TMP/bin2/unique2"
chmod +x "$AC_TEST_TMP/bin2/"*

export AC_SEARCH_PATH="$AC_TEST_BIN:$AC_TEST_TMP/bin2"
export AC_EXTRA_CANDIDATES='cd zsh_builtin'

out="$(collect_all_candidates)"
assert_eq 'candidates are filtered, deduped and sorted' \
    $'cd\ngrep\nls\nunique2\nzsh_builtin' "$out"

export AC_IGNORE_CANDIDATES='grep unique2'
out="$(collect_all_candidates)"
assert_eq 'ignored candidates are removed' $'cd\nls\nzsh_builtin' "$out"

ac_test_summary
