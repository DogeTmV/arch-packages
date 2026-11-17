# Architecture

## Data flow

```
fish command line
   |
   | unknown first token  -----> fish_command_not_found
   | `sudo <unknown>`     -----> sudo wrapper
   v
__ac_query (fish)  --- sets AC_EXTRA_CANDIDATES from fish builtins
   |
   v
autocorrect.sh (bash)
   |
   +--> lib/system.sh      resolves external tools from fixed system paths
   +--> lib/distance.sh    Damerau-Levenshtein (transpositions cost 1)
   +--> lib/candidates.sh  PATH executables + fish builtins, filtered/deduped
   +--> lib/common.sh      curated common-command list
   +--> lib/cache.sh       recently used commands from local shell history
   +--> lib/policy.sh      trust + sudo + dangerous-command rules
   |
   v
one output line: RUN<TAB>cmd | SUGGEST<TAB>cmd<TAB>... | NONE
   |
   v
fish executes only the corrected command name with the ORIGINAL arguments
```

## Trust tiers

| Tier | Source | Auto-run allowed? |
| --- | --- | --- |
| Trusted | recent-command cache (`AC_CACHE_MIN_COUNT`) | Yes, when unique and one edit away |
| Trusted | `share/common-commands.txt` | Yes, when unique and one edit away |
| Extra trusted | `AC_TRUST_EXTRA` | Yes, when unique and one edit away |
| Untrusted | PATH executables / fish builtins | No — suggestion only |
| Blocked | `share/dangerous-commands.txt` or `AC_NEVER_AUTO` | No — suggestion only |

sudo usage forces suggestion mode for every target except `pacman`, which is
the explicit exception requested by the user.

## Decision order in `lib/policy.sh`

1. Reject empty/invalid command tokens.
2. Collect all candidates and compute bounded edit distance (max 2 by
   default).
3. Prefer distance-1 matches; fall back to distance-2 matches for inputs of
   at least `AC_MIN_LEN_FOR_D2` characters. Distance-2 matches can never be
   auto-run.
4. Apply the sudo rule.
5. Apply the dangerous-command block.
6. Apply the trust check.
7. Only if exactly one distance-1 candidate survives is `RUN` emitted.

## Cache format

`~/.cache/terminal-autocorrect/commands.tsv`:

```
ls	42
git	31
mytool	2
```

- Written via temporary file + `mv`, under `flock` when available.
- Rebuilt from local shell history when missing or older than
  `AC_CACHE_MAX_AGE` (default 86400 seconds).
- Updated on every interactive command via fish's `fish_postexec` event;
  only the base command name is recorded.

## Base-only correction guarantee

The engine emits a command **name** only. Fish reuses `$argv[2..-1]`
unchanged. No code path constructs a replacement argument list, so
`pakman -Syu extra` becomes `pacman -Syu extra`, never
`pacman -S <something>`. This is asserted in both the CLI and fish
integration tests.

## Safety against PATH interference

A command named `grep` or `sort` earlier in `PATH` must not be able to
influence a trust decision. Therefore:

- `lib/system.sh` resolves `sort`, `stat`, `date`, etc. from
  `AC_SYSTEM_PATH` (`/usr/bin:/bin:/usr/sbin:/sbin` by default).
- Membership checks (`is_common_command`, `is_cached_command`,
  `is_never_auto`) are implemented in pure bash.

A regression test installs a fake `grep` and confirms corrections still
work.

## Non-goals

- Correcting file names or arguments.
- Reading other users' history or requiring elevated permissions.
- Modifying your shell configuration without an explicit install step.
