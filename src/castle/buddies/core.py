"""Versioned, evolving core state engine for Castle buddies."""

from datetime import datetime
from pathlib import Path
import platform
from typing import Callable

from castle.storage import get_data_dir, read_json, write_json

DEFAULT_RANKS: tuple[tuple[int, str], ...] = (
    (0, "Spark"),
    (30, "Sprout"),
    (90, "Companion"),
    (200, "Master"),
    (400, "Luminary"),
)

MAX_EVOLUTION_LOG = 50


def os_key() -> str:
    """Return normalized OS key ('windows', 'darwin', or 'linux')."""
    sys_name = platform.system().lower()
    if sys_name.startswith("win"):
        return "windows"
    if sys_name == "darwin":
        return "darwin"
    return "linux"


def get_core_path(buddy_id: str) -> Path:
    """Return ~/.castle/buddies/<id>/core.json path."""
    return get_data_dir() / "buddies" / buddy_id / "core.json"


def compute_level(xp: int, ranks: tuple[tuple[int, str], ...] = DEFAULT_RANKS) -> tuple[int, str]:
    """Compute (1-based level, rank title) from accumulated XP."""
    ordered = sorted(ranks, key=lambda item: item[0])
    level = 1
    rank = ordered[0][1] if ordered else "Spark"
    for idx, (threshold, title) in enumerate(ordered, start=1):
        if xp >= threshold:
            level = idx
            rank = title
    return level, rank


def _append_evolution(core: dict, message: str) -> None:
    stamp = datetime.now().isoformat(timespec="seconds")
    log = list(core.get("evolution_log") or [])
    log.append(f"{stamp} — {message}")
    if len(log) > MAX_EVOLUTION_LOG:
        log = log[-MAX_EVOLUTION_LOG:]
    core["evolution_log"] = log


def _ensure_structure(core: dict, buddy_id: str, ranks: tuple[tuple[int, str], ...]) -> dict:
    """Ensure required evolving core fields exist on loaded data."""
    now = datetime.now().isoformat(timespec="seconds")
    core.setdefault("buddy_id", buddy_id)
    core.setdefault("core_version", 1)
    core.setdefault("soul_version", 1)
    core.setdefault("xp", 0)
    core.setdefault("missions_completed", 0)
    core.setdefault("first_awakened", now)
    core.setdefault("last_active", now)
    if not isinstance(core.get("memory"), dict):
        core["memory"] = {}
    if not isinstance(core.get("machine_facts"), dict):
        core["machine_facts"] = {}
    core["machine_facts"].setdefault(os_key(), {})
    if not isinstance(core.get("evolution_log"), list):
        core["evolution_log"] = []
    lvl, rank = compute_level(int(core.get("xp", 0)), ranks)
    core["level"] = lvl
    core["rank"] = rank
    return core


def load_or_evolve_core(
    buddy_id: str,
    target_version: int = 1,
    soul_version: int = 1,
    room: str = "Castle Hall",
    ranks: tuple[tuple[int, str], ...] = DEFAULT_RANKS,
    migrate_fn: Callable[[dict, int], dict] | None = None,
) -> tuple[dict, bool]:
    """Load buddy core.json, creating or upgrading core_version if needed."""
    path = get_core_path(buddy_id)
    raw = read_json(path, {})
    evolved = False

    if not raw:
        core = _ensure_structure(
            {
                "buddy_id": buddy_id,
                "core_version": target_version,
                "soul_version": soul_version,
            },
            buddy_id=buddy_id,
            ranks=ranks,
        )
        _append_evolution(core, f"Core v{target_version} awakened in {room}.")
        write_json(path, core)
        return core, True

    core = _ensure_structure(raw, buddy_id=buddy_id, ranks=ranks)
    current_ver = int(core.get("core_version", 1))
    if current_ver < target_version:
        old_ver = current_ver
        for next_ver in range(current_ver + 1, target_version + 1):
            if migrate_fn is not None:
                core = migrate_fn(core, next_ver)
            core["core_version"] = next_ver
        _ensure_structure(core, buddy_id=buddy_id, ranks=ranks)
        _append_evolution(core, f"Upgraded core v{old_ver} -> v{target_version}.")
        evolved = True

    if int(core.get("soul_version", 1)) != soul_version:
        core["soul_version"] = soul_version
        evolved = True

    if evolved or not path.exists():
        write_json(path, core)
    return core, evolved


def record_mission(
    buddy_id: str,
    xp_gain: int = 10,
    ranks: tuple[tuple[int, str], ...] = DEFAULT_RANKS,
    memory_updates: dict | None = None,
    machine_updates: dict | None = None,
    target_version: int = 1,
    soul_version: int = 1,
    room: str = "Castle Hall",
    migrate_fn: Callable[[dict, int], dict] | None = None,
) -> tuple[dict, bool]:
    """Record a completed mission, award XP, update memories, and check level-up."""
    core, _ = load_or_evolve_core(
        buddy_id=buddy_id,
        target_version=target_version,
        soul_version=soul_version,
        room=room,
        ranks=ranks,
        migrate_fn=migrate_fn,
    )
    old_level = int(core.get("level", 1))
    core["xp"] = int(core.get("xp", 0)) + max(0, xp_gain)
    core["missions_completed"] = int(core.get("missions_completed", 0)) + 1
    core["last_active"] = datetime.now().isoformat(timespec="seconds")

    if memory_updates:
        core["memory"].update(memory_updates)
    if machine_updates:
        core["machine_facts"].setdefault(os_key(), {}).update(machine_updates)

    new_level, new_rank = compute_level(core["xp"], ranks)
    core["level"] = new_level
    core["rank"] = new_rank

    leveled_up = new_level > old_level
    if leveled_up:
        _append_evolution(core, f"Evolved to Lv.{new_level} ({new_rank})!")

    write_json(get_core_path(buddy_id), core)
    return core, leveled_up
