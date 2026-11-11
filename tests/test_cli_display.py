"""Tests for Rich retro screens, narrow width, zero AI/chat clutter, and CLI commands."""

from types import SimpleNamespace

from rich.console import Console

from castle.buddies.base import BuddyResult
import castle.buddies.pomo as pomo_mod
from castle.buddies.registry import BuddyRegistry
import castle.cli as cli_mod
from castle.storage.config import DEFAULTS
from castle.ui.display import Display


def test_display_renders_all_screens_narrow_width_and_no_chat_box(tmp_path, monkeypatch):
    monkeypatch.setenv("CASTLE_DIR", str(tmp_path / "castle"))
    monkeypatch.setenv("POMOCLK_DIR", str(tmp_path / "pomo"))
    monkeypatch.setattr(pomo_mod, "resolve_pomo_command", lambda cfg=None: ["pomo"])

    narrow = Console(record=True, width=42)
    display = Display()
    registry = BuddyRegistry()
    snapshots = registry.snapshot_all(DEFAULTS)

    narrow.print(
        display.render_home_screen(
            version="1.0.0b0",
            snapshots=snapshots,
            sirius_reply="✦ Yo dude—rig looks solid.",
            sirius_mood="smug",
            selected_idx=0,
            frame=0,
            show_shadow=True,
            host_label="macbook",
            target_console=narrow,
        )
    )
    narrow.print(
        display.render_helper_screen(
            title="SYSTEM PULSE",
            sirius_reply="✦ All good, dude.",
            sirius_mood="happy",
            result=BuddyResult(
                ok=True,
                message="ok",
                table_headers=("Vital", "Reading"),
                table_rows=[("Host", "macbook")],
            ),
            target_console=narrow,
        )
    )
    narrow.print(display.render_timer_screen(25, 1500, False, False, target_console=narrow))
    narrow.print(display.render_moods_screen(2, target_console=narrow))
    narrow.print(display.render_toys_screen("✦ Flip!", "wink", "HEADS ✦", target_console=narrow))
    narrow.print(display.render_directory_screen(snapshots, selected_idx=1, target_console=narrow))
    narrow.print(display.render_soul_screen(snapshots[0].soul, snapshots[0].core, target_console=narrow))
    narrow.print(
        display.render_log_screen(
            [{"timestamp": "2026-11-11T17:30:00", "buddy": "sirius", "action": "pulse", "summary": "ok"}],
            target_console=narrow,
        )
    )
    narrow.print(display.render_config_screen(DEFAULTS, selected_idx=0, target_console=narrow))
    narrow.print(display.render_goodbye_screen("✦ Peace out, dude!", snapshots[0].core, target_console=narrow))

    out = narrow.export_text()
    assert "SIRIUS & THE CASTLE" in out
    assert "Sirius" in out
    assert "Pomo" in out
    assert "░" in out  # visible shadow rendered
    assert "sirius ›" not in out  # no AI chat box
    assert "ollama" not in out.lower()
    for line in out.splitlines():
        assert len(line) <= 42


def test_cli_subcommands_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CASTLE_DIR", str(tmp_path / "castle"))
    monkeypatch.setenv("POMOCLK_DIR", str(tmp_path / "pomo"))
    monkeypatch.setattr(pomo_mod, "resolve_pomo_command", lambda cfg=None: ["pomo"])

    work = tmp_path / "proj"
    work.mkdir()
    cache = work / "__pycache__"
    cache.mkdir()
    (cache / "a.pyc").write_bytes(b"123")

    assert cli_mod.main(["status"]) == 0
    assert cli_mod.main(["pulse"]) == 0
    assert cli_mod.main(["repo", str(work)]) == 0
    assert cli_mod.main(["ports"]) == 0
    assert cli_mod.main(["sweep", str(work)]) == 0
    assert cache.exists()  # dry run preserves cache
    assert cli_mod.main(["sweep", str(work), "--clean", "--yes"]) == 0
    assert not cache.exists()

    assert cli_mod.main(["poke"]) == 0
    assert cli_mod.main(["snack", "espresso"]) == 0
    assert cli_mod.main(["flip"]) == 0
    assert cli_mod.main(["roll", "20"]) == 0
    assert cli_mod.main(["oracle"]) == 0
    assert cli_mod.main(["mood"]) == 0
    assert cli_mod.main(["mood", "smug"]) == 0
    assert cli_mod.main(["buddies"]) == 0
    assert cli_mod.main(["soul", "sirius"]) == 0
    assert cli_mod.main(["pomo", "status"]) == 0
    assert cli_mod.main(["config", "user_name", "Sepi"]) == 0
    assert cli_mod.main(["log"]) == 0

    captured = capsys.readouterr().out
    assert "Sirius" in captured
    assert "Pomo" in captured
    assert "Sepi" in captured
    assert "░" in captured

    launched = []

    def fake_run(cmd, **_kwargs):
        launched.append(cmd)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli_mod.subprocess, "run", fake_run)
    assert cli_mod.main(["pomo", "start", "-p", "sprint", "-t", "tests"]) == 0
    assert launched == [["pomo", "start", "-p", "sprint", "-t", "tests"]]
