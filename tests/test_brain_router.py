"""Tests for DeterministicBrain intent routing and soul.md-backed responses."""

from mansion.brain import create_brain
from mansion.buddies.registry import BuddyRegistry
from mansion.storage.config import load_config


def test_brain_routes_mansion_and_slash_commands(tmp_path, monkeypatch):
    monkeypatch.setenv("MANSION_DIR", str(tmp_path / "mansion"))
    monkeypatch.setenv("POMOCLK_DIR", str(tmp_path / "pomo"))

    cfg = load_config()
    cfg["user_name"] = "Sepi"
    registry = BuddyRegistry()
    brain, notice = create_brain(cfg)
    assert notice is None

    greet = brain.plan("", registry, cfg)
    assert greet.target == "sirius"
    assert greet.action == "greet"
    assert "Sepi" in greet.reply

    assert brain.plan("hello sirius", registry, cfg).action == "greet"
    assert brain.plan("/buddies", registry, cfg).action == "buddies"
    assert brain.plan("who lives in the mansion?", registry, cfg).action == "buddies"
    assert brain.plan("/log", registry, cfg).action == "log"
    assert brain.plan("soul pomo", registry, cfg).params["buddy"] == "pomo"
    assert brain.plan("goodnight", registry, cfg).action == "quit"

    unknown = brain.plan("bake me a cosmic pizza", registry, cfg)
    assert unknown.target == "sirius"
    assert unknown.action == "unknown"
    assert unknown.confidence == 0.0


def test_brain_extracts_pomo_presets_minutes_and_tasks(tmp_path, monkeypatch):
    monkeypatch.setenv("MANSION_DIR", str(tmp_path / "mansion"))
    monkeypatch.setenv("POMOCLK_DIR", str(tmp_path / "pomo"))

    cfg = load_config()
    registry = BuddyRegistry()
    brain, _ = create_brain(cfg)

    p1 = brain.plan("start deep work on sirius brain", registry, cfg)
    assert p1.target == "pomo"
    assert p1.action == "start"
    assert p1.params["preset"] == "deep"
    assert p1.params["task"] == "sirius brain"

    p2 = brain.plan("focus on writing for 45m", registry, cfg)
    assert p2.target == "pomo"
    assert p2.action == "start"
    assert p2.params["focus"] == 45
    assert p2.params["task"] == "writing"

    p3 = brain.plan("how many pomos today?", registry, cfg)
    assert p3.target == "pomo"
    assert p3.action == "status"

    p4 = brain.plan("show pomo history 14 days", registry, cfg)
    assert p4.target == "pomo"
    assert p4.action == "history"
    assert p4.params["days"] == 14

    p5 = brain.plan("open pomo", registry, cfg)
    assert p5.target == "pomo"
    assert p5.action == "open"
