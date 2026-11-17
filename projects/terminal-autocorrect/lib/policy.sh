#!/usr/bin/env bash
# Decision policy. This is the safety boundary of the whole program.
#
# A command is auto-run only when ALL of these hold:
#   * exactly one candidate is one edit away
#   * that candidate is trusted (recently used cache or common-command list)
#   * it is not on the never-auto list
#   * no sudo usage is involved (except a pacman target)
# Everything else becomes a suggestion, never an execution.

for _lib in system distance candidates common cache ranking system_commands; do
    if ! declare -F "$(case "$_lib" in
        distance) echo damerau_levenshtein ;;
        candidates) echo is_valid_command_name ;;
        common) echo common_commands ;;
        cache) echo cache_names ;;
        ranking) echo usage_score ;;
        system_commands) echo collect_system_command_names ;;
        system) echo ac_bin ;;
    esac)" >/dev/null 2>&1; then
        source "$(dirname "${BASH_SOURCE[0]}")/$_lib.sh"
    fi
done
unset _lib

declare -g AC_DECISION='NONE'
declare -g AC_CORRECTION=''
declare -g AC_MATCHES=''
declare -g AC_REASON=''
declare -g AC_DISTANCE=0
declare -g AC_MATCH_KIND=''

_dangerous_file() {
    printf '%s\n' "${AC_DANGEROUS_FILE:-${AC_ROOT:-}/share/dangerous-commands.txt}"
}

is_never_auto() {
    local wanted="$1" file path
    file="$(_dangerous_file)"
    ac_file_contains_line "$wanted" "$file" && return 0
    local -a extra=()
    read -r -a extra <<< "${AC_NEVER_AUTO:-}"
    ac_list_contains "$wanted" "${extra[@]}"
}

is_trusted_command() {
    local wanted="$1" extra_name
    is_cached_command "$wanted" && return 0
    is_common_command "$wanted" && return 0
    local -a extra=()
    read -r -a extra <<< "${AC_TRUST_EXTRA:-}"
    for extra_name in "${extra[@]}"; do
        [[ "$extra_name" == "$wanted" ]] && return 0
    done
    return 1
}

_policy_is_sudoish() {
    local token="$1" len d
    [[ "$token" == sudo ]] && return 0
    len="${#token}"
    ((len >= 3 && len <= 5)) || return 1
    d="$(distance_at_most "$token" sudo 1)"
    ((d == 1))
}

