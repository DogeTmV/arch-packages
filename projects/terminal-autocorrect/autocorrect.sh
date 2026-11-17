#!/usr/bin/env bash
# terminal-autocorrect - conservative command typo correction for fish.
#
# This file is the single entry point. Shell glue talks to `check` and
# `sudo`; humans use `explain`, `candidates`, `cache`, `version` and `help`.

set -uo pipefail

AC_VERSION='2.0.0'
AC_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AC_ROOT

for _lib in system distance candidates common cache policy; do
    source "$AC_ROOT/lib/$_lib.sh"
done
unset _lib

usage() {
    cat <<'EOF'
terminal-autocorrect - conservative command typo correction for fish

Usage:
  autocorrect.sh check <typed> [args...]   Decide about an unknown command
  autocorrect.sh sudo <target> [args...]   Decide about sudo's target
  autocorrect.sh explain <typed> [args...] Human-readable decision report
  autocorrect.sh candidates <typed>        List close command names
  autocorrect.sh cache <action> [name]     Manage recent-command cache
                 actions: rebuild, ensure, list, stats, add, add-line,
                          clear, path
  autocorrect.sh version                   Print version
  autocorrect.sh help                      Print this help

Output of check/sudo is one tab-separated line:
  RUN<TAB><command>            silently replace only the command token
  SUGGEST<TAB><cmd1><TAB>...   show alternatives, run nothing
  NONE                         no confident correction
EOF
}

cmd_candidates() {
    local typed="${1:-}" cand d max="${AC_MAX_SUGGEST_DIST:-2}"
    is_valid_command_name "$typed" || return 0
    while IFS= read -r cand; do
        [[ "$cand" == "$typed" ]] && continue
        d="$(distance_at_most "$typed" "$cand" "$max")"
        ((d <= max)) && printf '%s\t%s\n' "$cand" "$d"
    done < <(collect_all_candidates)
}

cmd_cache() {
    local action="${1:-stats}" name="${2:-}"
    case "$action" in
        rebuild) cache_rebuild; cache_stats ;;
        ensure) cache_ensure; cache_stats ;;
        list) cache_names ;;
        stats) cache_stats ;;
        add)
            if [[ -z "$name" ]]; then printf 'cache add needs a command name\n' >&2; return 2; fi
            cache_add "$name"
            ;;
        add-line)
            if [[ -z "$name" ]]; then printf 'cache add-line needs a command line\n' >&2; return 2; fi
            local base
            base="$(base_command_from_line "$name")"
            [[ -n "$base" ]] && cache_add "$base"
            ;;
        clear) cache_clear ;;
        path) cache_file ;;
        *) printf 'unknown cache action: %s\n' "$action" >&2; return 2 ;;
    esac
}

mode="${1:-check}"
case "$mode" in
    -h|--help|help) usage ;;
    -v|--version|version) printf '%s\n' "$AC_VERSION" ;;
    check)
        shift
        policy_analyze "${1:-}" "${@:2}"
        policy_emit
        ;;
    sudo)
        shift
        policy_analyze_sudo "${1:-}" "${@:2}"
        policy_emit
        ;;
    explain)
        shift
        policy_explain "${1:-}" "${@:2}"
        ;;
    candidates)
        shift
        cmd_candidates "${1:-}"
        ;;
    cache)
        shift
        cmd_cache "$@"
        ;;
    *)
        printf 'unknown mode: %s\n' "$mode" >&2
        usage >&2
        exit 2
        ;;
esac
