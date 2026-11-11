"""Base buddy protocol and shared soul/core lifecycle helpers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from castle.buddies.core import DEFAULT_RANKS, load_or_evolve_core, record_mission
from castle.buddies.soul import SoulProfile, load_soul


@dataclass(frozen=True)
class ActionSpec:
    """Describes one capability a buddy can execute."""

    name: str
    description: str
    examples: tuple[str, ...] = ()
    interactive: bool = False


@dataclass(frozen=True)
class BuddyStatus:
    """Live availability and short summary for a Castle buddy."""

    available: bool
    state_label: str
    summary: str
    detail: str = ""


@dataclass
class BuddyResult:
    """Structured result returned by executing a buddy action."""

    ok: bool
    message: str
    mood: str = "happy"
    interactive_cmd: list[str] | None = None
    table_headers: tuple[str, ...] | None = None
    table_rows: list[tuple[str, ...]] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


class BaseBuddy(ABC):
    """Contract implemented by Sirius and every specialist Castle cyber buddy."""

    id: str = ""
    default_name: str = ""
    default_room: str = ""
    task_summary: str = ""
    aliases: tuple[str, ...] = ()
    CORE_VERSION: int = 1
    RANKS: tuple[tuple[int, str], ...] = DEFAULT_RANKS
    actions: tuple[ActionSpec, ...] = ()

    def load_soul(self) -> SoulProfile:
        """Load (and initialize if missing) this buddy's local soul.md."""
        return load_soul(self.id)

    def migrate_core(self, core: dict, next_version: int) -> dict:
        """Override in subclasses to migrate core.json fields between CORE_VERSIONs."""
        return core

    def load_core(self) -> tuple[dict, bool]:
        """Load and automatically evolve/migrate this buddy's core.json."""
        soul = self.load_soul()
        return load_or_evolve_core(
            buddy_id=self.id,
            target_version=self.CORE_VERSION,
            soul_version=soul.soul_version,
            room=soul.room or self.default_room,
            ranks=self.RANKS,
            migrate_fn=self.migrate_core,
        )

    def record_mission(
        self,
        xp_gain: int = 10,
        memory_updates: dict | None = None,
        machine_updates: dict | None = None,
    ) -> tuple[dict, bool]:
        """Award XP, persist memories/machine facts, and return (core, leveled_up)."""
        soul = self.load_soul()
        return record_mission(
            buddy_id=self.id,
            xp_gain=xp_gain,
            ranks=self.RANKS,
            memory_updates=memory_updates,
            machine_updates=machine_updates,
            target_version=self.CORE_VERSION,
            soul_version=soul.soul_version,
            room=soul.room or self.default_room,
            migrate_fn=self.migrate_core,
        )

    @abstractmethod
    def check_status(self, config: dict) -> BuddyStatus:
        """Return live availability and concise status for the Castle Directory."""

    @abstractmethod
    def execute(self, action: str, params: dict, config: dict) -> BuddyResult:
        """Execute a named buddy action and return a BuddyResult."""

    def badge_lines(self, frame: int = 0) -> list[tuple[str, str]]:
        """Return compact colored ASCII lines representing this buddy."""
        return [
            (" ╭───╮ ", "bright_cyan"),
            (" │★ ★│ ", "bold bright_cyan"),
            (" ╰───╯ ", "bright_cyan"),
        ]
