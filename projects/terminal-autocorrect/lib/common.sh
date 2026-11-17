#!/usr/bin/env bash
# Curated list of commonly used commands. These are "trusted" candidates:
# a unique one-edit typo matching one of these may be corrected silently.

if ! declare -F is_valid_command_name >/dev/null 2>&1; then
    source "$(dirname "${BASH_SOURCE[0]}")/candidates.sh"
fi
if ! declare -F ac_bin >/dev/null 2>&1; then
    source "$(dirname "${BASH_SOURCE[0]}")/system.sh"
fi

_AC_FALLBACK_COMMON='ls pwd cd cat head tail grep sed awk find touch mkdir cp mv rm ln sort uniq wc cut tr tee xargs diff patch tar gzip unzip git make python python3 pip npm node cargo go vim nano less man echo printf sleep date time ps top kill systemctl journalctl curl wget ssh scp rsync chmod chown sudo pacman apt apt-get dnf apk bash fish zsh sh'

common_commands() {
    local file="${AC_COMMON_FILE:-${AC_ROOT:-}/share/common-commands.txt}"
    local -a names=()
    local line name

    if [[ -r "$file" ]]; then
        while IFS= read -r line || [[ -n "$line" ]]; do
            line="${line%%#*}"
            line="${line//$'\t'/ }"
            line="${line//$'\r'/ }"
            for name in $line; do
                is_valid_command_name "$name" && names+=("$name")
            done
        done < "$file"
    else
        read -r -a names <<< "$_AC_FALLBACK_COMMON"
    fi

    if ((${#names[@]} > 0)); then
        printf '%s\n' "${names[@]}" | LC_ALL=C "$(ac_bin sort)" -u
    fi
}

is_common_command() {
    local wanted="$1" name
    while IFS= read -r name; do
        [[ "$name" == "$wanted" ]] && return 0
    done < <(common_commands)
    return 1
}
