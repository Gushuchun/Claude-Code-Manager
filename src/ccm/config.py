"""Profile storage and environment-variable mapping."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

# profile field name -> Claude Code environment variable
ENV_VAR_MAP = {
    "base_url": "ANTHROPIC_BASE_URL",
    "api_key": "ANTHROPIC_API_KEY",
    "model": "ANTHROPIC_MODEL",
    "small_fast_model": "ANTHROPIC_SMALL_FAST_MODEL",
    "default_sonnet_model": "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "default_opus_model": "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "default_haiku_model": "ANTHROPIC_DEFAULT_HAIKU_MODEL",
}

REQUIRED = ("base_url", "api_key", "model")


def config_dir() -> Path:
    override = os.environ.get("CCM_CONFIG_DIR")
    if override:
        return Path(override)
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "ccm"


def config_file() -> Path:
    return config_dir() / "profiles.yaml"


def load() -> dict:
    path = config_file()
    if not path.exists():
        return {"default": None, "profiles": {}}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data.setdefault("default", None)
    data.setdefault("profiles", {})
    return data


def save(data: dict) -> None:
    d = config_dir()
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except OSError:
        pass
    path = config_file()
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    os.chmod(path, 0o600)


def build_env(profile: dict) -> dict:
    """Map a profile to Claude Code env vars, only for fields that are set."""
    env = {}
    for field, var in ENV_VAR_MAP.items():
        val = profile.get(field)
        if val:
            env[var] = str(val)
    for key, val in (profile.get("env") or {}).items():
        if val:
            env[str(key)] = str(val)
    return env
