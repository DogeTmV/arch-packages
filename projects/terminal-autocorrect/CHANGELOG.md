# Changelog

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
