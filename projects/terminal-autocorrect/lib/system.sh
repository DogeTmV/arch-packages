#!/usr/bin/env bash
# Resolve external utilities from a fixed system path so a command named
# "grep" or "sort" earlier in the user's PATH can never change safety
# decisions made by this program.

AC_SYSTEM_PATH="${AC_SYSTEM_PATH:-/usr/bin:/bin:/usr/sbin:/sbin}"

declare -gA _AC_BIN_CACHE=()

ac_bin() {
    local name="$1" p
    if [[ -n "${_AC_BIN_CACHE[$name]:-}" ]]; then
        printf '%s\n' "${_AC_BIN_CACHE[$name]}"
        return
    fi

    local IFS=':'
    local -a dirs=()
    read -r -a dirs <<< "$AC_SYSTEM_PATH"
    for p in "${dirs[@]}"; do
        if [[ -n "$p" && -x "$p/$name" ]]; then
            _AC_BIN_CACHE[$name]="$p/$name"
            printf '%s\n' "$p/$name"
            return
        fi
    done

    p="$(command -v "$name" 2>/dev/null || true)"
    _AC_BIN_CACHE[$name]="${p:-$name}"
    printf '%s\n' "${p:-$name}"
}

# Valid command names only. Names with spaces, leading dots, or leading
# dashes are excluded: correcting to them would produce surprising input.
is_valid_command_name() {
    local name="$1"
    [[ -n "$name" ]] || return 1
    [[ "$name" != -* && "$name" != .* ]] || return 1
    [[ "$name" =~ ^[A-Za-z0-9_.+@-]+$ ]]
}

# Pure-bash exact line membership. Avoids grep entirely in trust checks.
ac_list_contains() {
    local wanted="$1" item
    shift
    for item in "$@"; do
        [[ "$item" == "$wanted" ]] && return 0
    done
    return 1
}

ac_file_contains_line() {
    local wanted="$1" file="$2" line
    [[ -r "$file" ]] || return 1
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ "$line" == "$wanted" ]] && return 0
    done < "$file"
    return 1
}
