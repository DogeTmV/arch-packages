# Installation tutorial

This walks through installing, verifying, configuring, and removing
terminal-autocorrect. Every command below runs as your normal user. Nothing
needs `sudo`, root, or elevated permissions.

## 1. Check the prerequisites

You need:

- **fish 3.5 or newer** (the glue uses the `path` builtin):

  ```sh
  fish --version
  ```

- **bash 4 or newer** (the decision engine is a bash script):

  ```sh
  bash --version | head -n 1
  ```

- Standard userland tools (`sort`, `stat`, `date`). The program resolves them
  from `/usr/bin` and `/bin`, so a command earlier in your `PATH` cannot
  interfere with safety decisions.
- `flock` is optional. When present, concurrent shells cannot corrupt either
  cache. Without it, writes still use atomic rename.

## 2. Look around before installing

From the project directory:

```sh
bash tests/run_all.sh          # 166 isolated tests
bash autocorrect.sh version
bash autocorrect.sh explain lss
bash autocorrect.sh explain lst
bash autocorrect.sh candidates pakman
bash autocorrect.sh system stats
```

`explain` shows exactly what the program would do and why, without running
anything.

## 3. Install — permanently add it to fish

### Option A: fish-native installer (recommended)

From inside fish:

```fish
source /path/to/terminal-autocorrect/install.fish
```

This copies the files, writes the fish loader, and sources it **in the current
fish process**. The hooks are active immediately — there is no manual launch
and no restart needed. New shells load it automatically through
`~/.config/fish/conf.d/autocorrect.fish`.

### Option B: shell installer

```sh
bash install.sh
```

Then either restart fish or run:

```fish
source ~/.config/fish/conf.d/autocorrect.fish
```

Both options create:

```
~/.config/fish/autocorrect/
├── autocorrect.sh
├── fish_integration.fish
├── install.fish
├── lib/
│   ├── system.sh
│   ├── distance.sh
│   ├── candidates.sh
│   ├── common.sh
│   ├── cache.sh
│   ├── ranking.sh
│   ├── system_commands.sh
│   └── policy.sh
└── share/
    ├── common-commands.txt
    ├── dangerous-commands.txt
    ├── popular-commands.txt
    └── config.example.env
~/.config/fish/conf.d/autocorrect.fish
```

Re-running either installer is safe: files are refreshed and the loader is
not duplicated.

To install somewhere else:

```sh
AC_FISH_CONFIG_DIR=/path/to/fish bash install.sh
```

## 4. Verify in fish

```fish
functions -q fish_command_not_found; and echo hook-ok
functions -q sudo; and echo sudo-ok
functions -q __ac_record_command; and echo recorder-ok
```

Now try:

```fish
grpe file           # runs grep file silently (trusted common command)
lss                 # suggests ls/less/ss with the full system base
pakman -Syu         # runs pacman -Syu (only the command name is corrected)
sduo pacman -Syu    # runs sudo pacman -Syu
sduo apt update     # suggests sudo; runs nothing
sudo grpe file      # suggests grep; runs nothing
```

## 5. Whole-system command discovery

By default the program builds a cached list of command names from:

- `/usr/local/sbin`, `/usr/local/bin`, `/usr/sbin`, `/usr/bin`, `/sbin`,
  `/bin`, and your `PATH`,
- files owned by installed packages (`pacman -Qlq`; `dpkg-query` fallback),
  keeping only paths containing `/bin/` or `/sbin/`,
- fish function names from `~/.config/fish/functions` and system fish dirs,
- fish completion names from `~/.config/fish/completions` and system dirs.

The cache lives beside the recent-command cache as `system-commands.txt`.
It is rebuilt when missing or older than one week, unless `AC_NO_AUTO_CACHE=1`
is set (in which case a stale cache is reused). Force a refresh with:

```sh
bash autocorrect.sh system rebuild
bash autocorrect.sh system stats
bash autocorrect.sh system list
```

Discovery only creates **suggestion candidates**. A discovered command is
never trusted for silent correction just because it exists on the system.

To disable discovery entirely:

```fish
set -gx AC_DISCOVER_SYSTEM_COMMANDS 0
```

To restrict scanning to specific directories (for example on a minimal
system):

```fish
set -gx AC_SYSTEM_COMMAND_DIRS /usr/bin:/bin
set -gx AC_PACKAGE_FILE_LIST /nonexistent
```

## 6. Understand the caches

### Recent commands

The first time a shell starts, the program builds a cache of recently used
commands from your local history files:

