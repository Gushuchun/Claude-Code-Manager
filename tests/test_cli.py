"""Tests for ccm.cli."""

from __future__ import annotations

import errno
import os

import pytest
from typer.testing import CliRunner

from ccm.cli import app

runner = CliRunner()

URL = "https://api.example.com"
KEY = "sk-test-1234567890"


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("CCM_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    yield tmp_path


def _add(name: str, model: str = "m1", no_sync: bool = False, **extra) -> None:
    args = ["add", name, "--url", URL, "--key", KEY, "--model", model]
    if no_sync:
        args.append("--no-sync")
    for k, v in extra.items():
        args += [f"--{k}", v]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output


def test_add_creates_profile(isolated_config):
    result = runner.invoke(app, ["add", "demo", "--url", URL, "--key", KEY, "--model", "m1"])
    assert result.exit_code == 0
    assert "demo" in result.stdout
    assert (isolated_config / "profiles.yaml").exists()


def test_add_duplicate_fails(isolated_config):
    _add("demo")
    result = runner.invoke(app, ["add", "demo", "--url", URL, "--key", KEY, "--model", "m1"])
    assert result.exit_code != 0
    assert "already exists" in result.stderr


def test_add_missing_required(isolated_config):
    result = runner.invoke(app, ["add", "demo", "--url", URL, "--model", "m1", "--key", ""])
    assert result.exit_code != 0
    assert "Missing required fields" in result.stderr


def test_list_shows_profiles(isolated_config):
    _add("demo")
    _add("other")
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "demo" in result.stdout
    assert "other" in result.stdout


def test_use_sets_default(isolated_config):
    _add("demo")
    result = runner.invoke(app, ["use", "demo"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["current"])
    assert result.exit_code == 0
    assert "demo" in result.stdout


def test_current_without_default(isolated_config):
    result = runner.invoke(app, ["current"])
    assert result.exit_code != 0


def test_config_command_shows_dir(isolated_config):
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert result.stdout.strip() == str(isolated_config)


def test_env_prints_exports(isolated_config):
    _add("demo")
    result = runner.invoke(app, ["env", "demo"])
    assert result.exit_code == 0
    assert f'export ANTHROPIC_BASE_URL="{URL}"' in result.stdout
    assert f'export ANTHROPIC_API_KEY="{KEY}"' in result.stdout


def test_env_unsets_stale_managed_vars(isolated_config, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_DEFAULT_HAIKU_MODEL", "leaked")
    _add("demo", no_sync=True)
    result = runner.invoke(app, ["env", "demo"])
    assert result.exit_code == 0
    assert "unset ANTHROPIC_DEFAULT_HAIKU_MODEL" in result.stdout


def test_remove_deletes_profile(isolated_config):
    _add("demo")
    result = runner.invoke(app, ["remove", "demo", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.stdout


def test_run_launches_claude_with_profile_env(isolated_config, monkeypatch):
    _add("demo", model="m1")
    captured = {}

    def fake_execvpe(file, args, env):
        captured["file"] = file
        captured["args"] = args
        captured["env"] = env
        raise SystemExit(0)

    monkeypatch.setattr(os, "execvpe", fake_execvpe)
    monkeypatch.setattr("ccm.cli.shutil.which", lambda _: "/usr/bin/claude")

    result = runner.invoke(app, ["run", "demo", "--", "--dangerously-skip-permissions"])
    assert result.exit_code == 0
    assert captured["file"] == "/usr/bin/claude"
    assert captured["args"][1:] == ["--dangerously-skip-permissions"]
    assert captured["env"]["ANTHROPIC_BASE_URL"] == URL
    assert captured["env"]["ANTHROPIC_API_KEY"] == KEY
    assert captured["env"]["ANTHROPIC_MODEL"] == "m1"


def test_run_clears_stale_managed_vars(isolated_config, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_DEFAULT_HAIKU_MODEL", "leaked")
    _add("demo", model="m1", no_sync=True)
    captured = {}

    def fake_execvpe(file, args, env):
        captured["env"] = env
        raise SystemExit(0)

    monkeypatch.setattr(os, "execvpe", fake_execvpe)
    monkeypatch.setattr("ccm.cli.shutil.which", lambda _: "/usr/bin/claude")

    result = runner.invoke(app, ["run", "demo"])
    assert result.exit_code == 0
    assert "ANTHROPIC_DEFAULT_HAIKU_MODEL" not in captured["env"]


def test_run_without_default(isolated_config):
    result = runner.invoke(app, ["run"])
    assert result.exit_code != 0
    assert "No default profile" in result.stderr


def test_add_syncs_model_to_all_slots(isolated_config):
    _add("demo", model="m1")
    result = runner.invoke(app, ["env", "demo"])
    assert result.exit_code == 0
    for var in (
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL",
        "ANTHROPIC_SMALL_FAST_MODEL",
    ):
        assert f'export {var}="m1"' in result.stdout


def test_add_no_sync_only_sets_model(isolated_config):
    _add("demo", no_sync=True)
    result = runner.invoke(app, ["env", "demo"])
    assert result.exit_code == 0
    assert "export ANTHROPIC_DEFAULT_HAIKU_MODEL" not in result.stdout
    assert "export ANTHROPIC_SMALL_FAST_MODEL" not in result.stdout


def test_add_slot_override_wins_over_sync(isolated_config):
    _add("demo", model="m1", haiku="h9")
    result = runner.invoke(app, ["env", "demo"])
    assert 'export ANTHROPIC_DEFAULT_HAIKU_MODEL="h9"' in result.stdout
    assert 'export ANTHROPIC_DEFAULT_OPUS_MODEL="m1"' in result.stdout


def test_resume_passes_resume_flag(isolated_config, monkeypatch):
    _add("demo")
    captured = {}

    def fake_execvpe(file, args, env):
        captured["args"] = args
        raise SystemExit(0)

    monkeypatch.setattr(os, "execvpe", fake_execvpe)
    monkeypatch.setattr("ccm.cli.shutil.which", lambda _: "/usr/bin/claude")

    result = runner.invoke(app, ["resume", "demo", "--", "-p", "hello"])
    assert result.exit_code == 0
    assert captured["args"][1:] == ["--resume", "-p", "hello"]


def test_run_uses_ccm_claude_override(isolated_config, monkeypatch):
    _add("demo")
    monkeypatch.setenv("CCM_CLAUDE", "/opt/claude")
    captured = {}

    def fake_execvpe(file, args, env):
        captured["file"] = file
        raise SystemExit(0)

    monkeypatch.setattr(os, "execvpe", fake_execvpe)
    result = runner.invoke(app, ["run", "demo"])
    assert result.exit_code == 0
    assert captured["file"] == "/opt/claude"


def test_run_falls_back_to_shell_on_enexec(isolated_config, monkeypatch):
    _add("demo", model="m1")
    captured = {}

    def fake_execvpe(file, args, env):
        if file == "/usr/bin/claude":
            exc = OSError(errno.ENOEXEC, "Exec format error")
            raise exc
        captured["file"] = file
        captured["args"] = args
        captured["env"] = env
        raise SystemExit(0)

    monkeypatch.setattr(os, "execvpe", fake_execvpe)
    monkeypatch.setattr("ccm.cli.shutil.which", lambda _: "/usr/bin/claude")
    result = runner.invoke(app, ["run", "demo"])
    assert result.exit_code == 0
    assert captured["file"] == "/bin/sh"
    assert captured["args"][1] == "-c"
    assert captured["args"][2] == 'exec "$0" "$@"'
    assert captured["args"][3] == "/usr/bin/claude"
    assert captured["env"]["ANTHROPIC_MODEL"] == "m1"
