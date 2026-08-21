"""Claude Code Manager CLI."""

from __future__ import annotations

import errno
import os
import shutil

import typer
from rich.console import Console
from rich.table import Table

from . import config as cfg

app = typer.Typer(
    name="ccm",
    help="Claude Code Manager - switch Base URL / Model / API Key in one command",
    no_args_is_help=False,
)
console = Console()
err_console = Console(stderr=True)


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return f"{key[:6]}...{key[-4:]}"


def _require_profile(name: str) -> dict:
    profiles = cfg.load()["profiles"]
    if name not in profiles:
        err_console.print(f"[red]Profile not found: {name}[/red]")
        raise typer.Exit(1)
    return profiles[name]


def _resolve(name: str | None) -> tuple[str, dict]:
    data = cfg.load()
    if name:
        if name not in data["profiles"]:
            err_console.print(f"[red]Profile not found: {name}[/red]")
            raise typer.Exit(1)
        return name, data["profiles"][name]
    default = data.get("default")
    if not default or default not in data["profiles"]:
        err_console.print("[red]No default profile set. Use 'ccm use <name>' or 'ccm run <name>'[/red]")
        raise typer.Exit(1)
    return default, data["profiles"][default]


def _print_table() -> None:
    data = cfg.load()
    profiles = data["profiles"]
    default = data.get("default")
    if not profiles:
        console.print("[yellow]No profiles yet. Create the first one with 'ccm add <name>'[/yellow]")
        return
    table = Table(title="Claude Code Manager", show_lines=True)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("URL", no_wrap=True, overflow="ellipsis")
    table.add_column("Model", no_wrap=True, overflow="ellipsis")
    table.add_column("API Key", no_wrap=True)
    for name, p in profiles.items():
        marker = "[bold green]*[/bold green] " if name == default else "  "
        table.add_row(
            f"{marker}{name}",
            p.get("base_url", "-"),
            p.get("model", "-"),
            _mask_key(p.get("api_key", "")) or "-",
        )
    console.print(table)
    if default:
        console.print(f"Current default: [bold]{default}[/bold]  ->  launch with 'ccm run'")


@app.callback(invoke_without_command=True)
def _main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        _print_table()


@app.command("list")
def list_cmd() -> None:
    """List all profiles."""
    _print_table()


@app.command()
def current() -> None:
    """Show the current default profile."""
    data = cfg.load()
    default = data.get("default")
    if not default or default not in data["profiles"]:
        err_console.print("[yellow]No default profile set[/yellow]")
        raise typer.Exit(1)
    p = data["profiles"][default]
    console.print(f"[bold]{default}[/bold]")
    console.print(f"  URL:   {p.get('base_url', '-')}")
    console.print(f"  Model: {p.get('model', '-')}")
    console.print(f"  Key:   {_mask_key(p.get('api_key', '')) or '-'}")


@app.command()
def add(
    name: str = typer.Argument(..., help="Profile name"),
    url: str | None = typer.Option(None, "--url", prompt="Base URL"),
    key: str | None = typer.Option(
        None, "--key", prompt="API Key", hide_input=True, confirmation_prompt=True
    ),
    model: str | None = typer.Option(None, "--model", prompt="Model"),
    sonnet: str | None = typer.Option(None, "--sonnet", help="default sonnet model (defaults to --model)"),
    opus: str | None = typer.Option(None, "--opus", help="default opus model (defaults to --model)"),
    haiku: str | None = typer.Option(None, "--haiku", help="default haiku model (defaults to --model)"),
    small_fast: str | None = typer.Option(
        None, "--small-fast", help="small fast model (defaults to --model)"
    ),
    no_sync: bool = typer.Option(
        False, "--no-sync", help="only set --model, do not sync it to the other model slots"
    ),
) -> None:
    """Create a new profile (prompts interactively when --url/--key/--model are omitted).

    By default --model is synced to the sonnet/opus/haiku/small-fast slots so
    every model tier uses your provider; pass --no-sync to disable this.
    """
    data = cfg.load()
    if name in data["profiles"]:
        err_console.print(f"[red]Profile already exists: {name}[/red]")
        raise typer.Exit(1)

    profile = {"base_url": url, "api_key": key, "model": model}
    for field, val in (
        ("default_sonnet_model", sonnet),
        ("default_opus_model", opus),
        ("default_haiku_model", haiku),
        ("small_fast_model", small_fast),
    ):
        if no_sync:
            if val:
                profile[field] = val
        else:
            profile[field] = val or model

    missing = [f for f in cfg.REQUIRED if not profile.get(f)]
    if missing:
        err_console.print(f"[red]Missing required fields: {', '.join(missing)}[/red]")
        raise typer.Exit(1)

    data["profiles"][name] = profile
    if not data.get("default"):
        data["default"] = name
    cfg.save(data)

    msg = f"Created [bold]{name}[/bold]"
    if data["default"] == name:
        msg += " and set as default"
    console.print(f"[green]{msg}[/green]")


