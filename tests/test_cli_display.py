"""Tests for Castle Rich UI screens and Sirius CLI subcommands."""

from types import SimpleNamespace
from rich.console import Console

import castle.buddies.pomo as pomo_mod
import castle.cli as cli_mod
from castle.buddies.registry import BuddyRegistry
from castle.storage.config import DEFAULTS
from castle.ui.display import Display


def test_display_renders_all_screens_and_respects_narrow_width(tmp_path, monkeypatch):
    monkeypatch.setenv("CASTLE_DIR", str(tmp_path / "castle"))
    monkeypatch.setenv("POMOCLK_DIR", str(tmp_path / "pomo"))
    monkeypatch.setattr(pomo_mod, "resolve_pomo_command", lambda cfg=None: ["pomo"])

    narrow = Console(record=True, width=42)
    display = Display()
    registry = BuddyRegistry()
    snapshots = registry.snapshot_all(DEFAULTS)

    narrow.print(
        display.render_home_screen(
            version="0.1.0",
            snapshots=snapshots,
            sirius_reply="★ Hey friend! Ready in the Master Study.",
            sirius_mood="happy",
            prompt_text="focus",
            prompt_cursor=5,
            focus_zone="prompt",
            selected_idx=0,
            frame=0,
            target_console=narrow,
        )
    )
    narrow.print(display.render_directory_screen(snapshots, selected_idx=1, frame=0, target_console=narrow))
    narrow.print(
        display.render_soul_screen(
            snapshots[0].soul,
            snapshots[0].core,
            target_console=narrow,
        )
    )
    narrow.print(
        display.render_log_screen(
            [{"timestamp": "2026-11-11T17:30:00", "buddy": "pomo", "action": "status", "summary": "ok"}],
            target_console=narrow,
        )
    )
    narrow.print(display.render_config_screen(DEFAULTS, selected_idx=0, target_console=narrow))
    narrow.print(display.render_goodbye_screen("★ Bye!", snapshots[0].core, target_console=narrow))

    out = narrow.export_text()
    assert "THE CASTLE" in out
    assert "Sirius" in out
    assert "Pomo" in out
    assert "Clocktower" in out
    for line in out.splitlines():
        assert len(line) <= 42


def test_cli_subcommands_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CASTLE_DIR", str(tmp_path / "castle"))
    monkeypatch.setenv("POMOCLK_DIR", str(tmp_path / "pomo"))
    monkeypatch.setattr(pomo_mod, "resolve_pomo_command", lambda cfg=None: ["pomo"])

    assert cli_mod.main(["status"]) == 0
    assert cli_mod.main(["buddies"]) == 0
    assert cli_mod.main(["soul", "sirius"]) == 0
    assert cli_mod.main(["ask", "how", "many", "pomos", "today"]) == 0
    assert cli_mod.main(["pomo", "status"]) == 0
    assert cli_mod.main(["config", "user_name", "Sepi"]) == 0
    assert cli_mod.main(["log"]) == 0

    captured = capsys.readouterr().out
    assert "Sirius" in captured
    assert "Pomo" in captured
    assert "Clocktower" in captured
    assert "Sepi" in captured

    launched = []

    def fake_run(cmd, **_kwargs):
        launched.append(cmd)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)
    assert cli_mod.main(["ask", "start", "sprint", "focus", "on", "tests"]) == 0
    assert launched == [["pomo", "start", "-p", "sprint", "-t", "tests"]]
