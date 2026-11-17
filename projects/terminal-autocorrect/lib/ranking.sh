#!/usr/bin/env bash
# Usage-based ranking for suggestions. Ranking never grants trust; it only
# decides the order in which equally close candidates are shown.

for _dep in system common cache; do
    if ! declare -F "$(case "$_dep" in
        system) echo ac_bin ;;
        common) echo is_common_command ;;
        cache) echo cache_file ;;
    esac)" >/dev/null 2>&1; then
        source "$(dirname "${BASH_SOURCE[0]}")/$_dep.sh"
    fi
done
unset _dep

_popular_file() {
    printf '%s\n' "${AC_POPULAR_FILE:-${AC_ROOT:-}/share/popular-commands.txt}"
}

is_popular_command() {
    local wanted="$1" file line
    file="$(_popular_file)"
    [[ -r "$file" ]] || return 1
    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%%#*}"
        line="${line//$'\t'/ }"
        local name
        for name in $line; do
            [[ "$name" == "$wanted" ]] && return 0
        done
    done < "$file"
    return 1
}

cache_count_for() {
    local wanted="$1" file name count
    file="$(cache_file)"
    if [[ -f "$file" ]]; then
        while IFS=$'\t' read -r name count; do
            if [[ "$name" == "$wanted" ]]; then
                printf '%s\n' "${count:-0}"
                return
            fi
        done < "$file"
    fi
    printf '0\n'
}

usage_score() {
    local name="$1" count score
    count="$(cache_count_for "$name")"
    score=$((count * 10))
    is_common_command "$name" && score=$((score + 1000))
    is_popular_command "$name" && score=$((score + 500))
    printf '%s\n' "$score"
}

# Reads command names on stdin, writes them ordered by usage (best first),
# with alphabetical ties broken deterministically.
rank_matches() {
    local name score
    {
        while IFS= read -r name; do
            [[ -n "$name" ]] || continue
            score="$(usage_score "$name")"
            printf '%s\t%s\n' "$score" "$name"
        done
    } | LC_ALL=C "$(ac_bin sort)" -t $'\t' -k1,1nr -k2,2 |
        while IFS=$'\t' read -r score name; do
            printf '%s\n' "$name"
        done
}
