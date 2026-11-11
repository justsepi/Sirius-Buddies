"""Mansion global configuration stored in ~/.mansion/config.json."""

from pathlib import Path
from rich.console import Console

from mansion.storage import get_data_dir, read_json, write_json

DEFAULTS = {
    "user_name": "friend",
    "brain_provider": "deterministic",
    "ollama_model": "llama3.2",
    "ollama_url": "http://localhost:11434",
    "animations_enabled": True,
    "pomo_command": "",
}

VALID_BRAIN_PROVIDERS = ("deterministic", "ollama")


def get_config_file() -> Path:
    """Return path to config.json inside the active Mansion data directory."""
    return get_data_dir() / "config.json"


def load_config() -> dict:
    """Load config merged over DEFAULTS."""
    raw = read_json(get_config_file(), {})
    return {**DEFAULTS, **raw}


def save_config(cfg: dict) -> None:
    """Persist config dictionary to disk."""
    write_json(get_config_file(), cfg)


def parse_config_value(key: str, value: str) -> tuple[bool, object, str]:
    """Validate and coerce a CLI/TUI config value for `key`."""
    if key not in DEFAULTS:
        return False, None, f"Unknown key: {key}"

    default_val = DEFAULTS[key]
    if isinstance(default_val, bool):
        normalized = value.strip().lower()
        if normalized in ("true", "1", "yes", "on"):
            return True, True, ""
        if normalized in ("false", "0", "no", "off"):
            return True, False, ""
        return False, None, f"Expected boolean (true/false) for {key}"

    cleaned = value.strip()
    if key == "brain_provider" and cleaned not in VALID_BRAIN_PROVIDERS:
        opts = ", ".join(VALID_BRAIN_PROVIDERS)
        return False, None, f"brain_provider must be one of: {opts}"
    if key == "user_name" and not cleaned:
        return False, None, "user_name cannot be empty"
    return True, cleaned, ""


def set_config(key: str, value: str, console: Console | None = None) -> bool:
    """Validate, update, and print a single config key."""
    out = console or Console()
    ok, parsed, err = parse_config_value(key, value)
    if not ok:
        out.print(f"  [bright_red]{err}[/]")
        if key not in DEFAULTS:
            out.print(f"  [dim]Valid keys: {', '.join(DEFAULTS.keys())}[/]")
        return False

    cfg = load_config()
    cfg[key] = parsed
    save_config(cfg)
    out.print(f"  [bright_green]✓[/] {key} = {parsed}")
    return True


def show_config(key: str | None = None, console: Console | None = None) -> None:
    """Print current Mansion settings."""
    out = console or Console()
    cfg = load_config()
    out.print("\n  [bright_cyan]★  Mansion Config[/]\n")
    if key:
        if key in cfg:
            out.print(f"  {key} = {cfg[key]}")
        else:
            out.print(f"  [bright_red]Unknown key:[/] {key}")
    else:
        for k, v in cfg.items():
            shown = v if v != "" else "(auto)"
            out.print(f"  {k} = {shown}")
    out.print()


def toggle_or_cycle_config(cfg: dict, key: str) -> dict:
    """Toggle booleans or cycle enum settings from the interactive Config screen."""
    updated = dict(cfg)
    if isinstance(DEFAULTS.get(key), bool):
        updated[key] = not bool(updated.get(key, DEFAULTS[key]))
    elif key == "brain_provider":
        cur = updated.get(key, "deterministic")
        idx = VALID_BRAIN_PROVIDERS.index(cur) if cur in VALID_BRAIN_PROVIDERS else 0
        updated[key] = VALID_BRAIN_PROVIDERS[(idx + 1) % len(VALID_BRAIN_PROVIDERS)]
    save_config(updated)
    return updated


def reset_config() -> dict:
    """Restore all Mansion settings to DEFAULTS."""
    fresh = dict(DEFAULTS)
    save_config(fresh)
    return fresh
