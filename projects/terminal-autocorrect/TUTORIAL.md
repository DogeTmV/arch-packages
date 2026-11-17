# Installation tutorial

This walks through installing, verifying, configuring, and removing
terminal-autocorrect. Every command below runs as your normal user. Nothing
needs `sudo`, root, or elevated permissions.

## 1. Check the prerequisites

You need:

- **fish 3.5 or newer** (the glue uses the `path` builtin). Check with:

  ```sh
  fish --version
  ```

- **bash 4 or newer** (the decision engine is a bash script):

  ```sh
  bash --version | head -n 1
  ```

- Standard userland tools (`sort`, `stat`, `date`). The program resolves
  these from `/usr/bin` and `/bin`, so a command earlier in your `PATH`
  cannot interfere with safety decisions.
- `flock` is optional. When present, concurrent shells cannot corrupt the
  cache. Without it, the cache still uses atomic rename.

## 2. Look around before installing

From the project directory:

```sh
bash autocorrect.sh version
bash autocorrect.sh explain lss
bash autocorrect.sh explain lst
bash autocorrect.sh candidates pakman
```

`explain` shows exactly what the program would do and why, without running
anything. You can also run the whole suite first:

```sh
bash tests/run_all.sh
```

## 3. Install

```sh
bash install.sh
```

The installer creates:

```
~/.config/fish/autocorrect/
├── autocorrect.sh
├── fish_integration.fish
├── lib/
│   ├── system.sh
│   ├── distance.sh
│   ├── candidates.sh
│   ├── common.sh
│   ├── cache.sh
│   └── policy.sh
└── share/
    ├── common-commands.txt
    └── dangerous-commands.txt
~/.config/fish/conf.d/autocorrect.fish
```

The `conf.d` file is a one-line loader that fish sources automatically.
Re-running `install.sh` is safe: it refreshes the files and does not create
duplicate loader lines.

To install somewhere else:

```sh
AC_FISH_CONFIG_DIR=/path/to/fish bash install.sh
```

## 4. Verify in a fresh fish shell

Start a new fish shell (or `source ~/.config/fish/conf.d/autocorrect.fish`),
then check that the hooks are loaded:

```fish
functions -q fish_command_not_found; and echo hook-ok
functions -q sudo; and echo sudo-ok
functions -q __ac_record_command; and echo recorder-ok
```

Now try a few commands:

```fish
lss                 # runs `ls` silently (trusted common command)
lst                 # suggests `last, ls`; runs nothing
pakman -Syu         # runs `pacman -Syu` (only the command name is corrected)
sduo pacman -Syu    # runs `sudo pacman -Syu`
sduo apt update     # suggests `sudo`; runs nothing
sudo grpe file      # suggests `grep`; runs nothing
```

If a command is not installed locally it may not be a candidate at all;
`bash autocorrect.sh candidates <word>` shows the candidates the engine
currently sees.

## 5. Understand the cache

The first time a shell starts, the program builds a cache of recently used
commands from your local history files:

- `~/.local/share/fish/fish_history`
- `~/.config/fish/fish_history`
- `~/.bash_history`
- `~/.zsh_history` (and `$ZDOTDIR/.zsh_history`)

Every command you run afterwards is recorded automatically via fish's
`fish_postexec` event. Only the **base command name** is stored: `sudo pacman
-Syu` records `pacman`.

Inspect and manage it:

```sh
bash autocorrect.sh cache stats
bash autocorrect.sh cache list
bash autocorrect.sh cache rebuild
bash autocorrect.sh cache add mytool
bash autocorrect.sh cache clear
```

Cache entries are `name<TAB>count` lines. By default any command seen at
least once is trusted. To require more evidence, set:

```fish
set -gx AC_CACHE_MIN_COUNT 2
```

The cache is considered fresh for 24 hours. Change that with:

```fish
set -gx AC_CACHE_MAX_AGE 3600   # seconds
```

## 6. Trust rules (why some typos are only suggested)

A typo is auto-run **only** when all of these are true:

1. exactly one candidate is one edit away (swapped letters count as one),
2. that candidate is either in the cache or in `share/common-commands.txt`,
3. it is not listed in `share/dangerous-commands.txt`,
4. no `sudo` usage is involved — except a `pacman` target.

Everything else prints `Did you mean: ...` and runs nothing. This applies to
two-edit typos, ambiguous typos, untrusted commands, and dangerous commands.
Commands shaped like `sudo -u user command` are passed straight through to the
real `sudo`, since the wrapper intentionally skips sudo option prefixes.

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

## 7. Troubleshooting

**No corrections happen.** Run `bash autocorrect.sh explain lss`. If the
reason is `candidate is not trusted`, add the command to the cache with
`cache add` or to your common list. If it is `no close candidate`, check
`bash autocorrect.sh candidates lss`.

**Too many suggestions.** Lower `AC_MAX_SUGGESTIONS` (default 5), or raise
`AC_MIN_LEN_FOR_D2` (default 4) to suppress two-edit suggestions for short
words.

**A command is suggested but never auto-corrected.** Check
`share/dangerous-commands.txt` and `AC_NEVER_AUTO`.

**The `sudo` wrapper conflicts with another tool.** Check whether another
function named `sudo` is defined (`functions sudo`). Load this project after
that tool, or remove the conflicting function.

**Shell startup feels slow.** The cache refresh happens once per shell and
is normally milliseconds. Set `AC_NO_AUTO_CACHE=1` to skip automatic rebuilds
and refresh manually with `bash autocorrect.sh cache rebuild`.

**Running the tests touches my config.** It does not. Every test uses a
fresh temp directory and overrides `HOME`, `XDG_*`, `AC_CACHE_DIR`,
`AC_HISTORY_FILES`, and `AC_FISH_CONFIG_DIR`.

## 8. Uninstall

```sh
bash uninstall.sh
```

Then restart fish. This removes only `~/.config/fish/autocorrect/` and
`~/.config/fish/conf.d/autocorrect.fish`; the rest of your configuration is
left alone. The recent-command cache under `~/.cache/terminal-autocorrect/`
is also left alone and can be removed manually if you want.