# Sets AC_SUDO_TARGET if any token is sudo or a one-edit typo of it.
_policy_sudo_context() {
    local -a tokens=("$@")
    local i
    AC_SUDO_TARGET=''
    for ((i = 0; i < ${#tokens[@]}; i++)); do
        if _policy_is_sudoish "${tokens[i]}"; then
            AC_SUDO_TARGET="${tokens[i+1]:-}"
            return 0
        fi
    done
    return 1
}

# Fallback for typos too distant for the bounded edit-distance search.
# Shared prefixes and substrings catch cases like `zzgitstatuszz` -> `git`
# without ever making them eligible for automatic execution.
_policy_is_similar() {
    local typed="$1" cand="$2" prefixlen="$3"
    # Ignore one/two-letter substrings: they match almost everything and
    # would drown out the real suggestion.
    ((${#typed} >= prefixlen && ${#cand} > prefixlen)) || return 1
    [[ "${typed:0:prefixlen}" == "${cand:0:prefixlen}" ]] && return 0
    [[ "$typed" == *"$cand"* || "$cand" == *"$typed"* ]] && return 0
    return 1
}

# Core analysis. $1 is the command token to correct; $2 is 1 when privileged
# execution forces a suggestion.
policy_analyze_base() {
    local typed="$1" force="${2:-0}"
    local maxdist="${AC_MAX_SUGGEST_DIST:-3}"
    local minlen="${AC_MIN_LEN_FOR_D2:-4}"
    local limit="${AC_MAX_SUGGESTIONS:-8}"
    local prefixlen="${AC_SIMILAR_PREFIX_LEN:-2}"
    local -a all_candidates=() d1=() d2=() d3=() matches=() similar=()
    local cand d joined=''

    AC_DECISION='NONE'
    AC_CORRECTION=''
    AC_MATCHES=''
    AC_REASON=''
    AC_DISTANCE=0
    AC_MATCH_KIND=''

    cache_ensure || true
    is_valid_command_name "$typed" || { AC_REASON='invalid command token'; return; }

    while IFS= read -r cand; do
        all_candidates+=("$cand")
    done < <(collect_all_candidates)

    for cand in "${all_candidates[@]}"; do
        [[ "$cand" == "$typed" ]] && continue
        d="$(distance_at_most "$typed" "$cand" "$maxdist")"
        case "$d" in
            1) d1+=("$cand") ;;
            2) d2+=("$cand") ;;
            3) d3+=("$cand") ;;
        esac
    done

    if ((${#d1[@]} > 0)); then
        matches=("${d1[@]}")
        AC_DISTANCE=1
        AC_MATCH_KIND='one-edit'
    elif ((${#d2[@]} > 0)) && ((${#typed} >= minlen)); then
        matches=("${d2[@]}")
        AC_DISTANCE=2
        AC_MATCH_KIND='two-edit'
    elif ((${#d3[@]} > 0)) && ((${#typed} >= minlen)); then
        matches=("${d3[@]}")
        AC_DISTANCE=3
        AC_MATCH_KIND='three-edit'
    else
        if ((${#typed} >= minlen)); then
            for cand in "${all_candidates[@]}"; do
                [[ "$cand" == "$typed" ]] && continue
                _policy_is_similar "$typed" "$cand" "$prefixlen" && similar+=("$cand")
            done
        fi
        if ((${#similar[@]} > 0)); then
            matches=("${similar[@]}")
            AC_DISTANCE=4
            AC_MATCH_KIND='similar'
        else
            AC_REASON='no close candidate'
            return
        fi
    fi

    # Usage ranking changes only the order shown to the user. It can never
    # make an untrusted or distant match eligible for automatic execution.
    if ((${#matches[@]} > 0)); then
        mapfile -t matches < <(printf '%s\n' "${matches[@]}" | rank_matches)
    fi
    if ((${#matches[@]} > limit)); then
        matches=("${matches[@]:0:limit}")
    fi
    AC_MATCHES="$(IFS=$'\t'; printf '%s' "${matches[*]}")"

    if ((AC_DISTANCE != 1)); then
        AC_DECISION='SUGGEST'
        case "$AC_DISTANCE" in
            2) AC_REASON='distance two suggestion' ;;
            3) AC_REASON='distance three suggestion' ;;
            4) AC_REASON='similar command suggestion' ;;
        esac
        return
    fi
    if ((${#d1[@]} > 1)); then
        AC_DECISION='SUGGEST'
        AC_REASON='multiple close commands'
        return
    fi

    cand="${d1[0]}"
    if ((force)); then
        AC_DECISION='SUGGEST'
        AC_REASON='sudo requires confirmation'
        return
    fi
    if is_never_auto "$cand"; then
        AC_DECISION='SUGGEST'
        AC_REASON='dangerous command requires confirmation'
        return
    fi
    if ! is_trusted_command "$cand"; then
        AC_DECISION='SUGGEST'
        AC_REASON='candidate is not trusted'
        return
    fi

    AC_DECISION='RUN'
    AC_CORRECTION="$cand"
    AC_REASON='unique trusted one-edit match'
}

# Hook for an unknown command: $1 is the missing command, the rest are args.
policy_analyze() {
    local typed="$1" force=0
    shift || true
    if _policy_sudo_context "$typed" "$@"; then
        [[ "$AC_SUDO_TARGET" == pacman ]] || force=1
    fi
    policy_analyze_base "$typed" "$force"
}

# Hook for a correctly typed `sudo`: $1 is the command sudo would execute.
policy_analyze_sudo() {
    local target="$1"
    shift || true
    policy_analyze_base "$target" 0
    if [[ "$AC_DECISION" == RUN && "$AC_CORRECTION" != pacman ]]; then
        AC_DECISION='SUGGEST'
        AC_CORRECTION=''
        AC_REASON='sudo requires confirmation'
    fi
}

policy_emit() {
    case "$AC_DECISION" in
        RUN) printf 'RUN\t%s\n' "$AC_CORRECTION" ;;
        SUGGEST) printf 'SUGGEST\t%s\n' "$AC_MATCHES" ;;
        *) printf 'NONE\n' ;;
    esac
}

policy_explain() {
    policy_analyze "$@"
    printf 'command: %s\ndecision: %s\ncorrection: %s\ncandidates: %s\ndistance: %s\nkind: %s\nreason: %s\n' \
        "${1:-}" "$AC_DECISION" "$AC_CORRECTION" "$AC_MATCHES" "$AC_DISTANCE" "$AC_MATCH_KIND" "$AC_REASON"
}
