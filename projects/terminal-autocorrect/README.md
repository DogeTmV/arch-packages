# terminal-autocorrect

Conservative, test-driven command typo correction for **fish**. It hooks into
fish's command-not-found mechanism, so there is no new command to remember.

A typo is **auto-run** only when the intended command is one edit away, unique,
and trusted (recently used or in the curated common-command list). Everything
else becomes a suggestion. Corrections never touch your arguments.

## Quick start

```sh
bash tests/run_all.sh     # 166 tests, no permissions needed
bash install.sh           # install into ~/.config/fish
```

Or, from inside fish, install **and activate immediately** in the current
shell:

```fish
source /path/to/terminal-autocorrect/install.fish
```

Then:

```fish
grpe file           # runs grep file silently
lss                 # suggests ls/less/ss (ambiguous with the full system base)
pakman -Syu         # runs pacman -Syu (arguments untouched)
sduo apt update     # suggests: sudo
sudo grpe file      # suggests: grep
sudo paman -Syu     # runs sudo pacman -Syu
```

See **[TUTORIAL.md](TUTORIAL.md)** for the full step-by-step installation,
configuration, troubleshooting, and uninstall guide.
See **[ARCHITECTURE.md](ARCHITECTURE.md)** for design and safety details.

## Permanently add it to fish

The installer makes the correction hooks load automatically in **every new
fish shell**. It does not require `sudo` and does not change your existing
shell configuration beyond one loader file.

```sh
# From this project's directory:
bash install.sh
```

That copies the program to `~/.config/fish/autocorrect/` and creates
`~/.config/fish/conf.d/autocorrect.fish`, which fish sources on startup.
Then either restart fish or load it in the current shell:

```fish
source ~/.config/fish/conf.d/autocorrect.fish
```

Fish users can do both steps at once with the native installer:

```fish
source /path/to/terminal-autocorrect/install.fish
```

It runs `install.sh` and then sources the loader into the **current** fish
process, so the hooks work immediately without a restart.

Verify the hooks are active:

```fish
functions -q fish_command_not_found; and echo not-found-hook-ok
functions -q sudo; and echo sudo-hook-ok
functions -q __ac_record_command; and echo recorder-ok
```

There is nothing else to enable. Open a new terminal, type `grpe file`, and
fish will run `grep file` without any extra command. Re-running the installer later
upgrades the installed copy in place. To remove it permanently, run
`bash uninstall.sh` and restart fish.

If you keep fish config in a non-standard location:

```sh
AC_FISH_CONFIG_DIR=/path/to/your/fish bash install.sh
```

## Behavior at a glance

| Situation | Result |
| --- | --- |
| Unique one-edit typo of a trusted command | Corrected and run silently |
| Unique one-edit typo of an untrusted command | Suggestion only |
| Several equally close commands | Usage-ranked suggestion only |
| Two- or three-edit typo | Suggestion only |
| Similar name/prefix fallback | Suggestion only |
| Dangerous command (e.g. `rm`) | Suggestion only |
| `sudo` usage, target is not `pacman` | Suggestion only |
| `sudo pacman` with a mistyped `pacman` | Corrected and run silently |
| No plausible command | fish's usual error |

Examples of "one edit": deletion (`lss` → `ls`), insertion (`paman` →
`pacman`), substitution (`grpe` → `grep`), transposition (`sl` → `ls`).

## Whole-system command base

When enabled, the program builds a cached list of command names from:

- system `bin`/`sbin` directories and `PATH`,
- files owned by installed packages (`pacman -Qlq`, with dpkg fallback),
- fish function and completion names.

This list is used **only for suggestions**. Discovering a command never makes
it trusted enough to auto-run. Ranking uses the recent-command cache, the
curated common list, and `share/popular-commands.txt` so frequently used
commands appear first.

```sh
bash autocorrect.sh system stats
bash autocorrect.sh system list
bash autocorrect.sh system rebuild
bash autocorrect.sh system path
```

Set `AC_DISCOVER_SYSTEM_COMMANDS=0` to keep discovery disabled.

## Recent-command cache

On shell startup the program scans your local fish, bash, and zsh history
files and caches the base command names. Every command you run afterwards is
recorded automatically. Only the command name is stored, never arguments.

```sh
bash autocorrect.sh cache stats
bash autocorrect.sh cache list
bash autocorrect.sh cache rebuild
bash autocorrect.sh cache add mytool
bash autocorrect.sh cache clear
```

## Configuration

Set these in `config.fish` or a `conf.d` file loaded before `autocorrect.fish`.
See [share/config.example.env](share/config.example.env).

| Variable | Default | Purpose |
| --- | --- | --- |
| `AC_CACHE_MIN_COUNT` | `1` | Uses needed before cache entry is trusted |
| `AC_CACHE_MAX_AGE` | `86400` | Recent cache freshness in seconds |
| `AC_NO_AUTO_CACHE` | `0` | Set to `1` to disable automatic refresh |
| `AC_DISCOVER_SYSTEM_COMMANDS` | `1` | Scan the whole system for candidates |
| `AC_SYSTEM_COMMAND_DIRS` | standard dirs + `PATH` | Override scan directories |
| `AC_PACKAGE_FILE_LIST` | package DB | Fixture/alternative package file list |
| `AC_FISH_FUNCTIONS_DIR` | fish config + system | Override function scan dir |
| `AC_FISH_COMPLETIONS_DIR` | fish config + system | Override completion scan dir |
| `AC_SYSTEM_COMMANDS_MAX_AGE` | `604800` | System base freshness in seconds |
| `AC_POPULAR_FILE` | shipped list | Custom usage-boost list |
| `AC_MAX_SUGGEST_DIST` | `3` | Widest edit distance considered |
| `AC_MAX_SUGGESTIONS` | `8` | Maximum alternatives shown |
| `AC_MIN_LEN_FOR_D2` | `4` | Minimum typo length for multi-edit suggestions |
| `AC_SIMILAR_PREFIX_LEN` | `2` | Prefix length for the fallback matcher |
| `AC_SEARCH_PATH` | `$PATH` | Directories searched for candidate commands |
| `AC_EXTRA_CANDIDATES` | fish builtins | Additional suggestion candidates |
| `AC_TRUST_EXTRA` | empty | Extra names eligible for auto-correction |
| `AC_NEVER_AUTO` | empty | Extra names that must never be auto-run |
| `AC_COMMON_FILE` | shipped list | Custom common-command list |
| `AC_DANGEROUS_FILE` | shipped list | Custom never-auto list |
| `AC_SYSTEM_PATH` | `/usr/bin:/bin:/usr/sbin:/sbin` | Where external tools are resolved |

## Project layout

```
autocorrect.sh              CLI entry point
fish_integration.fish       fish hooks (not-found, sudo, postexec)
install.sh / uninstall.sh   shell install into fish config
install.fish                fish-native install + activate in current shell
Makefile                    make test / install / uninstall
lib/                        bash modules (discovery, ranking, policy, cache)
share/                      common/dangerous/popular lists, config example
tests/                      12 isolated test suites + run_all.sh
examples/                   safe demos
TUTORIAL.md                 installation and configuration guide
ARCHITECTURE.md             design and safety model
CHANGELOG.md                release history
```

## Development

```sh
make test                   # same as bash tests/run_all.sh
bash autocorrect.sh explain lss
bash autocorrect.sh candidates lst
bash autocorrect.sh system stats
```

Every test runs in a private temporary directory. The suite never writes to
your real `HOME`, shell config, or cache, and never needs elevated
permissions.

## Uninstall

```sh
bash uninstall.sh
```
