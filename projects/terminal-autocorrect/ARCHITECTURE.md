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
   +--> lib/system.sh          resolves external tools from fixed system paths
   +--> lib/distance.sh        Damerau-Levenshtein (transpositions cost 1)
   +--> lib/candidates.sh      PATH + system + fish candidates, filtered/deduped
   +--> lib/system_commands.sh whole-system base (dirs, packages, fish names)
   +--> lib/common.sh          curated common-command list
   +--> lib/cache.sh           recently used commands from local shell history
   +--> lib/ranking.sh         usage-based ordering of suggestions
   +--> lib/policy.sh          trust + sudo + dangerous-command rules
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
| Untrusted | PATH, system dirs, package files, fish builtins/functions | No — suggestion only |
| Boosted only | `share/popular-commands.txt` | No — ordering only, never trust |
| Blocked | `share/dangerous-commands.txt` or `AC_NEVER_AUTO` | No — suggestion only |

sudo usage forces suggestion mode for every target except `pacman`, which is
the explicit exception requested by the user.

## Decision order in `lib/policy.sh`

1. Reject empty/invalid command tokens.
2. Collect all candidates from `collect_all_candidates()`.
3. Compute bounded edit distance (max 3 by default).
4. Prefer distance-1 matches, then distance-2, then distance-3. For longer
   typos with no distance match, try a shared-prefix/substring fallback.
   Only distance 1 can ever be auto-run.
5. Rank the matches with `lib/ranking.sh` (usage count, common list, popular
   list, then alphabetical) and truncate to `AC_MAX_SUGGESTIONS`.
6. Apply the sudo rule.
7. Apply the dangerous-command block.
8. Apply the trust check.
9. Only if exactly one distance-1 candidate survives is `RUN` emitted.

## Whole-system command base

`lib/system_commands.sh` builds `system-commands.txt` from:

- standard `bin`/`sbin` directories plus `PATH` (overridable with
  `AC_SYSTEM_COMMAND_DIRS`),
- package-owned file lists (`pacman -Qlq`, dpkg fallback, or
  `AC_PACKAGE_FILE_LIST`). Only paths containing `/bin/` or `/sbin/` are used;
  documentation and other files are ignored,
- fish function and completion `.fish` filenames from user/system dirs.

The cache is written with temp-file + `mv` under a separate `flock`, and is
refreshed when missing or stale unless `AC_NO_AUTO_CACHE=1` is set. Running
`system rebuild` forces a refresh.

These names are suggestion candidates only. Discovery never changes trust.

## Caches

`~/.cache/terminal-autocorrect/commands.tsv`:

```
ls	42
git	31
mytool	2
```

`~/.cache/terminal-autocorrect/system-commands.txt`:

```
bash
curl
git
...
```

- Recent-command cache rebuilt from local shell history when missing or older
  than `AC_CACHE_MAX_AGE` (default 86400 seconds).
- Updated on every interactive command via fish's `fish_postexec` event; only
  the base command name is recorded.
- System base refreshed based on `AC_SYSTEM_COMMANDS_MAX_AGE` (default 604800
  seconds), and forced with `autocorrect.sh system rebuild`.

## Ranking

`usage_score(name)` is:

```
recent_count * 10
+ 1000 if the name is in the common-command list
+ 500  if the name is in the popular-command list
```

Higher scores sort first; ties are alphabetical. Ranking affects only the
order of `SUGGEST` output and `candidates` output. It cannot enable auto-run.

## Base-only correction guarantee

The engine emits a command **name** only. Fish reuses `$argv[2..-1]`
unchanged. No code path constructs a replacement argument list, so
`pakman -Syu extra` becomes `pacman -Syu extra`, never
`pacman -S <something>`. This is asserted in both the CLI and fish
integration tests.

## Safety against PATH interference

A command named `grep` or `sort` earlier in `PATH` must not be able to
influence a trust decision. Therefore:

- `lib/system.sh` resolves `sort`, `stat`, `date`, `cat`, etc. from
  `AC_SYSTEM_PATH` (`/usr/bin:/bin:/usr/sbin:/sbin` by default).
- Membership checks (`is_common_command`, `is_cached_command`,
  `is_never_auto`, `is_popular_command`) are implemented in pure bash.

A regression test installs a fake `grep` and confirms corrections still
work.

## Installer

- `install.sh` copies the program and writes `conf.d/autocorrect.fish`.
- `install.fish` calls `install.sh` and then sources that loader in the
  current fish process, so hooks are active without a restart.
- `uninstall.sh` removes only the files created by the installer.

## Non-goals

- Correcting file names or arguments.
- Reading other users' history or requiring elevated permissions.
- Modifying your shell configuration without an explicit install step.
