#!/usr/bin/env bash
# Smoke test for the bundled demo script.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
ac_test_init

export AC_SEARCH_PATH='/usr/bin:/bin'
out="$(fish --no-config "$AC_TEST_ROOT/examples/demo.fish" 2>&1)"
assert_contains 'demo explains a trusted typo' 'decision: RUN' "$out"
assert_contains 'demo explains an ambiguous typo' 'decision: SUGGEST' "$out"
assert_contains 'demo explains a sudo typo' 'sudo requires confirmation' "$out"

ac_test_summary
