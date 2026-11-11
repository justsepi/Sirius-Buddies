"""Brain factory and shared intent execution pipeline."""

from dataclasses import dataclass, field

from castle.brain.base import BrainProvider, IntentPlan
from castle.brain.router import DeterministicBrain
from castle.buddies.base import BuddyResult
from castle.buddies.registry import BuddyRegistry
from castle.storage.journal import log_event


@dataclass
class ExecutionOutcome:
    """Complete outcome of planning and executing a user utterance."""

    plan: IntentPlan
    result: BuddyResult | None = None
    levelups: list[str] = field(default_factory=list)


def create_brain(config: dict) -> tuple[BrainProvider, str | None]:
    """Create the configured BrainProvider, falling back safely to DeterministicBrain."""
    provider = str(config.get("brain_provider", "deterministic")).strip().lower()
    if provider == "deterministic":
        return DeterministicBrain(), None
    if provider == "ollama":
        return DeterministicBrain(), (
            "Local Ollama brain is planned for v0.2+; running offline deterministic router."
        )
    return DeterministicBrain(), f"Unknown brain_provider '{provider}'; using deterministic router."


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
        memory_updates={"last_dispatched_buddy": buddy_id, "last_action": action},
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
