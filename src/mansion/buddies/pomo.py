"""Pomo resident — adopts standalone pomoclk into the Mansion Clocktower."""

from datetime import date, timedelta
import importlib.util
import os
from pathlib import Path
import shlex
import shutil
import sys

from mansion.buddies.base import ActionSpec, BaseBuddy, BuddyResult, BuddyStatus
from mansion.storage import read_json

POMO_PRESETS = ("classic", "quick", "deep", "sprint")

POMO_CONFIG_DEFAULTS = {
    "focus_minutes": 25,
    "short_break_minutes": 5,
    "long_break_minutes": 15,
    "pomos_before_long_break": 4,
    "sound_enabled": True,
    "toast_enabled": True,
}


def get_pomoclk_dir() -> Path:
    """Return ~/.pomoclk or POMOCLK_DIR env override."""
    override = os.environ.get("POMOCLK_DIR", "").strip()
    return Path(override) if override else (Path.home() / ".pomoclk")


def _fmt_duration(secs: int) -> str:
    if 0 < secs < 60:
        return f"{secs}s"
    return f"{secs // 60}m"


def get_pomo_today_stats() -> dict:
    """Compute today's Pomodoro stats directly from ~/.pomoclk/history.json."""
    history = read_json(get_pomoclk_dir() / "history.json", [])
    today_str = date.today().isoformat()
    today_sessions = [s for s in history if isinstance(s, dict) and s.get("date") == today_str]

    completed = sum(1 for s in today_sessions if s.get("completed"))
    total_secs = sum(int(s.get("duration_secs", 0)) for s in today_sessions)
    tasks: dict[str, int] = {}
    for s in today_sessions:
        label = s.get("task") or "(no label)"
        tasks[label] = tasks.get(label, 0) + int(s.get("duration_secs", 0))

    return {
        "date": today_str,
        "completed": completed,
        "total_secs": total_secs,
        "total_fmt": _fmt_duration(total_secs),
        "tasks": sorted(tasks.items(), key=lambda item: -item[1]),
    }


def get_pomo_history_rows(days: int = 7) -> list[tuple[str, str, str, str]]:
    """Return formatted (date, pomos, focus, top_task) tuples for the last N days."""
    history = read_json(get_pomoclk_dir() / "history.json", [])
    cutoff = (date.today() - timedelta(days=max(days - 1, 0))).isoformat()

    by_date: dict[str, list[dict]] = {}
    for s in history:
        if isinstance(s, dict) and str(s.get("date", "")) >= cutoff:
            by_date.setdefault(s["date"], []).append(s)

    rows: list[tuple[str, str, str, str]] = []
    for day_str in sorted(by_date.keys(), reverse=True):
        sessions = by_date[day_str]
        pomos = sum(1 for s in sessions if s.get("completed"))
        total_secs = sum(int(s.get("duration_secs", 0)) for s in sessions)
        tasks: dict[str, int] = {}
        for s in sessions:
            label = s.get("task") or "-"
            tasks[label] = tasks.get(label, 0) + int(s.get("duration_secs", 0))
        top_task = max(tasks, key=tasks.get) if tasks else "-"
        rows.append((day_str, str(pomos), _fmt_duration(total_secs), top_task))
    return rows


def get_pomo_config() -> dict:
    """Load ~/.pomoclk/config.json merged with pomoclk defaults."""
    user = read_json(get_pomoclk_dir() / "config.json", {})
    return {**POMO_CONFIG_DEFAULTS, **user}


def resolve_pomo_command(config: dict | None = None) -> list[str] | None:
    """Resolve the standalone `pomo` executable or python module across OSes."""
    override = (config or {}).get("pomo_command", "").strip()
    if override:
        parts = shlex.split(override, posix=(os.name != "nt"))
        if parts:
            exe = shutil.which(parts[0])
            if exe or Path(parts[0]).exists():
                return [exe or parts[0], *parts[1:]]

    on_path = shutil.which("pomo")
    if on_path:
        return [on_path]

    if sys.platform == "win32":
        win_exe = Path(sys.executable).parent / "pomo.exe"
        if win_exe.exists():
            return [str(win_exe)]
    else:
        local_bin = Path.home() / ".local" / "bin" / "pomo"
        if local_bin.exists():
            return [str(local_bin)]

    if importlib.util.find_spec("pomoclk") is not None:
        return [sys.executable, "-m", "pomoclk.cli"]

    return None


