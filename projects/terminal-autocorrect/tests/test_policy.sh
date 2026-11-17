#!/usr/bin/env bash
# Tests for lib/policy.sh: trust tiers, sudo rules, distance-2 suggestions,
# dangerous-command guard, and base-only corrections.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
ac_test_init
export AC_ROOT="$AC_TEST_ROOT"
for lib in system distance candidates common cache policy; do
    source "$AC_TEST_ROOT/lib/$lib.sh"
done

analyze() {
    policy_analyze "$@"
    printf '%s|%s|%s|%s\n' "$AC_DECISION" "$AC_CORRECTION" "$AC_MATCHES" "$AC_REASON"
}

make_bin ls grep rm sudo pacman frobnicate abcdefgh

# 1. trusted common command, unique one-edit typo -> RUN
out="$(analyze lss)"
assert_eq 'trusted unique typo is RUN' 'RUN|ls|ls|unique trusted one-edit match' "$out"

# 2. unique typo of an untrusted command -> SUGGEST only
unset AC_COMMON_FILE
printf '%s\n' 'ls' > "$AC_TEST_TMP/common-min.txt"
export AC_COMMON_FILE="$AC_TEST_TMP/common-min.txt"
out="$(analyze frobnicat)"
assert_eq 'untrusted unique typo is SUGGEST' \
    'SUGGEST||frobnicate|candidate is not trusted' "$out"

# 3. two equally close commands -> SUGGEST both
unset AC_COMMON_FILE
make_bin last
out="$(analyze lst)"
assert_eq 'ambiguous typo suggests every close command' \
    $'SUGGEST||last\tls|multiple close commands' "$out"

# 4. a recently used command (not in common list) becomes trusted
make_bin mytool
printf '%s\n' '- cmd: mytool --flag' '- cmd: mytool' > "$AC_HISTORY_FILES"
export AC_CACHE_MIN_COUNT=1
cache_rebuild
export AC_COMMON_FILE="$AC_TEST_TMP/common-min.txt"
out="$(analyze mytooll)"
assert_eq 'cached command is trusted for RUN' \
    'RUN|mytool|mytool|unique trusted one-edit match' "$out"

# 5. distance-two matches are suggested, never run
export AC_COMMON_FILE="$AC_TEST_TMP/common-min.txt"
out="$(analyze abXdefXh)"
assert_eq 'distance-two match is SUGGEST only' \
    'SUGGEST||abcdefgh|distance two suggestion' "$out"

# 6. sudo policy forces suggestions, except for pacman
unset AC_COMMON_FILE
out="$(analyze sduo apt-get)"
assert_eq 'sudo typo forces SUGGEST' \
    'SUGGEST||sudo|sudo requires confirmation' "$out"
out="$(analyze sduo pacman -Syu)"
assert_eq 'sudo pacman exception allows RUN' \
    'RUN|sudo|sudo|unique trusted one-edit match' "$out"

# 7. dangerous commands are never auto-run, even when common
out="$(analyze rrm)"
assert_eq 'dangerous command is SUGGEST only' \
    'SUGGEST||rm|dangerous command requires confirmation' "$out"

# 8. corrections never include arguments
out="$(policy_analyze pakman -Syu; printf '%s' "$AC_CORRECTION")"
assert_eq 'base of command only, no arguments' 'pacman' "$out"

# 9. no plausible match
out="$(analyze zzzzzzzz)"
assert_eq 'no close command -> NONE' 'NONE|||no close candidate' "$out"

# 10. sudo wrapper mode
policy_analyze_sudo paman -Syu
assert_eq 'sudo target pacman typo runs' 'RUN|pacman|pacman' \
    "$AC_DECISION|$AC_CORRECTION|$AC_MATCHES"
policy_analyze_sudo grpe file
assert_eq 'sudo target other typo suggests' 'SUGGEST||grep' \
    "$AC_DECISION|$AC_CORRECTION|$AC_MATCHES"
policy_analyze_sudo ls -la
assert_eq 'sudo target already correct -> NONE' 'NONE||' \
    "$AC_DECISION|$AC_CORRECTION|$AC_MATCHES"

# 11. explain output includes the reason
unset AC_COMMON_FILE
explanation="$(policy_explain lss)"
assert_contains 'explain reports decision' 'RUN' "$explanation"
assert_contains 'explain reports reason' 'unique trusted one-edit match' "$explanation"

# 12. configuration overrides
unset AC_COMMON_FILE
export AC_NEVER_AUTO='grep'
out="$(analyze grpe)"
assert_eq 'AC_NEVER_AUTO blocks auto-run' \
    'SUGGEST||grep|dangerous command requires confirmation' "$out"
unset AC_NEVER_AUTO

export AC_TRUST_EXTRA='frobnicate'
out="$(analyze frobnicat)"
assert_eq 'AC_TRUST_EXTRA enables auto-run' \
    'RUN|frobnicate|frobnicate|unique trusted one-edit match' "$out"
unset AC_TRUST_EXTRA

custom_danger="$AC_TEST_TMP/danger.txt"
printf '%s\n' 'grep' > "$custom_danger"
export AC_DANGEROUS_FILE="$custom_danger"
out="$(analyze grpe)"
assert_eq 'custom dangerous list is honored' \
    'SUGGEST||grep|dangerous command requires confirmation' "$out"
unset AC_DANGEROUS_FILE

make_bin lstx
export AC_MAX_SUGGESTIONS=2
out="$(analyze lst)"
assert_eq 'suggestion limit is honored' \
    $'SUGGEST||last\tls|multiple close commands' "$out"
unset AC_MAX_SUGGESTIONS

export AC_MIN_LEN_FOR_D2=10
out="$(analyze abXdefXh)"
assert_eq 'minimum length suppresses distance-two suggestions' \
    'NONE|||no close candidate' "$out"
unset AC_MIN_LEN_FOR_D2

ac_test_summary
