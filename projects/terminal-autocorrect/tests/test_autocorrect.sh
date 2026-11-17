#!/usr/bin/env bash
# CLI-level tests for autocorrect.sh, including the original hook contract.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
ac_test_init

main="$AC_TEST_ROOT/autocorrect.sh"
run() { bash "$main" "$@"; }

make_bin ls cd grep make last sudo pacman frobnicate abcdefgh rm

# --- original hook contract -------------------------------------------------
assert_eq 'unique minor typo -> RUN' $'RUN\tls' "$(run check lss)"
assert_eq 'two equally close candidates -> SUGGEST' $'SUGGEST\tlast\tls' "$(run check lst)"
assert_eq 'transposed letters -> RUN' $'RUN\tls' "$(run check sl)"
assert_eq 'no close candidate -> NONE' 'NONE' "$(run check xyzzy)"

# --- sudo rules -------------------------------------------------------------
assert_eq 'mistyped sudo, non-pacman target -> SUGGEST' \
    $'SUGGEST\tsudo' "$(run check sduo apt-get)"
assert_eq 'mistyped sudo, pacman target -> RUN' \
    $'RUN\tsudo' "$(run check sduo pacman -Syu)"
assert_eq 'sudo mode + pacman typo -> RUN' \
    $'RUN\tpacman' "$(run sudo paman -Syu)"
assert_eq 'sudo mode + other typo -> SUGGEST' \
    $'SUGGEST\tgrep' "$(run sudo grpe somefile)"
assert_eq 'sudo mode + correct command -> NONE' 'NONE' "$(run sudo ls -la)"

# --- trust tiers and safety -------------------------------------------------
assert_eq 'untrusted unique typo -> SUGGEST' \
    $'SUGGEST\tfrobnicate' "$(run check frobnicat)"
assert_eq 'distance-two match -> SUGGEST' \
    $'SUGGEST\tabcdefgh' "$(run check abXdefXh)"
assert_eq 'dangerous command -> SUGGEST' \
    $'SUGGEST\trm' "$(run check rrm)"

out="$(run check pakman -Syu somepackage)"
assert_eq 'only the base command is corrected' $'RUN\tpacman' "$out"
assert_not_contains 'arguments are never rewritten' 'Syu' "$out"

out="$(run explain lss)"
assert_contains 'explain prints decision' 'decision: RUN' "$out"
assert_contains 'explain prints reason' 'unique trusted one-edit match' "$out"

out="$(run candidates lst)"
assert_contains 'candidates lists close names' $'ls\t1' "$out"
assert_contains 'candidates lists both close names' $'last\t1' "$out"

# --- cache subcommands ------------------------------------------------------
unset AC_NO_AUTO_CACHE
printf '%s\n' '- cmd: mytool --flag' '- cmd: mytool' '- cmd: ls' > "$AC_HISTORY_FILES"
out="$(run cache rebuild)"
assert_contains 'cache rebuild reports stats' 'commands=' "$out"
out="$(run cache list)"
assert_contains 'cache list shows recent command' 'mytool' "$out"
out="$(run cache stats)"
assert_contains 'cache stats shows path' 'path=' "$out"
out="$(run cache path)"
assert_contains 'cache path points at TSV' 'commands.tsv' "$out"
run cache add manualcmd
out="$(run cache list)"
assert_contains 'cache add records a command' 'manualcmd' "$out"
run cache add-line 'sudo git status'
out="$(run cache list)"
assert_contains 'cache add-line records the base command' 'git' "$out"
run cache clear
out="$(run cache list)"
assert_count_lines 'cache clear empties the cache' 0 "$out"

# --- help and error handling ------------------------------------------------
assert_eq 'version' '2.0.0' "$(run version)"
assert_contains 'help mentions check' 'check <typed>' "$(run help)"
run no-such-mode >/dev/null 2>&1
assert_eq 'unknown mode exits 2' 2 "$?"

ac_test_summary