class PomoBuddy(BaseBuddy):
    """Pomo the Pomidor — Clocktower keeper for focus timers & stats."""

    id = "pomo"
    default_name = "Pomo"
    default_room = "Clocktower"
    task_summary = "Focus sprints, Pomodoro timer, & time tracking"
    aliases = ("pomo", "pomidor", "pomoclk", "clocktower", "focus", "timer")
    CORE_VERSION = 1
    RANKS = (
        (0, "Seed"),
        (30, "Sprout"),
        (90, "Pomidor"),
        (200, "Clockmaster"),
        (400, "Timelord"),
    )
    actions = (
        ActionSpec("open", "Launch Pomo's full interactive TUI", ("open pomo",), interactive=True),
        ActionSpec(
            "start",
            "Start a focus timer session",
            ("start deep focus on api", "focus 25m on writing"),
            interactive=True,
        ),
        ActionSpec("status", "Check today's pomodoros and focus minutes", ("pomo status",)),
        ActionSpec("history", "Browse multi-day focus history", ("pomo history 14 days",)),
        ActionSpec("config", "Inspect Pomo's current configuration", ("pomo config",)),
    )

    def check_status(self, config: dict) -> BuddyStatus:
        cmd = resolve_pomo_command(config)
        stats = get_pomo_today_stats()
        summary = f"Today: {stats['completed']} pomos · {stats['total_fmt']}"
        if cmd:
            return BuddyStatus(
                available=True,
                state_label="online",
                summary=summary,
                detail=f"cmd: {' '.join(cmd)}",
            )
        return BuddyStatus(
            available=False,
            state_label="not installed",
            summary=summary,
            detail="Install pomoclk or set `pomo_command` in Mansion config.",
        )

    def execute(self, action: str, params: dict, config: dict) -> BuddyResult:
        soul = self.load_soul()
        self.load_core()

        if action == "status":
            stats = get_pomo_today_stats()
            msg = soul.react(
                "status",
                completed=stats["completed"],
                total_fmt=stats["total_fmt"],
            )
            rows = [(task, _fmt_duration(secs)) for task, secs in stats["tasks"]]
            return BuddyResult(
                ok=True,
                message=msg,
                mood="happy",
                table_headers=("Task", "Focus") if rows else None,
                table_rows=rows,
                meta={"xp_gain": 2},
            )

        if action == "history":
            days = max(1, int(params.get("days", 7)))
            rows = get_pomo_history_rows(days=days)
            msg = (
                f"{soul.signature} Last {days} days in the Clocktower ({len(rows)} active days)."
                if rows
                else f"{soul.signature} No Clocktower sessions logged in the last {days} days yet."
            )
            return BuddyResult(
                ok=True,
                message=msg,
                mood="happy",
                table_headers=("Date", "🍅", "Focus", "Top Task") if rows else None,
                table_rows=rows,
                meta={"xp_gain": 2},
            )

        if action == "config":
            pomo_cfg = get_pomo_config()
            rows = [(k, str(v)) for k, v in pomo_cfg.items()]
            return BuddyResult(
                ok=True,
                message=f"{soul.signature} Pomo's Clocktower settings:",
                mood="happy",
                table_headers=("Setting", "Value"),
                table_rows=rows,
                meta={"xp_gain": 1},
            )

        cmd = resolve_pomo_command(config)
        if not cmd:
            return BuddyResult(
                ok=False,
                message=soul.react("missing"),
                mood="curious",
            )

        if action == "open":
            extra = [str(a) for a in params.get("raw_args", [])]
            return BuddyResult(
                ok=True,
                message=soul.react("greet", summary="Opening Pomo's Clocktower!"),
                mood="working",
                interactive_cmd=[*cmd, *extra],
                meta={"xp_gain": 5, "machine_updates": {"pomo_available": True, "pomo_cmd": cmd[0]}},
            )

        if action == "start":
            cli_cmd = [*cmd, "start"]
            desc_parts: list[str] = []
            preset = str(params.get("preset", "")).lower().strip()
            if preset in POMO_PRESETS:
                cli_cmd.extend(["-p", preset])
                desc_parts.append(preset)
            focus = params.get("focus")
            if isinstance(focus, int) and focus >= 1:
                cli_cmd.extend(["--focus", str(focus)])
                desc_parts.append(f"{focus}m")
            task = str(params.get("task", "")).strip()
            if task:
                cli_cmd.extend(["-t", task])
                desc_parts.append(f"'{task}'")

            detail = " ".join(desc_parts) if desc_parts else "a fresh focus session"
            mem_updates = {}
            if preset in POMO_PRESETS:
                mem_updates["last_preset"] = preset
            if task:
                mem_updates["last_task"] = task

            return BuddyResult(
                ok=True,
                message=soul.react("start", detail=detail),
                mood="working",
                interactive_cmd=cli_cmd,
                meta={
                    "xp_gain": 15,
                    "memory_updates": mem_updates,
                    "machine_updates": {"pomo_available": True, "pomo_cmd": cmd[0]},
                },
            )

        return BuddyResult(
            ok=False,
            message=f"{soul.signature} Pomo doesn't recognize action '{action}'.",
            mood="curious",
        )

    def badge_lines(self, frame: int = 0) -> list[tuple[str, str]]:
        eyes = " - - " if (frame % 12) == 11 else " o o "
        return [
            ("  \\|/  ", "bold bright_green"),
            (f" █{eyes}█ ", "bold bright_white on red"),
            ("  ▀▀▀  ", "red"),
        ]
