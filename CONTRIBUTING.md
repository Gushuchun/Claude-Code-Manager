# Contributing

Thanks for your interest in contributing to Claude Code Manager (ccm)!

## Development setup

Requirements:

- Python 3.9+
- [uv](https://docs.astral.sh/uv/)

```bash
git clone <repo-url>
cd claude-code-manager
uv sync --dev                        # install the project and dev tools into .venv
uv run pre-commit install            # optional: enable pre-commit hooks
```

## Running checks

```bash
uv run pytest                        # run tests
uv run ruff check .                  # lint
uv run ruff format --check .         # formatting check
uv run pre-commit run --all-files    # run all pre-commit hooks
```

## Submitting changes

1. Fork the repository and create a feature branch from `main`.
2. Make your change, keeping it focused and minimal.
3. Add tests for any new behavior.
4. Run all of the checks above.
5. Open a pull request against `main` and fill out the template.

## Commit messages

Use concise, imperative-style messages, for example:

```text
fix: clear stale ANTHROPIC_* vars in run
feat: add ccm test connectivity check
```

## Code style

- Python 3.9+ compatible; `from __future__ import annotations` is used.
- Linting and formatting are enforced by [ruff](https://docs.astral.sh/ruff/)
  (see `pyproject.toml`).
- Keep user-facing CLI messages in English.
