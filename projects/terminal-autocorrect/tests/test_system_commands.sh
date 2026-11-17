#!/usr/bin/env bash
# Tests for lib/system_commands.sh: scanning system dirs, packages, fish
# functions/completions, and caching the resulting command name base.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/helpers.sh"
ac_test_init
export AC_ROOT="$AC_TEST_ROOT"
for lib in system distance candidates common cache system_commands; do
    source "$AC_TEST_ROOT/lib/$lib.sh"
done

sysbin1="$AC_TEST_TMP/sysbin1"
sysbin2="$AC_TEST_TMP/sysbin2"
mkdir -p "$sysbin1" "$sysbin2"
for name in sysonly sharedcmd; do
    printf '#!/bin/sh\n' > "$sysbin1/$name"
    printf '#!/bin/sh\n' > "$sysbin2/$name"
    chmod +x "$sysbin1/$name" "$sysbin2/$name"
done
printf '#!/bin/sh\n' > "$sysbin2/secondonly"
chmod +x "$sysbin2/secondonly"

pkgfiles="$AC_TEST_TMP/package-files.txt"
printf '%s\n' \
    '/usr/bin/pkgonly' \
    '/usr/local/bin/pkgcmd' \
    '/usr/share/doc/pkgonly/README' \
    '/usr/bin/sharedcmd' > "$pkgfiles"

fishcfg="$AC_TEST_TMP/fishcfg"
mkdir -p "$fishcfg/functions" "$fishcfg/completions"
printf 'function myfunc\nend\n' > "$fishcfg/functions/myfunc.fish"
printf 'complete -c mycomp\n' > "$fishcfg/completions/mycomp.fish"

export AC_SYSTEM_COMMAND_DIRS="$sysbin1:$sysbin2"
export AC_PACKAGE_FILE_LIST="$pkgfiles"
export AC_FISH_FUNCTIONS_DIR="$fishcfg/functions"
export AC_FISH_COMPLETIONS_DIR="$fishcfg/completions"
export AC_DISCOVER_SYSTEM_COMMANDS=1

out="$(collect_system_command_names)"
for expected in sysonly sharedcmd secondonly pkgonly pkgcmd myfunc mycomp; do
    assert_contains "discovered $expected" "$expected" "$out"
done
assert_not_contains 'non-binary package paths are ignored' 'README' "$out"
assert_eq 'duplicates are removed and names sorted' \
    $'mycomp\nmyfunc\npkgcmd\npkgonly\nsecondonly\nsharedcmd\nsysonly' "$out"

assert_true 'system command cache is written' \
    '[[ -f "$(system_commands_cache_file)" ]]'

printf '#!/bin/sh\n' > "$sysbin1/newcmd"
chmod +x "$sysbin1/newcmd"
out="$(collect_system_command_names)"
assert_not_contains 'cached base is reused until rebuilt' 'newcmd' "$out"
system_commands_rebuild
out="$(collect_system_command_names)"
assert_contains 'rebuild picks up new system commands' 'newcmd' "$out"

out="$(collect_all_candidates)"
assert_contains 'candidate list includes system commands when enabled' 'pkgonly' "$out"
export AC_DISCOVER_SYSTEM_COMMANDS=0
out="$(collect_all_candidates)"
assert_not_contains 'candidate list excludes system commands when disabled' 'pkgonly' "$out"

ac_test_summary
