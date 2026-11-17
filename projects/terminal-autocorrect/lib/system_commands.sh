#!/usr/bin/env bash
# System-wide command discovery.
#
# Builds a cached list of every command name we can find locally:
#   * system bin/sbin directories (and PATH)
#   * files owned by installed packages (pacman-style file lists)
#   * fish function and completion names
# The list is used only as suggestion candidates. Trust is still decided by
# lib/policy.sh; discovering a command never makes it safe to auto-run.

if ! declare -F ac_bin >/dev/null 2>&1; then
    source "$(dirname "${BASH_SOURCE[0]}")/system.sh"
fi

_system_commands_dir() {
    printf '%s\n' "${AC_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/terminal-autocorrect}"
}

system_commands_cache_file() {
    printf '%s\n' "$(_system_commands_dir)/system-commands.txt"
}

_system_lock() {
    local op="$1"
    command -v flock >/dev/null 2>&1 || return 0
    if [[ "$op" == open ]]; then
        mkdir -p "$(_system_commands_dir)"
        exec 8>"$(_system_commands_dir)/.system.lock"
        flock -x 8
    else
        flock -u 8 2>/dev/null || true
        exec 8>&- 2>/dev/null || true
    fi
}

_system_command_dirs() {
    if [[ -n "${AC_SYSTEM_COMMAND_DIRS:-}" ]]; then
        printf '%s\n' "$AC_SYSTEM_COMMAND_DIRS"
        return
    fi
    local dirs='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
    if [[ -n "${PATH:-}" ]]; then
        dirs="$dirs:$PATH"
    fi
    printf '%s\n' "$dirs"
}

_scan_executable_dirs() {
    local dir entry name
    local IFS=':'
    local -a dirs=()
    read -r -a dirs <<< "$(_system_command_dirs)"
    for dir in "${dirs[@]}"; do
        [[ -n "$dir" && -d "$dir" ]] || continue
        for entry in "$dir"/*; do
            [[ -e "$entry" && ! -d "$entry" && -x "$entry" ]] || continue
            name="${entry##*/}"
            is_valid_command_name "$name" && printf '%s\n' "$name"
        done
    done
}

_package_file_lines() {
    if [[ -n "${AC_PACKAGE_FILE_LIST:-}" ]]; then
        [[ -r "$AC_PACKAGE_FILE_LIST" ]] || return 0
        "$(ac_bin cat)" "$AC_PACKAGE_FILE_LIST"
        return
    fi

    # Arch: every file owned by every installed package. Read-only and runs
    # as the current user.
    if command -v pacman >/dev/null 2>&1; then
        pacman -Qlq 2>/dev/null || true
    fi
    # Debian-style fallback for completeness on other systems.
    if command -v dpkg-query >/dev/null 2>&1; then
        dpkg-query -W -f='${db:Status-Abbrev}\t${Package}\n' 2>/dev/null |
            while IFS=$'\t' read -r status pkg; do
                [[ "$status" == ii* ]] || continue
                dpkg-query -L "$pkg" 2>/dev/null || true
            done
    fi
}

_scan_package_files() {
    local path name
    while IFS= read -r path || [[ -n "$path" ]]; do
        path="${path%$'\r'}"
        case "$path" in
            */bin/*|*/sbin/*) ;;
            *) continue ;;
        esac
        name="${path##*/}"
        is_valid_command_name "$name" && printf '%s\n' "$name"
    done < <(_package_file_lines)
}

_fish_name_dirs() {
    local kind="$1"
    if [[ "$kind" == functions ]]; then
        if [[ -n "${AC_FISH_FUNCTIONS_DIR:-}" ]]; then
            printf '%s\n' "$AC_FISH_FUNCTIONS_DIR"
            return
        fi
        printf '%s\n' \
            "${XDG_CONFIG_HOME:-$HOME/.config}/fish/functions" \
            '/usr/share/fish/functions' \
            '/usr/local/share/fish/functions'
    else
        if [[ -n "${AC_FISH_COMPLETIONS_DIR:-}" ]]; then
            printf '%s\n' "$AC_FISH_COMPLETIONS_DIR"
            return
        fi
        printf '%s\n' \
            "${XDG_CONFIG_HOME:-$HOME/.config}/fish/completions" \
            '/usr/share/fish/completions' \
            '/usr/local/share/fish/completions'
    fi
}

_scan_fish_names() {
    local kind dir entry name
    for kind in functions completions; do
        while IFS= read -r dir; do
            [[ -n "$dir" && -d "$dir" ]] || continue
            for entry in "$dir"/*.fish; do
                [[ -f "$entry" ]] || continue
                name="${entry##*/}"
                name="${name%.fish}"
                is_valid_command_name "$name" && printf '%s\n' "$name"
            done
        done < <(_fish_name_dirs "$kind")
    done
}

system_commands_rebuild() {
    local dir file tmp
    dir="$(_system_commands_dir)"
    mkdir -p "$dir" || return 1
    file="$(system_commands_cache_file)"
    tmp="$file.tmp.$$"

    _system_lock open
    {
        _scan_executable_dirs
        _scan_package_files
        _scan_fish_names
    } | LC_ALL=C "$(ac_bin sort)" -u > "$tmp"
    mv -f "$tmp" "$file"
    _system_lock close
}

system_commands_is_fresh() {
    local file max mtime now
    file="$(system_commands_cache_file)"
    [[ -f "$file" ]] || return 1
    max="${AC_SYSTEM_COMMANDS_MAX_AGE:-604800}"
    ((max > 0)) || return 1
    mtime="$("$(ac_bin stat)" -c %Y "$file" 2>/dev/null)" || return 1
    now="$("$(ac_bin date)" +%s)"
    ((now - mtime <= max))
}

# Build a missing cache. If one exists, refresh it only when stale and
# AC_NO_AUTO_CACHE is not set. This keeps startup cheap while still allowing
# callers to force a rebuild with system_commands_rebuild.
system_commands_ensure() {
    local file
    file="$(system_commands_cache_file)"
    if [[ -f "$file" ]]; then
        if [[ "${AC_NO_AUTO_CACHE:-0}" == 1 ]] || system_commands_is_fresh; then
            return 0
        fi
    fi
    system_commands_rebuild
}

collect_system_command_names() {
    system_commands_ensure || return 0
    local file name
    file="$(system_commands_cache_file)"
    [[ -f "$file" ]] || return 0
    while IFS= read -r name || [[ -n "$name" ]]; do
        [[ -n "$name" ]] && printf '%s\n' "$name"
    done < "$file"
}

system_commands_stats() {
    local file n=0 name
    file="$(system_commands_cache_file)"
    if [[ -f "$file" ]]; then
        while IFS= read -r name; do [[ -n "$name" ]] && ((n++)); done < "$file"
    fi
    printf 'commands=%s path=%s max_age=%s\n' \
        "$n" "$file" "${AC_SYSTEM_COMMANDS_MAX_AGE:-604800}"
}