- `~/.local/share/fish/fish_history`
- `~/.config/fish/fish_history`
- `~/.bash_history`
- `~/.zsh_history` (and `$ZDOTDIR/.zsh_history`)

Every command you run afterwards is recorded automatically via fish's
`fish_postexec` event. Only the **base command name** is stored: `sudo pacman
-Syu` records `pacman`.

```sh
bash autocorrect.sh cache stats
bash autocorrect.sh cache list
bash autocorrect.sh cache rebuild
bash autocorrect.sh cache add mytool
bash autocorrect.sh cache clear
```

Cache entries are `name<TAB>count` lines. By default any command seen at
least once is trusted. To require more evidence:

```fish
set -gx AC_CACHE_MIN_COUNT 2
```

The cache is considered fresh for 24 hours. Change that with:

```fish
set -gx AC_CACHE_MAX_AGE 3600   # seconds
```

### Usage ranking

Suggestions are ordered by:

1. recent-command count,
2. membership in the common-command list,
3. membership in `share/popular-commands.txt`,
4. alphabetical order for ties.

Ranking never grants trust; it only changes which suggestion is shown first.
Customize the boost list with:

```fish
set -gx AC_POPULAR_FILE "$HOME/.config/my-popular-commands.txt"
```

## 7. Trust rules

A typo is auto-run **only** when all of these are true:

1. exactly one candidate is one edit away (swapped letters count as one),
2. that candidate is either in the cache or in `share/common-commands.txt`,
3. it is not listed in `share/dangerous-commands.txt`,
4. no `sudo` usage is involved — except a `pacman` target.

Everything else prints `Did you mean: ...` and runs nothing. This applies to
two- and three-edit typos, similar-name fallbacks, ambiguous typos, untrusted
commands, and dangerous commands. Commands shaped like `sudo -u user command`
are passed straight through to the real `sudo`.

To add your own trusted command without editing the shipped list:

```fish
set -gx AC_TRUST_EXTRA "mytool othertool"
```

To permanently block auto-correction to a command:

```fish
set -gx AC_NEVER_AUTO "deploy prod-deploy"
```

To copy and edit the shipped lists, point the program at your own files:

```fish
set -gx AC_COMMON_FILE "$HOME/.config/my-common-commands.txt"
set -gx AC_DANGEROUS_FILE "$HOME/.config/my-dangerous-commands.txt"
```

Put any `set -gx` lines in `~/.config/fish/config.fish` before the autocorrect
loader runs, or in a separate `conf.d` file whose name sorts before
`autocorrect.fish`.

## 8. Troubleshooting

**No corrections happen.** Run `bash autocorrect.sh explain lss`. If the
reason is `candidate is not trusted`, add the command to the cache with
`cache add` or to your common list. If it is `no close candidate`, check
`bash autocorrect.sh candidates lss` and `bash autocorrect.sh system stats`.

**A command is missing from suggestions.** Rebuild the system base with
`bash autocorrect.sh system rebuild`. If it lives outside the standard dirs,
set `AC_SYSTEM_COMMAND_DIRS` or `AC_PACKAGE_FILE_LIST`.

**Too many suggestions.** Lower `AC_MAX_SUGGESTIONS` (default 8), lower
`AC_MAX_SUGGEST_DIST` (default 3), or raise `AC_MIN_LEN_FOR_D2` (default 4) to
suppress multi-edit and fallback suggestions for short words.

**A command is suggested but never auto-corrected.** Check
`share/dangerous-commands.txt` and `AC_NEVER_AUTO`.

**The `sudo` wrapper conflicts with another tool.** Check whether another
function named `sudo` is defined (`functions sudo`). Load this project after
that tool, or remove the conflicting function.

**Shell startup feels slow.** Set `AC_NO_AUTO_CACHE=1` to skip automatic
refreshes, then update manually with `cache rebuild` / `system rebuild`.

**Running the tests touches my config.** It does not. Every test uses a fresh
temp directory and overrides `HOME`, `XDG_*`, `AC_CACHE_DIR`,
`AC_HISTORY_FILES`, and `AC_FISH_CONFIG_DIR`.

## 9. Uninstall

```sh
bash uninstall.sh
```

Then restart fish. This removes only `~/.config/fish/autocorrect/` and
`~/.config/fish/conf.d/autocorrect.fish`; the rest of your configuration is
left alone. Caches under `~/.cache/terminal-autocorrect/` are also left alone
and can be removed manually if you want.
