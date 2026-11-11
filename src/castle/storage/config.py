"""Castle global configuration stored in ~/.castle/config.json."""

from pathlib import Path
from rich.console import Console

from castle.storage import get_data_dir, read_json, write_json

DEFAULTS = {
    "user_name": "dude",
    "animations_enabled": True,
    "show_shadow": True,
    "pomo_command": "",
}


def get_config_file() -> Path:
    """Return path to config.json inside the active Castle data directory."""
    return get_data_dir() / "config.json"


def load_config() -> dict:
    """Load active Castle settings merged over DEFAULTS."""
    raw = read_json(get_config_file(), {})
    cleaned = {k: v for k, v in raw.items() if k in DEFAULTS}
    return {**DEFAULTS, **cleaned}


def save_config(cfg: dict) -> None:
    """Persist active Castle config keys to disk."""
    filtered = {k: cfg.get(k, default) for k, default in DEFAULTS.items()}
    write_json(get_config_file(), filtered)


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
    out.print(f"  [bright_blue]✓[/] {key} = {parsed}")
    return True


def show_config(key: str | None = None, console: Console | None = None) -> None:
    """Print current Castle settings."""
    out = console or Console()
    cfg = load_config()
    out.print("\n  [bold bright_white]✦  Castle Config[/]\n")
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
    """Toggle boolean settings from the interactive Config screen."""
    updated = dict(cfg)
    if isinstance(DEFAULTS.get(key), bool):
        updated[key] = not bool(updated.get(key, DEFAULTS[key]))
    save_config(updated)
    return updated


def reset_config() -> dict:
    """Restore all Castle settings to DEFAULTS."""
    fresh = dict(DEFAULTS)
    save_config(fresh)
    return fresh
