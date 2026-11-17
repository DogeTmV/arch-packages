#!/usr/bin/env bash
# Integration tests: drive real fish with the installed hook and sudo wrapper.
# All fake commands and caches live in a private temp directory.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
ac_test_init

integration="$AC_TEST_ROOT/fish_integration.fish"
main="$AC_TEST_ROOT/autocorrect.sh"

fake_command() {
    local name="$1" output="$2"
    printf '%s\n' '#!/bin/sh' "echo $output" > "$AC_TEST_BIN/$name"
    chmod +x "$AC_TEST_BIN/$name"
}
fake_command ls LSRAN
fake_command last LASTRAN
fake_command grep GREPRAN
fake_command apt-get APTRAN
fake_command pacman 'PACMAN ARGS: $*'
fake_command sudo 'SUDO RAN: $*'
fake_command frobnicate FROBRAN
fake_command mytool 'MYTOOL ARGS: $*'
fake_command rm RMRAN
fake_command unique2 UNIQUE2RAN

run_fish() {
    local code="$1" prelude="${2:-}"
    fish --no-config -c \
        "set -gx PATH $AC_TEST_BIN \$PATH; set -gx AC_SEARCH_PATH $AC_TEST_BIN; $prelude; source $integration; $code" 2>&1
}

out="$(run_fish 'lss')"
assert_contains 'mistyped ls runs ls silently' LSRAN "$out"
assert_not_contains 'silent correction prints no suggestion' 'Did you mean' "$out"

out="$(run_fish 'lst')"
assert_contains 'ambiguous typo prints a suggestion' 'Did you mean' "$out"
assert_not_contains 'ambiguous typo does not run a command' LSRAN "$out"

out="$(run_fish 'sduo apt-get')"
assert_contains 'mistyped sudo suggests sudo' 'sudo' "$out"

out="$(run_fish 'sudo grpe somefile')"
assert_contains 'sudo + mistyped grep suggests grep' 'grep' "$out"
assert_not_contains 'sudo suggestion does not run sudo' 'SUDO RAN' "$out"

out="$(run_fish 'sudo paman -Syu')"
assert_contains 'sudo + pacman typo runs pacman silently' 'SUDO RAN: pacman -Syu' "$out"

out="$(run_fish 'xyzzy')"
assert_contains 'unknown command falls through to fish' 'Unknown command' "$out"

out="$(run_fish 'frobnicat')"
assert_contains 'untrusted command is suggested' 'Did you mean: frobnicate' "$out"
assert_not_contains 'untrusted command is not executed' FROBRAN "$out"

out="$(run_fish 'rrm somefile')"
assert_contains 'dangerous command is suggested' 'Did you mean: rm' "$out"
assert_not_contains 'dangerous command is not executed' RMRAN "$out"

# A command seen twice in history becomes trusted and is silently corrected.
printf '%s\n' '- cmd: mytool --flag' '- cmd: mytool' > "$AC_HISTORY_FILES"
out="$(run_fish 'mytooll --other' 'set -e AC_NO_AUTO_CACHE')"
assert_contains 'cached command is silently corrected' 'MYTOOL ARGS: --other' "$out"
assert_not_contains 'cached correction prints no suggestion' 'Did you mean' "$out"

# Corrections must never add, drop, or rewrite arguments.
out="$(run_fish 'pakman -Syu extra')"
assert_contains 'base-only correction preserves arguments exactly' \
    'PACMAN ARGS: -Syu extra' "$out"

# The fish_postexec handler is wired to real interactive command lines; call
# it directly here so the test stays non-interactive and permission-free.
out="$(run_fish 'functions -q __ac_record_command; and __ac_record_command "unique2 --flag"')"
assert_eq 'postexec handler is defined and callable' 0 "$?"
cache_contents="$(cat "$(bash "$main" cache path)" 2>/dev/null || true)"
assert_contains 'postexec handler records the base command' 'unique2' "$cache_contents"

ac_test_summary
