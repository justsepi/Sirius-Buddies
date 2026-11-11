"""Shared mission logging and buddy core evolution pipeline."""

from castle.buddies.registry import BuddyRegistry
from castle.storage.journal import log_event


def record_mission_outcome(
    buddy_id: str,
    action: str,
    summary: str,
    registry: BuddyRegistry,
    xp_gain: int = 5,
    memory_updates: dict | None = None,
    machine_updates: dict | None = None,
    ok: bool = True,
) -> list[str]:
    """Log mission to journal.json and evolve both the buddy's and Sirius's core."""
    log_event(buddy_id=buddy_id, action=action, summary=summary, ok=ok)
    levelups: list[str] = []

    target_buddy = registry.get(buddy_id)
    if target_buddy and target_buddy.id != "sirius":
        core, leveled = target_buddy.record_mission(
            xp_gain=xp_gain,
            memory_updates=memory_updates,
            machine_updates=machine_updates,
        )
        if leveled:
            soul = target_buddy.load_soul()
            levelups.append(
                soul.react("levelup", buddy=soul.name, level=core["level"], rank=core["rank"])
            )

    sirius_xp = max(2, xp_gain // 2) if buddy_id != "sirius" else xp_gain
    sirius_core, sirius_leveled = registry.sirius.record_mission(
        xp_gain=sirius_xp,
        memory_updates={
            "last_dispatched_buddy": buddy_id,
            "last_action": action,
            **(memory_updates if buddy_id == "sirius" and memory_updates else {}),
        },
        machine_updates=machine_updates if buddy_id == "sirius" else None,
    )
    if sirius_leveled:
        sirius_soul = registry.sirius.load_soul()
        levelups.append(
            sirius_soul.react(
                "levelup",
                buddy=sirius_soul.name,
                level=sirius_core["level"],
                rank=sirius_core["rank"],
            )
        )

    return levelups
