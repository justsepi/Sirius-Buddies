"""Tests for Castle offline config and bounded journal storage."""

from rich.console import Console

from castle.storage import write_json
import castle.storage.config as config_mod
import castle.storage.journal as journal_mod


def test_config_defaults_save_and_validation(tmp_path, monkeypatch):
    monkeypatch.setenv("CASTLE_DIR", str(tmp_path))

    cfg = config_mod.load_config()
    assert cfg["user_name"] == "dude"
    assert cfg["animations_enabled"] is True
    assert cfg["show_shadow"] is True
    assert "brain_provider" not in cfg
    assert "ollama_model" not in cfg

    # Legacy keys in an old config.json are ignored cleanly
    write_json(config_mod.get_config_file(), {"user_name": "Sepi", "brain_provider": "ollama"})
    migrated = config_mod.load_config()
    assert migrated["user_name"] == "Sepi"
    assert "brain_provider" not in migrated

    buf = Console(record=True, width=80)
    assert config_mod.set_config("user_name", "Sepi", console=buf) is True
    assert config_mod.set_config("animations_enabled", "off", console=buf) is True
    assert config_mod.set_config("show_shadow", "false", console=buf) is True
    assert config_mod.set_config("user_name", "   ", console=buf) is False
    assert config_mod.set_config("unknown_key", "123", console=buf) is False

    reloaded = config_mod.load_config()
    assert reloaded["user_name"] == "Sepi"
    assert reloaded["animations_enabled"] is False
    assert reloaded["show_shadow"] is False

    toggled = config_mod.toggle_or_cycle_config(reloaded, "animations_enabled")
    assert toggled["animations_enabled"] is True

    fresh = config_mod.reset_config()
    assert fresh == config_mod.DEFAULTS


def test_journal_logging_and_bounding(tmp_path, monkeypatch):
    monkeypatch.setenv("CASTLE_DIR", str(tmp_path))
    monkeypatch.setattr(journal_mod, "MAX_JOURNAL_ENTRIES", 5)

    for i in range(8):
        journal_mod.log_event("sirius", "pulse", f"mission {i}", ok=True)

    recent = journal_mod.get_recent_events(limit=10)
    assert len(recent) == 5
    assert recent[0]["summary"] == "mission 7"
    assert recent[-1]["summary"] == "mission 3"
    assert journal_mod.get_recent_events(limit=0) == []
