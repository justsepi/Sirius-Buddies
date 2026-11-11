"""Tests for Castle offline config and bounded journal storage."""

from rich.console import Console

import castle.storage.config as config_mod
import castle.storage.journal as journal_mod


def test_config_defaults_save_and_validation(tmp_path, monkeypatch):
    monkeypatch.setenv("CASTLE_DIR", str(tmp_path))

    cfg = config_mod.load_config()
    assert cfg["user_name"] == "friend"
    assert cfg["brain_provider"] == "deterministic"
    assert cfg["animations_enabled"] is True

    buf = Console(record=True, width=80)
    assert config_mod.set_config("user_name", "Sepi", console=buf) is True
    assert config_mod.set_config("animations_enabled", "off", console=buf) is True
    assert config_mod.set_config("brain_provider", "invalid_ai", console=buf) is False
    assert config_mod.set_config("user_name", "   ", console=buf) is False
    assert config_mod.set_config("unknown_key", "123", console=buf) is False

    reloaded = config_mod.load_config()
    assert reloaded["user_name"] == "Sepi"
    assert reloaded["animations_enabled"] is False

    cycled = config_mod.toggle_or_cycle_config(reloaded, "brain_provider")
    assert cycled["brain_provider"] == "ollama"

    fresh = config_mod.reset_config()
    assert fresh == config_mod.DEFAULTS


def test_journal_logging_and_bounding(tmp_path, monkeypatch):
    monkeypatch.setenv("CASTLE_DIR", str(tmp_path))
    monkeypatch.setattr(journal_mod, "MAX_JOURNAL_ENTRIES", 5)

    for i in range(8):
        journal_mod.log_event("pomo", "start", f"mission {i}", ok=True)

    recent = journal_mod.get_recent_events(limit=10)
    assert len(recent) == 5
    assert recent[0]["summary"] == "mission 7"
    assert recent[-1]["summary"] == "mission 3"
    assert journal_mod.get_recent_events(limit=0) == []
