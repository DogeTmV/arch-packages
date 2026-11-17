#!/usr/bin/env bash
# String distance helpers.
#
# We use optimal string alignment (restricted Damerau-Levenshtein): insert,
# delete, substitute, and adjacent transposition each cost 1. This makes
# "sl" -> "ls" a single typo, which is what terminal autocorrect needs.

# Print the edit distance between two strings.
damerau_levenshtein() {
    local s="$1" t="$2"
    local m="${#s}" n="${#t}"

    if ((m == 0)); then printf '%s\n' "$n"; return; fi
    if ((n == 0)); then printf '%s\n' "$m"; return; fi

    local -a d0 d1 d2
    local i j cost v
    for ((j = 0; j <= n; j++)); do d0[j]="$j"; done

    for ((i = 1; i <= m; i++)); do
        d1[0]="$i"
        for ((j = 1; j <= n; j++)); do
            cost=1
            [[ "${s:i-1:1}" == "${t:j-1:1}" ]] && cost=0
            v="$((d0[j-1] + cost))"
            ((d0[j] + 1 < v)) && v="$((d0[j] + 1))"
            ((d1[j-1] + 1 < v)) && v="$((d1[j-1] + 1))"
            if ((i > 1 && j > 1)) &&
               [[ "${s:i-1:1}" == "${t:j-2:1}" && "${s:i-2:1}" == "${t:j-1:1}" ]]; then
                ((d2[j-2] + 1 < v)) && v="$((d2[j-2] + 1))"
            fi
            d1[j]="$v"
        done
        for ((j = 0; j <= n; j++)); do
            d2[j]="${d0[j]}"
            d0[j]="${d1[j]}"
        done
    done
    printf '%s\n' "${d0[n]}"
}

# Like damerau_levenshtein, but skips the DP entirely when the length
# difference alone proves the distance exceeds $3. Returns max+1 in that
# case, which callers can compare without special handling.
distance_at_most() {
    local s="$1" t="$2" max="$3"
    local m="${#s}" n="${#t}"
    local diff=$((m > n ? m - n : n - m))
    if ((diff > max)); then
        printf '%s\n' "$((max + 1))"
        return
    fi
    local d
    d="$(damerau_levenshtein "$s" "$t")"
    if ((d > max)); then
        printf '%s\n' "$((max + 1))"
    else
        printf '%s\n' "$d"
    fi
}
