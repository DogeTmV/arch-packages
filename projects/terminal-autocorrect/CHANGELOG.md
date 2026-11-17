# Changelog

## 2.1.0

- Added whole-system command discovery: standard bin/sbin dirs, `PATH`,
  package-owned files (`pacman -Qlq`, dpkg fallback), and fish function and
  completion names. Discoveries are suggestion candidates only, never trusted
  for auto-run.
- Added `lib/system_commands.sh` with a cached, atomic, flock-protected system
  base and `autocorrect.sh system rebuild|stats|list|path`.
- Added `lib/ranking.sh` and `share/popular-commands.txt`. Suggestions are now
  ordered by usage count, common-list membership, popular-list boost, then
  alphabetically. Ranking never grants trust.
- Widened suggestion search to three edits plus a shared-prefix/substring
  fallback. Only unique one-edit trusted matches are still auto-run.
- Expanded `share/common-commands.txt` with a much larger trusted command base.
- Added `install.fish`, which installs and activates the hooks in the current
  fish process with a single `source` command.
- Added `AC_DISCOVER_SYSTEM_COMMANDS`, `AC_SYSTEM_COMMAND_DIRS`,
  `AC_PACKAGE_FILE_LIST`, `AC_FISH_FUNCTIONS_DIR`,
  `AC_FISH_COMPLETIONS_DIR`, `AC_SYSTEM_COMMANDS_MAX_AGE`,
  `AC_POPULAR_FILE`, `AC_MAX_SUGGEST_DIST`, and `AC_SIMILAR_PREFIX_LEN`.
- Expanded the suite to 166 tests across 12 isolated suites.

## 2.0.0

- Rebuilt as a modular project: `lib/system.sh`, `distance.sh`,
  `candidates.sh`, `common.sh`, `cache.sh`, and `policy.sh`.
- Added recent-command cache built from local fish/bash/zsh history, with
  atomic writes, optional `flock`, freshness control, and `fish_postexec`
  recording of every command you run.
- Added trust tiers: only cached, common, or explicitly trusted commands are
  auto-corrected. All other close matches are suggestions only.
- Added `share/dangerous-commands.txt`; destructive commands are never
  auto-run.
- Added two-edit suggestions (never auto-run) and configurable suggestion
  limits.
- Preserved the sudo rule: privileged commands suggest, except pacman.
- Guaranteed base-only correction: arguments are never rewritten.
- Removed reliance on PATH-resolved `grep` for safety decisions.
- Added `install.sh`, `uninstall.sh`, `Makefile`, `TUTORIAL.md`,
  `ARCHITECTURE.md`, and a unified test runner.
- Expanded test suite to 130 tests across 9 suites, including real fish
  integration tests.

## 1.0.0

- Initial bash heuristic with fish `fish_command_not_found` and `sudo`
  hooks.
