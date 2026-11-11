"""Registry of Mansion residents (Sirius + specialist cyber buddies)."""

from dataclasses import dataclass

from mansion.buddies.base import BaseBuddy, BuddyStatus
from mansion.buddies.pomo import PomoBuddy
from mansion.buddies.sirius import SiriusBuddy
from mansion.buddies.soul import SoulProfile


@dataclass
class BuddySnapshot:
    """Combined live snapshot of a buddy's soul, core, and runtime status."""

    buddy: BaseBuddy
    soul: SoulProfile
    core: dict
    status: BuddyStatus
    evolved: bool = False


class BuddyRegistry:
    """Manages Sirius and all resident cyber buddies in the Mansion."""

    def __init__(self) -> None:
        self._sirius = SiriusBuddy()
        self._specialists: list[BaseBuddy] = [
            PomoBuddy(),
        ]
        self._by_id: dict[str, BaseBuddy] = {
            self._sirius.id: self._sirius,
            **{b.id: b for b in self._specialists},
        }

    @property
    def sirius(self) -> SiriusBuddy:
        """Return the Master buddy (Sirius)."""
        return self._sirius

    def specialists(self) -> list[BaseBuddy]:
        """Return specialist cyber buddies (excluding Sirius)."""
        return list(self._specialists)

    def all_buddies(self) -> list[BaseBuddy]:
        """Return Sirius followed by all specialist residents."""
        return [self._sirius, *self._specialists]

    def get(self, name_or_alias: str) -> BaseBuddy | None:
        """Look up any buddy by id, name, room, or registered alias."""
        needle = name_or_alias.strip().lower()
        if not needle:
            return None
        if needle in self._by_id:
            return self._by_id[needle]
        for buddy in self.all_buddies():
            soul = buddy.load_soul()
            candidates = {
                buddy.id.lower(),
                buddy.default_name.lower(),
                buddy.default_room.lower(),
                soul.name.lower(),
                soul.room.lower(),
                *(a.lower() for a in buddy.aliases),
            }
            if needle in candidates:
                return buddy
        return None

    def snapshot_all(self, config: dict) -> list[BuddySnapshot]:
        """Load souls, evolve/migrate cores, and gather live status for all residents."""
        snapshots: list[BuddySnapshot] = []
        for buddy in self.all_buddies():
            soul = buddy.load_soul()
            core, evolved = buddy.load_core()
            status = buddy.check_status(config)
            snapshots.append(
                BuddySnapshot(
                    buddy=buddy,
                    soul=soul,
                    core=core,
                    status=status,
                    evolved=evolved,
                )
            )
        return snapshots
