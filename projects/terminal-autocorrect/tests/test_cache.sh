#!/usr/bin/env bash
# Tests for lib/cache.sh: history parsing, rebuild, freshness, and mutations.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
ac_test_init
export AC_ROOT="$AC_TEST_ROOT"
source "$AC_TEST_ROOT/lib/cache.sh"

check_base() {
    local line="$1" expected="$2" got
    got="$(base_command_from_line "$line")"
    assert_eq "base of: $line" "$expected" "$got"
}

check_base '- cmd: ls -la' 'ls'
check_base '- cmd: sudo pacman -Syu' 'pacman'
check_base '- cmd: FOO=bar vim file' 'vim'
check_base ': 123456:0;grep foo' 'grep'
check_base 'command git status' 'git'
check_base 'nohup sleep 5 &' 'sleep'
check_base '   ' ''
check_base '' ''

printf '%s\n' \
    '- cmd: ls -la' \
    '- cmd: ls' \
    '- cmd: vim file' \
    '- cmd: vim other' \
    '- cmd: rare' \
    '- cmd: sudo pacman -Syu' > "$AC_HISTORY_FILES"

export AC_CACHE_MIN_COUNT=2
cache_rebuild
assert_eq 'only commands seen at least twice are trusted' \
    $'ls\t2\nvim\t2' "$(cat "$(cache_file)")"
assert_eq 'cache_names lists names only' $'ls\nvim' "$(cache_names)"

if is_cached_command 'ls'; then actual=0; else actual=1; fi
assert_eq 'ls is cached' 0 "$actual"
if is_cached_command 'rare'; then actual=0; else actual=1; fi
assert_eq 'rare is not cached' 1 "$actual"

if cache_is_fresh; then actual=0; else actual=1; fi
assert_eq 'fresh cache reports fresh' 0 "$actual"
export AC_CACHE_MAX_AGE=0
if cache_is_fresh; then actual=0; else actual=1; fi
assert_eq 'zero max age makes cache stale' 1 "$actual"

cache_add 'ls'
assert_eq 'cache_add increments an existing command' $'ls\t3\nvim\t2' "$(cat "$(cache_file)")"
cache_add 'newcmd'
cache_add 'newcmd'
assert_eq 'cache_add inserts a new command' $'ls\t3\nnewcmd\t2\nvim\t2' "$(cat "$(cache_file)")"

cache_stats | grep -q 'commands=3'
assert_eq 'cache_stats reports command count' 0 "$?"

cache_clear
assert_true 'cache_clear removes the file' '[[ ! -f "$(cache_file)" ]]'

cache_ensure
assert_true 'cache_ensure respects AC_NO_AUTO_CACHE' '[[ ! -f "$(cache_file)" ]]'
unset AC_NO_AUTO_CACHE
cache_ensure
assert_true 'cache_ensure builds a missing cache' '[[ -f "$(cache_file)" ]]'

assert_true 'no temporary files are left behind' \
    '[[ -z "$(find "$(cache_dir)" -name "*.tmp.*" -print -quit 2>/dev/null)" ]]'

ac_test_summary
