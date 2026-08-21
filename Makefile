.PHONY: help install dev test lint format check clean

help:
	@echo "Targets: install, dev, test, lint, format, check, clean"

install:
	uv tool install .

dev:
	uv sync --dev

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

check: lint format-check test

format-check:
	uv run ruff format --check .

clean:
	rm -rf .venv build dist *.egg-info .pytest_cache .ruff_cache
