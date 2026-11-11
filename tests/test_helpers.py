"""Tests for Sirius pure-offline device helpers and buddy interactions."""

import shutil
import subprocess

import pytest

from castle.helpers.buddy_toys import (
    cosmic_oracle,
    feed_sirius,
    flip_coin,
    poke_sirius,
    roll_dice,
)
import castle.helpers.ports as ports_mod
from castle.helpers.ports import _parse_lsof_output, _parse_windows_netstat, inspect_ports
from castle.helpers.repo import inspect_workspace
from castle.helpers.sweep import clean_safe_caches, scan_clutter
from castle.helpers.vitals import SystemVitals, DiskStat, format_vitals_report, gather_vitals


def test_vitals_gather_and_warning_expressions():
    vitals = gather_vitals()
    assert vitals.cpu_cores >= 1
    assert vitals.hostname
    assert len(vitals.disks) >= 1

    mood, comment, rows = format_vitals_report(vitals)
    assert mood in ("chill", "happy", "smug", "curious", "unimpressed", "alarmed")
    assert "dude" in comment.lower()
    assert len(rows) >= 5

    # Simulate low battery & full disk warnings
    critical = SystemVitals(
        hostname="test-box",
        os_label="macOS 15.0",
        arch="arm64",
        shell="zsh",
        python_version="3.12.0",
        uptime="1h 5m",
        cpu_cores=8,
        cpu_detail="8 cores",
        ram_used=4_000_000_000,
        ram_total=16_000_000_000,
        ram_percent=25.0,
        disks=[DiskStat("/", 950, 1000, 50, 95.0)],
        battery_percent=12,
        battery_plugged=False,
        local_ip="192.168.1.5",
    )
    crit_mood, crit_comment, _ = format_vitals_report(critical)
    assert crit_mood == "alarmed"
    assert "95%" in crit_comment


def test_repo_scout_git_and_plain_folder(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    plain_rep = inspect_workspace(plain)
    assert plain_rep.is_git is False
    assert "Python (pyproject)" in plain_rep.stack

    if not shutil.which("git"):
        pytest.skip("git not installed")

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "dude@example.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Dude"], cwd=repo, check=True, capture_output=True)
    (repo / "app.py").write_text("print('hi')\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)

    clean_rep = inspect_workspace(repo)
    assert clean_rep.is_git is True
    assert clean_rep.mood == "proud"

    (repo / "dirty.txt").write_text("wip\n", encoding="utf-8")
    dirty_rep = inspect_workspace(repo)
    assert dirty_rep.untracked == 1
    assert dirty_rep.mood == "curious"


def test_ports_inspector_windows_macos_and_loopback(monkeypatch):
    win_sample = (
        "  TCP    127.0.0.1:8000         0.0.0.0:0              LISTENING       4242\n"
        "  TCP    0.0.0.0:5173           0.0.0.0:0              LISTENING       9001\n"
    )
    win_parsed = _parse_windows_netstat(win_sample, {4242: "python.exe", 9001: "node.exe"})
    assert win_parsed == {8000: "python.exe", 5173: "node.exe"}

    mac_sample = (
        "COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME\n"
        "node    12345 sepi   22u  IPv6 0x1234      0t0  TCP *:3000 (LISTEN)\n"
        "python3 54321 sepi    4u  IPv4 0x5678      0t0  TCP 127.0.0.1:8000 (LISTEN)\n"
    )
    mac_parsed = _parse_lsof_output(mac_sample)
    assert mac_parsed == {3000: "node (12345)", 8000: "python3 (54321)"}

    monkeypatch.setattr(ports_mod, "_discover_os_listeners", lambda: {3000: "node.exe"})
    monkeypatch.setattr(ports_mod, "_probe_loopback", lambda port, timeout=0.04: port == 8000)

    report = inspect_ports([3000, 8000, 9999])
    states = {e.port: e.state for e in report.entries}
    assert states[3000] == "LISTENING"
    assert states[8000] == "LISTENING"
    assert states[9999] == "free"
    assert report.listening_count == 2


def test_sweep_scans_and_safely_cleans_only_safe_caches(tmp_path):
    src_file = tmp_path / "main.py"
    src_file.write_text("x = 1\n", encoding="utf-8")

    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "main.cpython-315.pyc").write_bytes(b"0" * 2048)

    ds_store = tmp_path / ".DS_Store"
    ds_store.write_bytes(b"1234")

    node_mods = tmp_path / "node_modules" / "pkg"
    node_mods.mkdir(parents=True)
    (node_mods / "index.js").write_text("module.exports = {}\n", encoding="utf-8")

    report = scan_clutter(tmp_path)
    assert report.safe_count == 2
    assert report.heavy_count == 1
    assert report.safe_bytes >= 2052

    removed, freed, errors = clean_safe_caches(report)
    assert errors == []
    assert removed == 2
    assert freed >= 2052
    assert not pycache.exists()
    assert not ds_store.exists()
    assert src_file.exists()
    assert (node_mods / "index.js").exists()


def test_buddy_toys_interactions():
    p0 = poke_sirius(0)
    p3 = poke_sirius(3)
    assert p0.mood != p3.mood
    assert "dude" in p0.message.lower()

    snack = feed_sirius(70, "espresso")
    assert snack.charge == 90
    assert snack.mood == "hyped"

    assert flip_coin().headline in ("HEADS ✦", "TAILS ○")
    assert "d20" in roll_dice(20).headline
    assert "✦" in cosmic_oracle().message