@app.command()
def use(name: str = typer.Argument(..., help="Profile name")) -> None:
    """Set the default profile."""
    _require_profile(name)
    data = cfg.load()
    data["default"] = name
    cfg.save(data)
    console.print(f"Default profile switched to [bold]{name}[/bold] -> launch with 'ccm run'")


def _launch(name: str | None, extra: list[str]) -> None:
    prof_name, profile = _resolve(name)
    missing = [f for f in cfg.REQUIRED if not profile.get(f)]
    if missing:
        err_console.print(
            f"[red]Profile '{prof_name}' is missing required fields: {', '.join(missing)}[/red]"
        )
        raise typer.Exit(1)

    claude = os.environ.get("CCM_CLAUDE") or shutil.which("claude")
    if not claude:
        err_console.print("[red]claude not found on PATH. Install Claude Code or set CCM_CLAUDE.[/red]")
        raise typer.Exit(1)

    managed = set(cfg.ENV_VAR_MAP.values())
    env = {k: v for k, v in os.environ.items() if k not in managed}
    env.update(cfg.build_env(profile))
    console.print(
        f"Launching [bold]{prof_name}[/bold] -> [cyan]{profile['model']}[/cyan] @ {profile['base_url']}"
    )
    try:
        os.execvpe(claude, [claude, *extra], env)
    except OSError as exc:
        if exc.errno != errno.ENOEXEC:
            raise
        # Shebang-less scripts fail with ENOEXEC under execve; let a shell
        # interpret them instead (POSIX shells fall back to script mode).
        os.execvpe("/bin/sh", ["/bin/sh", "-c", 'exec "$0" "$@"', claude, *extra], env)


@app.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
def run(
    ctx: typer.Context,
    name: str | None = typer.Argument(None, help="Profile name (defaults to the active profile)"),
) -> None:
    """Launch Claude Code with a profile (extra args are passed through to claude)."""
    _launch(name, ctx.args)


@app.command("resume", context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
def resume(
    ctx: typer.Context,
    name: str | None = typer.Argument(None, help="Profile name (defaults to the active profile)"),
) -> None:
    """Launch claude --resume to pick a past session."""
    _launch(name, ["--resume", *ctx.args])


@app.command()
def env(
    name: str | None = typer.Argument(None, help="Profile name (defaults to the active profile)"),
) -> None:
    """Print export statements for the current shell, e.g. eval "$(ccm env <name>)"."""
    _, profile = _resolve(name)
    built = cfg.build_env(profile)
    if not built:
        err_console.print("[yellow]This profile has no environment variables[/yellow]")
        raise typer.Exit(1)
    for var in cfg.ENV_VAR_MAP.values():
        if var not in built and var in os.environ:
            print(f"unset {var}")
    for var, val in built.items():
        escaped = val.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")
        print(f'export {var}="{escaped}"')


@app.command()
def remove(
    name: str = typer.Argument(..., help="Profile name"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a profile."""
    data = cfg.load()
    if name not in data["profiles"]:
        err_console.print(f"[red]Profile not found: {name}[/red]")
        raise typer.Exit(1)
    if not yes:
        if not typer.confirm(f"Delete profile '{name}'?"):
            console.print("Cancelled")
            raise typer.Exit(0)
    del data["profiles"][name]
    if data.get("default") == name:
        data["default"] = None
    cfg.save(data)
    console.print(f"[green]Deleted {name}[/green]")


@app.command()
def config() -> None:
    """Show the config directory path."""
    console.print(cfg.config_dir())
