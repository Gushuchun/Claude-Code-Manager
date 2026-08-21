"""Tests for ccm.config."""

from __future__ import annotations

import pytest

from ccm import config


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("CCM_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    yield tmp_path


def test_config_dir_override(isolated_config, tmp_path):
    assert config.config_dir() == tmp_path
    assert config.config_file() == tmp_path / "profiles.yaml"


def test_config_dir_xdg(monkeypatch, tmp_path):
    monkeypatch.delenv("CCM_CONFIG_DIR", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert config.config_dir() == tmp_path / "ccm"


def test_load_returns_empty_when_missing(isolated_config):
    assert config.load() == {"default": None, "profiles": {}}


def test_save_and_load_roundtrip(isolated_config):
    data = {
        "default": "a",
        "profiles": {"a": {"base_url": "https://x", "api_key": "k", "model": "m"}},
    }
    config.save(data)
    assert config.load() == data
    assert (config.config_file().stat().st_mode & 0o777) == 0o600


def test_build_env_maps_fields():
    profile = {
        "base_url": "https://x",
        "api_key": "k",
        "model": "m",
        "default_haiku_model": "h",
        "env": {"ANTHROPIC_CUSTOM_HEADERS": "{}"},
    }
    env = config.build_env(profile)
    assert env["ANTHROPIC_BASE_URL"] == "https://x"
    assert env["ANTHROPIC_API_KEY"] == "k"
    assert env["ANTHROPIC_MODEL"] == "m"
    assert env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "h"
    assert env["ANTHROPIC_CUSTOM_HEADERS"] == "{}"
    assert "ANTHROPIC_DEFAULT_OPUS_MODEL" not in env
    assert "ANTHROPIC_SMALL_FAST_MODEL" not in env


def test_build_env_skips_empty():
    profile = {"base_url": "https://x", "api_key": "", "model": None}
    env = config.build_env(profile)
    assert env == {"ANTHROPIC_BASE_URL": "https://x"}
