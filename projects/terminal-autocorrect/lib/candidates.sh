#!/usr/bin/env bash
# Candidate discovery. A "candidate" is a command name we might suggest.
# Nothing here decides whether a candidate is trusted; that is policy.sh.

if ! declare -F ac_bin >/dev/null 2>&1; then
    source "$(dirname "${BASH_SOURCE[0]}")/system.sh"
fi

# Names with spaces, leading dots, or leading dashes are deliberately
# excluded: correcting to them would produce surprising command lines.
is_valid_command_name() {
    local name="$1"
    [[ -n "$name" ]] || return 1
    [[ "$name" != -* && "$name" != .* ]] || return 1
    [[ "$name" =~ ^[A-Za-z0-9_.+@-]+$ ]]
}

collect_all_candidates() {
    local search_path="${AC_SEARCH_PATH:-$PATH}"
    local dir entry name
    local -a dirs=() extras=() ignored=()
    local IFS=':'
    read -r -a dirs <<< "$search_path"
    IFS=$' \t\n'
    read -r -a extras <<< "${AC_EXTRA_CANDIDATES:-}"
    read -r -a ignored <<< "${AC_IGNORE_CANDIDATES:-}"

    {
        for dir in "${dirs[@]}"; do
            [[ -d "$dir" ]] || continue
            for entry in "$dir"/*; do
                [[ -f "$entry" && -x "$entry" ]] || continue
                name="${entry##*/}"
                is_valid_command_name "$name" && printf '%s\n' "$name"
            done
        done
        for name in "${extras[@]}"; do
            is_valid_command_name "$name" && printf '%s\n' "$name"
        done
    } | LC_ALL=C "$(ac_bin sort)" -u | {
        local candidate skip
        while IFS= read -r candidate; do
            skip=0
            for ignored_name in "${ignored[@]}"; do
                if [[ "$candidate" == "$ignored_name" ]]; then skip=1; break; fi
            done
            ((skip == 0)) && printf '%s\n' "$candidate"
        done
    }
}
