#!/usr/bin/env bash
# Tests for lib/distance.sh: edit distance, transpositions, and early exit.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
ac_test_init
source "$AC_TEST_ROOT/lib/distance.sh"

check_distance() {
    local a="$1" b="$2" expected="$3" got
    got="$(damerau_levenshtein "$a" "$b")"
    assert_eq "distance '$a' -> '$b'" "$expected" "$got"
}

check_distance '' '' 0
check_distance 'abc' '' 3
check_distance '' 'abc' 3
check_distance 'abc' 'abc' 0
check_distance 'kitten' 'sitting' 3
check_distance 'sl' 'ls' 1
check_distance 'lss' 'ls' 1
check_distance 'grpe' 'grep' 1
check_distance 'pakman' 'pacman' 1
check_distance 'ca' 'abc' 3

check_bounded() {
    local a="$1" b="$2" max="$3" expected="$4" got
    got="$(distance_at_most "$a" "$b" "$max")"
    assert_eq "bounded($a,$b,$max)" "$expected" "$got"
}

check_bounded 'lss' 'ls' 1 1
check_bounded 'kitten' 'sitting' 2 3
check_bounded 'kitten' 'sitting' 1 2
check_bounded 'abcdef' 'ghijkl' 1 2
check_bounded 'abc' 'abc' 1 0

ac_test_summary
