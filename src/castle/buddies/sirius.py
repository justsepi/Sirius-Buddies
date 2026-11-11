"""Sirius — Master Star & offline device-helper resident definition."""

from datetime import datetime

from castle.buddies.base import ActionSpec, BaseBuddy, BuddyResult, BuddyStatus
from castle.helpers import (
    clean_safe_caches,
    cosmic_oracle,
    feed_sirius,
    flip_coin,
    format_bytes,
    format_vitals_report,
    gather_vitals,
    inspect_ports,
    inspect_workspace,
    poke_sirius,
    roll_dice,
    scan_clutter,
)
from castle.ui.sirius_art import build_sirius_badge


def _time_greeting_key(now: datetime | None = None) -> tuple[str, str]:
    """Return (reaction_key, default_mood) based on local time of day."""
    hour = (now or datetime.now()).hour
    if 5 <= hour < 12:
        return "greet_morning", "happy"
    if 12 <= hour < 18:
        return "greet_afternoon", "chill"
    if 18 <= hour < 24:
        return "greet_evening", "smug"
    return "greet_night", "wink"


class SiriusBuddy(BaseBuddy):
    """Master resident of the Castle: floating star buddy and offline device helper."""

    id = "sirius"
    default_name = "Sirius"
    default_room = "Master Study"
    task_summary = "System pulse, git scout, port inspector, cache sweep & buddy tools"
    aliases = ("sirius", "master", "study", "star")
    CORE_VERSION = 1
    RANKS = (
        (0, "Spark"),
        (30, "Blue Dwarf"),
        (90, "Beacon"),
        (200, "Binary Star"),
        (400, "Supergiant"),
    )
    actions = (
        ActionSpec("pulse", "Inspect OS, CPU, RAM, disk, battery & local IP", ("sirius pulse",)),
        ActionSpec("repo", "Scout Git branch, dirty tree & project stack", ("sirius repo",)),
        ActionSpec("ports", "Inspect listening TCP ports and dev servers", ("sirius ports",)),
        ActionSpec("sweep", "Scan and safely tidy dev caches & junk files", ("sirius sweep",)),
        ActionSpec("timer", "Built-in offline keyboard countdown timer", ("sirius timer 25",), interactive=True),
        ActionSpec("poke", "Poke Sirius and watch his mood shift", ("sirius poke",)),
        ActionSpec("snack", "Toss Sirius a cosmic snack to top up charge", ("sirius snack",)),
        ActionSpec("flip", "Flip a cosmic coin offline", ("sirius flip",)),
        ActionSpec("roll", "Roll a die offline (default d20)", ("sirius roll 20",)),
        ActionSpec("oracle", "Get a deadpan cosmic call on a tough choice", ("sirius oracle",)),
    )

    def check_status(self, config: dict) -> BuddyStatus:
        core, _ = self.load_core()
        charge = int((core.get("memory") or {}).get("charge", 85))
        return BuddyStatus(
            available=True,
            state_label="online",
            summary=f"Lv.{core['level']} {core['rank']} · charge {charge}% · {core['missions_completed']} ops",
            detail=f"{core['xp']} XP",
        )

    def execute(self, action: str, params: dict, config: dict) -> BuddyResult:
        soul = self.load_soul()
        core, _ = self.load_core()
        memory = core.get("memory") or {}
        user = config.get("user_name", "dude")

        if action in ("greet", "idle"):
            key, default_mood = _time_greeting_key()
            if action == "idle":
                key = "idle"
                default_mood = "chill"
            charge = int(memory.get("charge", 85))
            summary = f"Charge {charge}% · Lv.{core['level']} {core['rank']}."
            return BuddyResult(
                ok=True,
                message=soul.react([key, "greet"], user=user, summary=summary),
                mood=default_mood,
            )

        if action in ("pulse", "status"):
            vitals = gather_vitals()
            mood, comment, rows = format_vitals_report(vitals)
            return BuddyResult(
                ok=True,
                message=f"{soul.signature} {comment}",
                mood=mood,
                table_headers=("Vital", "Reading"),
                table_rows=rows,
                meta={"xp_gain": 3, "machine_updates": {"os": vitals.os_label, "shell": vitals.shell}},
            )

        if action in ("repo", "git"):
            report = inspect_workspace(params.get("path"))
            return BuddyResult(
                ok=True,
                message=f"{soul.signature} {report.comment}",
                mood=report.mood,
                table_headers=("Workspace", "Detail"),
                table_rows=report.rows,
                meta={"xp_gain": 4, "memory_updates": {"last_repo": str(report.root or report.path)}},
            )

        if action == "ports":
            custom = params.get("ports")
            report = inspect_ports(custom)
            return BuddyResult(
                ok=True,
                message=f"{soul.signature} {report.comment}",
                mood=report.mood,
                table_headers=("Port", "State", "Process", "Note"),
                table_rows=report.rows,
                meta={"xp_gain": 3},
            )

        if action == "sweep":
            report = scan_clutter(params.get("path"))
            if params.get("clean"):
                removed, freed, errors = clean_safe_caches(report)
                if errors:
                    msg = f"{soul.signature} Swept {removed} spot(s) ({format_bytes(freed)}), hit {len(errors)} hiccup(s), dude."
                    mood = "curious"
                elif removed:
                    msg = f"{soul.signature} Boom—vaporized {format_bytes(freed)} across {removed} safe cache(s), dude."
                    mood = "proud"
                else:
                    msg = f"{soul.signature} Nothin' safe to sweep in `{report.root.name}`, dude."
                    mood = "chill"
                # Re-scan after cleaning so table reflects remaining entries
                after = scan_clutter(report.root)
                return BuddyResult(
                    ok=len(errors) == 0,
                    message=msg,
                    mood=mood,
                    table_headers=("Item", "Count", "Size", "Safety") if after.rows else None,
                    table_rows=after.rows,
                    meta={"xp_gain": 6, "report": after, "cleaned_bytes": freed},
                )

            return BuddyResult(
                ok=True,
                message=f"{soul.signature} {report.comment}",
                mood=report.mood,
                table_headers=("Item", "Count", "Size", "Safety") if report.rows else None,
                table_rows=report.rows,
                meta={"xp_gain": 2, "report": report},
            )

        if action == "poke":
            count = int(memory.get("poke_count", 0))
            toy = poke_sirius(count)
            return BuddyResult(
                ok=True,
                message=toy.message,
                mood=toy.mood,
                meta={"xp_gain": 1, "memory_updates": {"poke_count": count + 1}},
            )

        if action == "snack":
            charge = int(memory.get("charge", 85))
            snacks_eaten = int(memory.get("snacks_eaten", 0))
            toy = feed_sirius(charge, params.get("item"))
            return BuddyResult(
                ok=True,
                message=toy.message,
                mood=toy.mood,
                meta={
                    "xp_gain": 2,
                    "headline": toy.headline,
                    "memory_updates": {"charge": toy.charge, "snacks_eaten": snacks_eaten + 1},
                },
            )

        if action == "flip":
            toy = flip_coin()
            return BuddyResult(
                ok=True,
                message=toy.message,
                mood=toy.mood,
                meta={"xp_gain": 1, "headline": toy.headline},
            )

        if action == "roll":
            sides = int(params.get("sides", 20))
            toy = roll_dice(sides)
            return BuddyResult(
                ok=True,
                message=toy.message,
                mood=toy.mood,
                meta={"xp_gain": 1, "headline": toy.headline},
            )

        if action == "oracle":
            toy = cosmic_oracle()
            return BuddyResult(
                ok=True,
                message=toy.message,
                mood=toy.mood,
                meta={"xp_gain": 1, "headline": toy.headline},
            )

        if action == "help":
            return BuddyResult(
                ok=True,
                message=soul.react("help", user=user),
                mood="wink",
            )

        return BuddyResult(
            ok=False,
            message=soul.react("unknown", query=action, user=user),
            mood="curious",
        )

    def badge_lines(self, frame: int = 0) -> list[tuple[str, str]]:
        return build_sirius_badge(frame=frame)
