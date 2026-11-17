#!/usr/bin/env bash
# Run every test file. Each test is isolated; no elevated permissions needed.
set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root" || exit 1

total=0
failures=0
for test_file in tests/test_*.sh; do
    printf '\n=== %s ===\n' "$test_file"
    output="$(bash "$test_file" 2>&1)"
    status="$?"
    printf '%s\n' "$output" | tail -n 2
    ((total++))
    if ((status != 0)); then
        printf '%s\n' "$output"
        ((failures++))
    fi
done

printf '\n%d suites, %d failed\n' "$total" "$failures"
((failures == 0))
