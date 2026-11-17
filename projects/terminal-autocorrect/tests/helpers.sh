#!/usr/bin/env bash
# Shared test helpers. Every test runs in a private temp directory; nothing
# here writes to the user's real HOME, shell config, or cache.

ac_test_init() {
    AC_TEST_ROOT="$(cd "$(dirname "${BASH_SOURCE[1]}")/.." && pwd)"
    AC_TEST_TMP="$(mktemp -d)"
    AC_TEST_BIN="$AC_TEST_TMP/bin"
    mkdir -p "$AC_TEST_BIN"

    # Isolate every path a test or the program might consult.
    export XDG_CACHE_HOME="$AC_TEST_TMP/xdg-cache"
    export XDG_CONFIG_HOME="$AC_TEST_TMP/xdg-config"
    export XDG_DATA_HOME="$AC_TEST_TMP/xdg-data"
    export HOME="$AC_TEST_TMP/home"
    export AC_CACHE_DIR="$AC_TEST_TMP/cache"
    export AC_SEARCH_PATH="$AC_TEST_BIN"
    export AC_HISTORY_FILES="$AC_TEST_TMP/fish_history"
    export AC_NO_AUTO_CACHE=1
    export AC_DISCOVER_SYSTEM_COMMANDS=0
    : > "$AC_HISTORY_FILES"
    mkdir -p "$HOME"

    trap 'rm -rf "$AC_TEST_TMP"' EXIT

    AC_PASS=0
    AC_FAIL=0
}

assert_eq() {
    local name="$1" expected="$2" actual="$3"
    if [[ "$actual" == "$expected" ]]; then
        printf 'ok   %s\n' "$name"
        ((AC_PASS++))
    else
        printf 'FAIL %s\n  expected: %q\n  actual:   %q\n' "$name" "$expected" "$actual"
        ((AC_FAIL++))
    fi
}

assert_contains() {
    local name="$1" needle="$2" output="$3"
    if [[ "$output" == *"$needle"* ]]; then
        printf 'ok   %s\n' "$name"
        ((AC_PASS++))
    else
        printf 'FAIL %s\n  missing: %s\n  output:  %q\n' "$name" "$needle" "$output"
        ((AC_FAIL++))
    fi
}

assert_not_contains() {
    local name="$1" needle="$2" output="$3"
    if [[ "$output" != *"$needle"* ]]; then
        printf 'ok   %s\n' "$name"
        ((AC_PASS++))
    else
        printf 'FAIL %s\n  unexpected: %s\n  output:     %q\n' "$name" "$needle" "$output"
        ((AC_FAIL++))
    fi
}

assert_true() {
    local name="$1"
    if (eval "$2"); then
        printf 'ok   %s\n' "$name"
        ((AC_PASS++))
    else
        printf 'FAIL %s\n  condition: %s\n' "$name" "$2"
        ((AC_FAIL++))
    fi
}

assert_count_lines() {
    local name="$1" expected="$2" output="$3"
    local actual
    actual="$(printf '%s\n' "$output" | grep -c . || true)"
    assert_eq "$name" "$expected" "$actual"
}

# Create executable stubs used as candidate commands.
make_bin() {
    local cmd
    for cmd in "$@"; do
        printf '#!/bin/sh\nexit 0\n' > "$AC_TEST_BIN/$cmd"
        chmod +x "$AC_TEST_BIN/$cmd"
    done
}

# Append fish-history style entries to the isolated history file.
add_fish_history() {
    local command_line="$1"
    printf -- '- cmd: %s\n' "$command_line" >> "$AC_HISTORY_FILES"
}

ac_test_summary() {
    printf '\n%d passed, %d failed\n' "$AC_PASS" "$AC_FAIL"
    ((AC_FAIL == 0))
}
