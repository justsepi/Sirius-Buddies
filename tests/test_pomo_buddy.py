"""Tests for PomoBuddy adoption and standalone pomoclk data integration."""

from datetime import date
import json

import castle.buddies.pomo as pomo_mod
from castle.buddies.pomo import PomoBuddy


def test_pomo_reads_pomoclk_history_and_status(tmp_path, monkeypatch):
    castle_dir = tmp_path / "castle"
    pomo_dir = tmp_path / "pomoclk"
    pomo_dir.mkdir()
    monkeypatch.setenv("CASTLE_DIR", str(castle_dir))
    monkeypatch.setenv("POMOCLK_DIR", str(pomo_dir))

    today = date.today().isoformat()
    (pomo_dir / "history.json").write_text(
        json.dumps([
            {"date": today, "start": f"{today}T10:00:00", "task": "api", "duration_secs": 1500, "completed": True},
            {"date": today, "start": f"{today}T11:00:00", "task": "docs", "duration_secs": 600, "completed": False},
        ]),
        encoding="utf-8",
    )

    buddy = PomoBuddy()
    monkeypatch.setattr(pomo_mod, "resolve_pomo_command", lambda cfg=None: ["pomo"])

    status = buddy.check_status({})
    assert status.available is True
    assert "1 pomos" in status.summary
    assert "35m" in status.summary

    res_status = buddy.execute("status", {}, {})
    assert res_status.ok is True
    assert "1 pomos" in res_status.message
    assert ("api", "25m") in res_status.table_rows

    res_hist = buddy.execute("history", {"days": 7}, {})
    assert res_hist.ok is True
    assert len(res_hist.table_rows) == 1
    assert res_hist.table_rows[0][0] == today


def test_pomo_start_builds_flags_and_handles_missing_cli(tmp_path, monkeypatch):
    monkeypatch.setenv("CASTLE_DIR", str(tmp_path / "castle"))
    monkeypatch.setenv("POMOCLK_DIR", str(tmp_path / "empty_pomo"))
    buddy = PomoBuddy()

    monkeypatch.setattr(pomo_mod, "resolve_pomo_command", lambda cfg=None: ["pomo"])
    res = buddy.execute("start", {"preset": "deep", "focus": 45, "task": "backend"}, {})
    assert res.ok is True
    assert res.interactive_cmd == ["pomo", "start", "-p", "deep", "--focus", "45", "-t", "backend"]
    assert res.meta["memory_updates"]["last_preset"] == "deep"

    monkeypatch.setattr(pomo_mod, "resolve_pomo_command", lambda cfg=None: None)
    missing = buddy.execute("start", {}, {})
    assert missing.ok is False
    assert "not" in missing.message.lower() or "isn't" in missing.message.lower()
