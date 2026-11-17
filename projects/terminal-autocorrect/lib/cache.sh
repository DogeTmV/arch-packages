#!/usr/bin/env bash
# Recently-used command cache.
#
# The cache is built from local shell history files only. It never needs
# elevated permissions and never reads another user's data. Entries are
# "name<TAB>count", sorted by count descending. Trust is decided elsewhere:
# this module merely records what the user has actually run.

if ! declare -F is_valid_command_name >/dev/null 2>&1; then
    source "$(dirname "${BASH_SOURCE[0]}")/candidates.sh"
fi
if ! declare -F ac_bin >/dev/null 2>&1; then
    source "$(dirname "${BASH_SOURCE[0]}")/system.sh"
fi

cache_dir() {
    printf '%s\n' "${AC_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/terminal-autocorrect}"
}

cache_file() {
    printf '%s\n' "$(cache_dir)/commands.tsv"
}

ac_history_files() {
    if [[ -n "${AC_HISTORY_FILES:-}" ]]; then
        printf '%s\n' "$AC_HISTORY_FILES"
        return
    fi
    local data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
    local zdotdir="${ZDOTDIR:-$HOME}"
    local -a paths=(
        "$data_home/fish/fish_history"
        "$HOME/.config/fish/fish_history"
        "$HOME/.bash_history"
        "$HOME/.zsh_history"
        "$zdotdir/.zsh_history"
    )
    local path result=''
    for path in "${paths[@]}"; do
        [[ ":$result:" == *":$path:"* ]] && continue
        result+="${result:+:}$path"
    done
    printf '%s\n' "$result"
}

# Reduce a history line to the bare command name. Handles fish's "- cmd: ",
# zsh's extended ": <time>:<dur>;", assignment prefixes and common wrappers
# such as sudo/env/command/nohup.
base_command_from_line() {
    local line="$1"
    line="${line#"${line%%[![:space:]]*}"}"
    [[ -n "$line" ]] || return 0

    if [[ "$line" == '- cmd: '* ]]; then
        line="${line#- cmd: }"
    elif [[ "$line" == :*\;* ]]; then
        line="${line#*;}"
    fi

    local -a tokens=()
    local IFS=$' \t\n'
    read -r -a tokens <<< "$line"
    local i raw_prev='' token result=''
    for ((i = 0; i < ${#tokens[@]}; i++)); do
        token="${tokens[i]}"
        if [[ "$token" == *=* || "$token" == -* ]]; then
            raw_prev="$token"
            continue
        fi
        case "$token" in
            sudo|doas|env|command|builtin|time|nohup|nice|ionice)
                raw_prev="$token"
                continue
                ;;
        esac
        if [[ "$raw_prev" == '-u' || "$raw_prev" == '-g' ]]; then
            raw_prev="$token"
            continue
        fi
        result="$token"
        break
    done

    is_valid_command_name "$result" && printf '%s\n' "$result"
}

_cache_lock() {
    local op="$1"
    command -v flock >/dev/null 2>&1 || return 0
    if [[ "$op" == open ]]; then
        exec 9>"$(cache_dir)/.lock"
        flock -x 9
    else
        flock -u 9 2>/dev/null || true
        exec 9>&- 2>/dev/null || true
    fi
}

cache_rebuild() {
    local dir file tmp path line cmd min
    dir="$(cache_dir)"
    mkdir -p "$dir" || return 1
    file="$(cache_file)"
    tmp="$file.tmp.$$"
    min="${AC_CACHE_MIN_COUNT:-1}"

    _cache_lock open
    local -A counts=()
    local -a sources=()
    local IFS=':'
    read -r -a sources <<< "$(ac_history_files)"

    for path in "${sources[@]}"; do
        [[ -f "$path" && -r "$path" ]] || continue
        while IFS= read -r line || [[ -n "$line" ]]; do
            cmd="$(base_command_from_line "$line")"
            [[ -n "$cmd" ]] || continue
            counts["$cmd"]=$(( ${counts["$cmd"]:-0} + 1 ))
        done < "$path"
    done

    {
        for cmd in "${!counts[@]}"; do
            ((counts["$cmd"] >= min)) && printf '%s\t%s\n' "$cmd" "${counts[$cmd]}"
        done
    } | LC_ALL=C "$(ac_bin sort)" -t $'\t' -k2,2nr -k1,1 > "$tmp"
    mv -f "$tmp" "$file"
    _cache_lock close
}

cache_is_fresh() {
    local file max mtime now
    file="$(cache_file)"
    [[ -f "$file" ]] || return 1
    max="${AC_CACHE_MAX_AGE:-86400}"
    ((max > 0)) || return 1
    mtime="$("$(ac_bin stat)" -c %Y "$file" 2>/dev/null)" || return 1
    now="$("$(ac_bin date)" +%s)"
    ((now - mtime <= max))
}

cache_ensure() {
    [[ "${AC_NO_AUTO_CACHE:-0}" == 1 ]] && return 0
    cache_is_fresh || cache_rebuild
}

cache_names() {
    local min="${AC_CACHE_MIN_COUNT:-1}" file name count
    file="$(cache_file)"
    [[ -f "$file" ]] || return 0
    while IFS=$'\t' read -r name count; do
        [[ -n "$name" ]] || continue
        ((count >= min)) && printf '%s\n' "$name"
    done < "$file"
}

is_cached_command() {
    local wanted="$1" name
    while IFS= read -r name; do
        [[ "$name" == "$wanted" ]] && return 0
    done < <(cache_names)
    return 1
}

cache_add() {
    local name="$1" dir file tmp path line cmd count
    is_valid_command_name "$name" || return 1
    dir="$(cache_dir)"
    mkdir -p "$dir" || return 1
    file="$(cache_file)"
    tmp="$file.tmp.$$"

    _cache_lock open
    local -A counts=()
    if [[ -f "$file" ]]; then
        while IFS=$'\t' read -r cmd count; do
            [[ -n "$cmd" ]] && counts["$cmd"]="${count:-0}"
        done < "$file"
    fi
    counts["$name"]=$(( ${counts["$name"]:-0} + 1 ))

    {
        for cmd in "${!counts[@]}"; do
            printf '%s\t%s\n' "$cmd" "${counts[$cmd]}"
        done
    } | LC_ALL=C "$(ac_bin sort)" -t $'\t' -k2,2nr -k1,1 > "$tmp"
    mv -f "$tmp" "$file"
    _cache_lock close
}

cache_stats() {
    local file n=0 name sources=0 path
    file="$(cache_file)"
    while IFS= read -r name; do [[ -n "$name" ]] && ((n++)); done < <(cache_names)
    local IFS=':'
    local -a paths=()
    read -r -a paths <<< "$(ac_history_files)"
    for path in "${paths[@]}"; do [[ -f "$path" && -r "$path" ]] && ((sources++)); done
    printf 'commands=%s sources=%s path=%s\n' "$n" "$sources" "$file"
}

cache_clear() {
    rm -f "$(cache_file)"
}
