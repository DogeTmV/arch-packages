#!/usr/bin/env bash
# Tests for lib/ranking.sh: usage-based ordering of suggestions.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
ac_test_init
export AC_ROOT="$AC_TEST_ROOT"
for lib in system distance candidates common cache ranking; do
    source "$AC_TEST_ROOT/lib/$lib.sh"
done

make_bin ls last grep frobnicate othercmd

printf '%s\n' \
    '- cmd: ls' \
    '- cmd: last one' \
    '- cmd: last two' \
    '- cmd: last three' \
    '- cmd: last four' \
    '- cmd: frobnicate a' \
    '- cmd: frobnicate b' \
    '- cmd: frobnicate c' \
    '- cmd: frobnicate d' \
    '- cmd: othercmd' > "$AC_HISTORY_FILES"
export AC_CACHE_MIN_COUNT=1
cache_rebuild

assert_eq 'common bonus outranks raw usage' \
    $'ls\nlast' "$(printf '%s\n' last ls | rank_matches)"

assert_eq 'most-used command ranks first' \
    $'frobnicate\nothercmd' "$(printf '%s\n' othercmd frobnicate | rank_matches)"

assert_eq 'common command outranks untrusted command' \
    $'grep\nfrobnicate' "$(printf '%s\n' frobnicate grep | rank_matches)"

assert_eq 'ties are alphabetical' \
    $'frobnicate\nothercmd' "$(printf '%s\n' othercmd frobnicate | rank_matches)"

popular="$AC_TEST_TMP/popular.txt"
printf '%s\n' 'frobnicate' > "$popular"
export AC_POPULAR_FILE="$popular"
assert_eq 'popular list boosts a command' \
    $'frobnicate\nothercmd' "$(printf '%s\n' othercmd frobnicate | rank_matches)"
unset AC_POPULAR_FILE

frob_score="$(usage_score frobnicate)"
other_score="$(usage_score othercmd)"
assert_true 'higher usage yields higher score' "[[ $frob_score -gt $other_score ]]"

ac_test_summary
