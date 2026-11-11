"""Sirius — Master & Brain resident definition."""

from castle.buddies.base import ActionSpec, BaseBuddy, BuddyResult, BuddyStatus


class SiriusBuddy(BaseBuddy):
    """Master resident of the Castle who coordinates all other buddies."""

    id = "sirius"
    default_name = "Sirius"
    default_room = "Master Study"
    task_summary = "Castle brain, orchestration, & core keeper"
    aliases = ("sirius", "master", "study", "brain")
    CORE_VERSION = 1
    RANKS = (
        (0, "Spark"),
        (30, "Lantern"),
        (90, "Beacon"),
        (200, "Northstar"),
        (400, "Luminary"),
    )
    actions = (
        ActionSpec("status", "Show Castle overview and resident summaries"),
        ActionSpec("buddies", "Inspect all residents, rooms, and evolving cores"),
        ActionSpec("log", "Show recent Castle mission chronicle"),
        ActionSpec("help", "Explain what Sirius and the Castle can do"),
    )

    def check_status(self, config: dict) -> BuddyStatus:
        core, _ = self.load_core()
        provider = config.get("brain_provider", "deterministic")
        return BuddyStatus(
            available=True,
            state_label="online",
            summary=f"brain: {provider} · {core['missions_completed']} missions",
            detail=f"{core['xp']} XP",
        )

    def execute(self, action: str, params: dict, config: dict) -> BuddyResult:
        soul = self.load_soul()
        core, _ = self.load_core()
        user = config.get("user_name", "friend")
        if action == "help":
            return BuddyResult(
                ok=True,
                message=soul.react("help", user=user, level=core["level"], rank=core["rank"]),
                mood="happy",
            )
        return BuddyResult(
            ok=True,
            message=soul.react(
                "greet",
                user=user,
                summary=f"Core Lv.{core['level']} ({core['rank']}) active.",
            ),
            mood="happy",
        )

    def badge_lines(self, frame: int = 0) -> list[tuple[str, str]]:
        eyes = " - - " if (frame % 12) == 11 else " ★ ★ "
        return [
            (" ╭───╮ ", "bright_cyan"),
            (f" │{eyes[:5]}│ ", "bold bright_cyan"),
            (" ╰─◡─╯ ", "bright_cyan"),
        ]
