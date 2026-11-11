"""Offline JSON storage helpers for ~/.mansion/."""

import json
import os
from pathlib import Path
from typing import Any


def get_data_dir() -> Path:
    """Return Mansion's data directory (~/.mansion or MANSION_DIR env override)."""
    override = os.environ.get("MANSION_DIR", "").strip()
    return Path(override) if override else (Path.home() / ".mansion")


def read_json(path: Path, default: Any) -> Any:
    """Load JSON from disk, returning a fresh copy of `default` on missing/invalid files."""
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if type(data) is type(default):
                return data
        except (OSError, json.JSONDecodeError):
            pass
    if isinstance(default, dict):
        return dict(default)
    if isinstance(default, list):
        return list(default)
    return default


def write_json(path: Path, data: Any) -> None:
    """Persist JSON data to disk, creating parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
