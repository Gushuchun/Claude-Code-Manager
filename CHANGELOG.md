# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `ccm resume` — launch `claude --resume` to pick a past session
- `ccm add` syncs `--model` to all model slots by default (`--no-sync` to opt
  out), matching the previous all-slots setup

### Changed

- `ccm list` draws a horizontal separator between every profile row, and long
  cells are truncated with an ellipsis instead of wrapping

### Fixed

- `ccm run` falls back to shell interpretation when exec fails with `ENOEXEC`
  (shebang-less scripts), and supports the `CCM_CLAUDE` env var to override
  which claude binary is launched.
- Require Python 3.10+; `str | None` annotations break Typer's runtime type
  hint evaluation on Python 3.9.

## [0.1.0] - 2026-08-21

### Added

- `ccm add` — create profiles interactively or via flags
- `ccm list` / bare `ccm` — list all profiles as a table
- `ccm current` — show the active default profile
- `ccm use` — set the default profile
- `ccm run` — launch Claude Code with a profile; extra args are passed through
- `ccm env` — print `export`/`unset` statements for `eval`
- `ccm remove` — delete a profile
- `ccm config` — print the config directory path
- Deterministic managed `ANTHROPIC_*` env vars (stale values are cleared)
- Config stored in `~/.config/ccm/profiles.yaml` with `0700`/`0600` permissions
