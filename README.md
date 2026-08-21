# Claude Code Manager (ccm)

Switch Claude Code's **Base URL / API Key / Model** in one command. No more
editing `~/.bashrc` and `source`-ing it every time you change providers.

## Features

- **Profiles** — group a base URL, API key, and model set into a named profile
- **One-command launch** — `ccm run` starts Claude Code with the active profile
- **Shell-friendly** — `eval "$(ccm env <name>)"` updates your current shell
- **Deterministic env** — managed `ANTHROPIC_*` variables not defined by a
  profile are cleared, so stale values never leak in
- **Secure by default** — config directory is `0700`, config file is `0600`

## Installation

### From PyPI

```bash
pip install ccm-cli
```

Or, for an isolated global `ccm` binary:

```bash
pipx install ccm-cli
# or with uv
uv tool install ccm-cli
```

`pip install` puts the `ccm` command into the current Python environment's
bin directory (e.g. `venv/bin/ccm` or `~/.local/bin/ccm` with `--user`).
`pipx` / `uv tool` install it into an isolated environment with a globally
available `ccm`.

### From source (for development)

If you want to work on the code itself:

```bash
git clone <repo-url>
cd claude-code-manager
uv tool install .
# or editable, so code changes take effect immediately
uv tool install --editable .
```

Requires Python 3.9+.

## Quickstart

```bash
# Create a profile (interactive prompts; or pass --url/--key/--model)
ccm add volcengine
ccm add deepseek --url https://api.deepseek.com --key sk-xxxx --model deepseek-chat

# List, set default, launch
ccm list
ccm use deepseek
ccm run

# Launch a specific profile, passing extra args through to claude
ccm run volcengine -- --dangerously-skip-permissions

# Apply to the current shell
eval "$(ccm env deepseek)"
```

## Commands

| Command            | Description                                                        |
| ------------------ | ------------------------------------------------------------------ |
| `ccm` / `ccm list` | List all profiles (the default is marked with `*`)                 |
| `ccm current`      | Show the active default profile                                    |
| `ccm add <name>`   | Create a profile (interactive; or `--url/--key/--model/--sonnet/--opus/--haiku`) |
| `ccm use <name>`   | Set the default profile                                            |
| `ccm run [name]`   | Launch claude with a profile; extra args are passed through        |
| `ccm resume [name]`| Launch `claude --resume` to pick a past session                    |
| `ccm env [name]`   | Print `export`/`unset` statements to eval in the current shell     |
| `ccm remove <name>`| Delete a profile (`-y` to skip confirmation)                       |
| `ccm config`       | Print the config directory path                                    |

## Configuration

Stored in `~/.config/ccm/profiles.yaml` (override with `CCM_CONFIG_DIR`).

```yaml
default: volcengine
profiles:
  volcengine:
    base_url: https://ark.cn-beijing.volces.com/api/plan
    api_key: ark-xxxx
    model: deepseek-v4-flash[1m]
    default_sonnet_model: deepseek-v4-flash[1m]
    default_opus_model: deepseek-v4-flash[1m]
    default_haiku_model: deepseek-v4-flash[1m]
    # env:  # optional: pass through arbitrary extra env vars
    #   ANTHROPIC_CUSTOM_HEADERS: '{"x-foo": "bar"}'
```

### Field to environment variable mapping

| Field                | Environment variable          |
| -------------------- | ----------------------------- |
| `base_url`           | `ANTHROPIC_BASE_URL`          |
| `api_key`            | `ANTHROPIC_API_KEY`           |
| `model`              | `ANTHROPIC_MODEL`             |
| `small_fast_model`   | `ANTHROPIC_SMALL_FAST_MODEL`  |
| `default_sonnet_model` | `ANTHROPIC_DEFAULT_SONNET_MODEL` |
| `default_opus_model` | `ANTHROPIC_DEFAULT_OPUS_MODEL` |
| `default_haiku_model` | `ANTHROPIC_DEFAULT_HAIKU_MODEL` |

### Model slots

`ANTHROPIC_MODEL` sets the main model. The other slots control what Claude Code
uses for specific roles: the small/fast (Haiku) slot for background work such as
auto-compaction and title generation, and the Sonnet / Opus / Haiku tiers you
can select with Shift+Tab or `/model`. With a custom endpoint, point every slot
at your model, or background tasks will reach your endpoint with default
Anthropic model names and fail.

`ccm add` syncs `--model` to all slots by default. Pass `--no-sync` to only set
`ANTHROPIC_MODEL`, or override individual slots with
`--sonnet/--opus/--haiku/--small-fast`.

## Resuming sessions

```bash
ccm resume              # claude --resume: pick a past session (default profile)
ccm resume deepseek     # same, with a specific profile
ccm run deepseek --resume   # also works: extra args pass through to claude
```

## Choosing the claude binary

`ccm run` uses the first `claude` found on `PATH`. If that resolves to the
wrong binary (for example, a broken npm-installed stub shadowing a working
install), override it with `CCM_CLAUDE`, which takes precedence over the
`PATH` lookup:

```bash
CCM_CLAUDE=/usr/local/bin/claude ccm run
```

## Design notes

- **No `.bashrc` hacks, no parent-shell mutation.** `ccm run` uses
  `os.execvpe` to replace itself with claude; `ccm env` goes through `eval`
  when you want to affect the current shell. A child process can never change
  its parent's environment.
- **Deterministic managed vars.** When running, managed variables that a
  profile does not define are removed from the environment; `ccm env` emits
  `unset` lines for them first. Switching is always predictable.
- **Schema decoupled from Claude Code.** Profiles store business fields; env
  vars are generated at launch time from `ENV_VAR_MAP` in
  `src/ccm/config.py`. If Claude Code renames or adds env vars, update the map
  in one place — no profile migration needed.
- **API keys are stored in the config file** (no system keyring in v1, because
  WSL2 has no Secret Service daemon by default). The config directory is
  `0700` and the file is `0600`.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, testing, and contribution
guidelines.

## License

MIT. See [LICENSE](LICENSE).
