"""Tests for pure-keyboard interactive TUI screens and buddy handoffs."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import castle.buddies.pomo as pomo_mod
from castle.buddies.registry import BuddyRegistry
import castle.storage.config as config_mod
import castle.ui.app as app_mod
from castle.ui.display import Display


def test_directory_soul_config_moods_and_toys_screens(tmp_path, monkeypatch):
    monkeypatch.setenv("CASTLE_DIR", str(tmp_path / "castle"))
    monkeypatch.setenv("POMOCLK_DIR", str(tmp_path / "pomo"))
    monkeypatch.setattr(pomo_mod, "resolve_pomo_command", lambda cfg=None: ["pomo"])

    display = Display()
    live = MagicMock()
    registry = BuddyRegistry()
    cfg = config_mod.load_config()

    # Directory: select Pomo (DOWN) then press 's' to inspect Pomo's soul.md
    with (
        patch.object(app_mod, "flush_keys"),
        patch.object(app_mod, "read_key", side_effect=["DOWN", "s"]),
    ):
        route, picked = app_mod._run_directory_screen(display, live, registry, cfg)
    assert (route, picked) == ("soul", "pomo")

    # Directory: select Pomo then ENTER -> summon_pomo
    with (
        patch.object(app_mod, "flush_keys"),
        patch.object(app_mod, "read_key", side_effect=["DOWN", "ENTER"]),
    ):
        route, picked = app_mod._run_directory_screen(display, live, registry, cfg)
    assert (route, picked) == ("summon_pomo", "pomo")

    # Soul screen: ESC returns home
    with (
        patch.object(app_mod, "flush_keys"),
        patch.object(app_mod, "read_key", side_effect=["ESC"]),
    ):
        assert app_mod._run_soul_screen(display, live, registry, "pomo") == "home"

    # Config screen: DOWN -> ENTER toggles animations_enabled to False, then 'b' saves & returns
    with (
        patch.object(app_mod, "flush_keys"),
        patch.object(app_mod, "read_key", side_effect=["DOWN", "ENTER", "b"]),
    ):
        updated = app_mod._run_config_screen(display, live)
    assert updated["animations_enabled"] is False
    assert config_mod.load_config()["animations_enabled"] is False

    # Moods gallery: cycle right, left, then ESC back
    with (
        patch.object(app_mod, "flush_keys"),
        patch.object(app_mod, "read_key", side_effect=["RIGHT", "LEFT", "ESC"]),
    ):
        assert app_mod._run_moods_screen(display, live, cfg) == "home"

    # Toys deck: flip, roll, oracle, snack, poke, then ESC back
    with (
        patch.object(app_mod, "flush_keys"),
        patch.object(app_mod, "read_key", side_effect=["1", "2", "4", "f", "p", "ESC"]),
    ):
        assert app_mod._run_toys_screen(display, live, registry, cfg) == "home"


def test_helper_sweep_confirm_and_timer_and_run_loop(tmp_path, monkeypatch):
    monkeypatch.setenv("CASTLE_DIR", str(tmp_path / "castle"))
    monkeypatch.setenv("POMOCLK_DIR", str(tmp_path / "pomo"))
    monkeypatch.setattr(pomo_mod, "resolve_pomo_command", lambda cfg=None: ["pomo"])

    work = tmp_path / "work"
    work.mkdir()
    cache = work / "__pycache__"
    cache.mkdir()
    (cache / "x.pyc").write_bytes(b"12345")
    monkeypatch.chdir(work)

    display = Display()
    registry = BuddyRegistry()
    cfg = config_mod.load_config()
    live = MagicMock()

    # Sweep helper: press 'c' -> 'n' (cancel), then 'c' -> 'y' (confirm), then 'ESC'
    with (
        patch.object(app_mod, "flush_keys"),
        patch.object(app_mod, "read_key", side_effect=["c", "n", "c", "y", "ESC"]),
    ):
        assert app_mod._run_helper_screen(display, live, registry, cfg, "sweep") == "home"
    assert not cache.exists()

    # Quick Timer: '+' adjust, 'SPACE' toggle, 'r' reset, 'ESC' back
    with (
        patch.object(app_mod, "flush_keys"),
        patch.object(app_mod, "read_key", side_effect=["+", "SPACE", "r", "ESC"]),
    ):
        assert app_mod._run_timer_screen(display, live, registry, cfg) == "home"

    # Pomo interactive handoff suspends Live and invokes subprocess
    with patch.object(app_mod.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as mock_run:
        reply, mood = app_mod._summon_pomo_interactive(
            live,
            registry,
            cfg,
            "start",
            {"preset": "sprint", "task": "ui"},
        )
    mock_run.assert_called_once_with(["pomo", "start", "-p", "sprint", "-t", "ui"])
    live.stop.assert_called_once()
    live.start.assert_called_once()
    assert mood == "happy"
    assert "Clocktower" in reply

    # Full keyboard run_interactive loop: poke ('p'), snack ('f'), pulse ('1' then ESC), quit ('q')
    seq = iter(["p", "f", "1", "ESC", "q"])

    class DummyLive:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def update(self, *args, **kwargs):
            pass

        def stop(self):
            pass

        def start(self, *args, **kwargs):
            pass

    with (
        patch.object(app_mod, "Live", DummyLive),
        patch.object(app_mod, "flush_keys"),
        patch.object(app_mod, "read_key", side_effect=lambda timeout=0.25: next(seq)),
        patch.object(app_mod.console, "print"),
    ):
        app_mod.run_interactive("1.0.0b0")
