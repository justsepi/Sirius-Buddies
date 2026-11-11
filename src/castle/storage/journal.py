"""Bounded mission chronicle stored in ~/.castle/journal.json."""

from datetime import datetime
from pathlib import Path

from castle.storage import get_data_dir, read_json, write_json

MAX_JOURNAL_ENTRIES = 300


def get_journal_file() -> Path:
    """Return path to journal.json inside the active Castle data directory."""
    return get_data_dir() / "journal.json"


def log_event(
    buddy_id: str,
    action: str,
    summary: str,
    ok: bool = True,
) -> dict:
    """Append a mission event to journal.json, keeping the latest MAX_JOURNAL_ENTRIES."""
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "buddy": buddy_id,
        "action": action,
        "summary": summary,
        "ok": ok,
    }
    entries = read_json(get_journal_file(), [])
    entries.append(entry)
    if len(entries) > MAX_JOURNAL_ENTRIES:
        entries = entries[-MAX_JOURNAL_ENTRIES:]
    try:
        write_json(get_journal_file(), entries)
    except OSError:
        pass
    return entry


def get_recent_events(limit: int = 15) -> list[dict]:
    """Return the most recent journal entries (newest first)."""
    entries = read_json(get_journal_file(), [])
    if limit <= 0:
        return []
    return list(reversed(entries[-limit:]))
