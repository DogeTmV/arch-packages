# terminal-autocorrect

Conservative, test-driven command typo correction for **fish**. It hooks into
fish's command-not-found mechanism, so there is no new command to remember.

A typo is **auto-run** only when the intended command is one edit away, unique,
and trusted (recently used or in the curated common-command list). Everything
else becomes a suggestion. Corrections never touch your arguments.

## Quick start

```sh
bash tests/run_all.sh     # 130 tests, no permissions needed
bash install.sh           # install into ~/.config/fish
```

Restart fish, then:

```fish
lss                 # runs ls silently
lst                 # suggests: last, ls
pakman -Syu         # runs pacman -Syu (arguments untouched)
sduo apt update     # suggests: sudo
sudo grpe file      # suggests: grep
sudo paman -Syu     # runs sudo pacman -Syu
```

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

Verify the hooks are active:

```fish
functions -q fish_command_not_found; and echo not-found-hook-ok
functions -q sudo; and echo sudo-hook-ok
functions -q __ac_record_command; and echo recorder-ok
```

There is nothing else to enable. Open a new terminal, type `lss`, and fish
will run `ls` without any extra command. Re-running `bash install.sh` later
upgrades the installed copy in place. To remove it permanently, run
`bash uninstall.sh` and restart fish.

If you keep fish config in a non-standard location:

```sh
AC_FISH_CONFIG_DIR=/path/to/your/fish bash install.sh
```

See **[TUTORIAL.md](TUTORIAL.md)** for the full step-by-step installation,
configuration, troubleshooting, and uninstall guide.
See **[ARCHITECTURE.md](ARCHITECTURE.md)** for design and safety details.

## Behavior at a glance

| Situation | Result |
| --- | --- |
| Unique one-edit typo of a trusted command | Corrected and run silently |
| Unique one-edit typo of an untrusted command | Suggestion only |
| Several equally close commands | Suggestion only |
| Two-edit typo | Suggestion only |
| Dangerous command (e.g. `rm`) | Suggestion only |
| `sudo` usage, target is not `pacman` | Suggestion only |
| `sudo pacman` with a mistyped `pacman` | Corrected and run silently |
| No plausible command | fish's usual error |

Examples of "one edit": deletion (`lss` → `ls`), insertion (`paman` →
`pacman`), substitution (`grpe` → `grep`), transposition (`sl` → `ls`).

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
| `AC_CACHE_MAX_AGE` | `86400` | Cache freshness in seconds |
| `AC_NO_AUTO_CACHE` | `0` | Set to `1` to disable automatic rebuilds |
| `AC_SEARCH_PATH` | `$PATH` | Directories searched for candidate commands |
| `AC_EXTRA_CANDIDATES` | fish builtins | Additional suggestion candidates |
| `AC_TRUST_EXTRA` | empty | Extra names eligible for auto-correction |
| `AC_NEVER_AUTO` | empty | Extra names that must never be auto-run |
| `AC_COMMON_FILE` | shipped list | Custom common-command list |
| `AC_DANGEROUS_FILE` | shipped list | Custom never-auto list |
| `AC_MAX_SUGGESTIONS` | `5` | Maximum alternatives shown |
| `AC_MIN_LEN_FOR_D2` | `4` | Minimum typo length for two-edit suggestions |
| `AC_SYSTEM_PATH` | `/usr/bin:/bin:/usr/sbin:/sbin` | Where external tools are resolved |

## Project layout

```
autocorrect.sh              CLI entry point
fish_integration.fish       fish hooks (not-found, sudo, postexec)
install.sh / uninstall.sh   install into fish config
Makefile                    make test / install / uninstall
lib/                        bash modules
share/                      common/dangerous lists, config example
tests/                      8 isolated test suites + run_all.sh
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
```

Every test runs in a private temporary directory. The suite never writes to
your real `HOME`, shell config, or cache, and never needs elevated
permissions.

## Uninstall

```sh
bash uninstall.sh
```
