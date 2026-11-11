"""CLI entry point for `sirius` and `castle`."""

import argparse
import os
import subprocess
import sys

from castle import __version__
from castle.buddies.missions import record_mission_outcome
from castle.buddies.registry import BuddyRegistry
from castle.storage.config import load_config, set_config, show_config
from castle.storage.journal import get_recent_events
from castle.ui.display import Display
from castle.ui.sirius_art import SIRIUS_MOODS, get_mood_spec


def _ensure_utf8() -> None:
    """Ensure UTF-8 output on Windows consoles when possible."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and getattr(stream, "encoding", "").lower() != "utf-8":
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def _execute_cli_buddy(
    buddy_id: str,
    action: str,
    params: dict,
    registry: BuddyRegistry,
    cfg: dict,
    display: Display,
) -> int:
    """Execute a buddy action from one-shot CLI mode and record evolution/journal."""
    buddy = registry.get(buddy_id)
    if buddy is None:
        display.print_sirius_cli(f"✦ Buddy '{buddy_id}' isn't in the Castle yet, dude.", mood="curious")
        return 1

    show_shadow = bool(cfg.get("show_shadow", True))
    result = buddy.execute(action, params, cfg)
    if not result.ok:
        record_mission_outcome(buddy.id, action, result.message, registry, xp_gain=0, ok=False)
        display.print_sirius_cli(
            result.message,
            mood=result.mood,
            result=result,
            show_shadow=show_shadow,
        )
        return 1

    if result.interactive_cmd:
        display.print_sirius_cli(result.message, mood=result.mood, show_shadow=show_shadow)
        try:
            proc = subprocess.run(result.interactive_cmd)
            ok = proc.returncode == 0
            detail = f"exit code {proc.returncode}"
            code = proc.returncode
        except OSError as exc:
            ok = False
            detail = str(exc)
            code = 1
        levelups = record_mission_outcome(
            buddy_id=buddy.id,
            action=action,
            summary=f"{action} ({detail})",
            registry=registry,
            xp_gain=int(result.meta.get("xp_gain", 10)) if ok else 2,
            memory_updates=result.meta.get("memory_updates"),
            machine_updates=result.meta.get("machine_updates"),
            ok=ok,
        )
        for msg in levelups:
            display.print_sirius_cli(msg, mood="hyped", show_shadow=show_shadow)
        return code

    levelups = record_mission_outcome(
        buddy_id=buddy.id,
        action=action,
        summary=result.message,
        registry=registry,
        xp_gain=int(result.meta.get("xp_gain", 3)),
        memory_updates=result.meta.get("memory_updates"),
        machine_updates=result.meta.get("machine_updates"),
        ok=True,
    )
    display.print_sirius_cli(
        result.message,
        mood=result.mood,
        result=result,
        levelups=levelups,
        show_shadow=show_shadow,
    )
    return 0


def _handle_summon_args(
    buddy_name: str,
    raw_args: list[str],
    registry: BuddyRegistry,
    cfg: dict,
    display: Display,
) -> int:
    """Route `sirius summon <buddy> [args...]` or `sirius pomo [args...]` cleanly."""
    buddy = registry.get(buddy_name)
    if buddy is None:
        display.print_sirius_cli(f"✦ No resident named '{buddy_name}' in the Castle, dude.", mood="curious")
        return 1
    if buddy.id == "sirius":
        snapshots = registry.snapshot_all(cfg)
        greet = buddy.execute("greet", {}, cfg)
        display.print_status_cli(
            snapshots,
            greet.message,
            mood=greet.mood,
            show_shadow=bool(cfg.get("show_shadow", True)),
        )
        return 0

    cleaned = [a for a in raw_args if a != "--"]
    if not cleaned:
        return _execute_cli_buddy(buddy.id, "open", {}, registry, cfg, display)

    first = cleaned[0].lower()
    if first in ("status", "history", "config"):
        params = {}
        if first == "history" and len(cleaned) > 1 and cleaned[1].isdigit():
            params["days"] = int(cleaned[1])
        return _execute_cli_buddy(buddy.id, first, params, registry, cfg, display)

    return _execute_cli_buddy(buddy.id, "open", {"raw_args": cleaned}, registry, cfg, display)


def _handle_sweep_cli(args, registry: BuddyRegistry, cfg: dict, display: Display) -> int:
    show_shadow = bool(cfg.get("show_shadow", True))
    if not args.clean:
        return _execute_cli_buddy("sirius", "sweep", {"path": args.path}, registry, cfg, display)

    # Preview first before cleaning
    preview = registry.sirius.execute("sweep", {"path": args.path}, cfg)
    report = (preview.meta or {}).get("report")
    if report is None or report.safe_count == 0:
        display.print_sirius_cli(preview.message, mood=preview.mood, result=preview, show_shadow=show_shadow)
        return 0

    if not args.yes:
        display.print_sirius_cli(preview.message, mood=preview.mood, result=preview, show_shadow=show_shadow)
        if not sys.stdin.isatty():
            display.print_sirius_cli(
                "✦ Pass `--yes` to clean non-interactively, dude.",
                mood="unimpressed",
                show_shadow=show_shadow,
            )
            return 1
        try:
            answer = input("Sweep safe caches now? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return 1
        if answer not in ("y", "yes"):
            display.print_sirius_cli("✦ Chill—left everything alone, dude.", mood="chill", show_shadow=show_shadow)
            return 0

    return _execute_cli_buddy("sirius", "sweep", {"path": args.path, "clean": True}, registry, cfg, display)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sirius",
        description="✦ Sirius & the Castle — Offline Retro CLI Cyber-Buddy & Device Helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  sirius                    Open interactive keyboard TUI Hub\n"
            "  sirius pulse              Check OS, CPU, RAM, disk & battery\n"
            "  sirius repo               Scout Git branch, dirty files & stack\n"
            "  sirius ports              Inspect listening localhost & dev ports\n"
            "  sirius sweep              Scan workspace for safe cache clutter\n"
            "  sirius timer 25           Start a 25m offline countdown timer\n"
            "  sirius poke               Poke Sirius for a sharp reaction\n"
            "  sirius mood smug          Preview Sirius expressions in CLI\n"
            "  sirius pomo status        Check Pomo Clocktower stats\n"
        ),
    )
    parser.add_argument("-v", "--version", action="version", version=f"Castle {__version__}")

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("pulse", aliases=["vitals"], help="Inspect OS, CPU, RAM, disk, battery & local IP")
    sub.add_parser("status", help="Show Sirius and Castle buddies summary")

    sp_repo = sub.add_parser("repo", aliases=["git"], help="Scout Git repo & project stack")
    sp_repo.add_argument("path", nargs="?", default=None, help="Directory to inspect (default: cwd)")

    sp_ports = sub.add_parser("ports", help="Inspect listening TCP ports and dev servers")
    sp_ports.add_argument("ports", nargs="*", type=int, help="Optional specific ports to check")

    sp_sweep = sub.add_parser("sweep", help="Scan workspace for safe dev cache clutter")
    sp_sweep.add_argument("path", nargs="?", default=None, help="Directory to scan (default: cwd)")
    sp_sweep.add_argument("--clean", action="store_true", help="Sweep safe caches (__pycache__, .pytest_cache, etc.)")
    sp_sweep.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt with --clean")

    sp_timer = sub.add_parser("timer", help="Start built-in offline keyboard countdown timer")
    sp_timer.add_argument("minutes", nargs="?", type=int, default=25, help="Countdown duration in minutes (default: 25)")

    sub.add_parser("poke", help="Poke Sirius and watch how he reacts")

    sp_snack = sub.add_parser("snack", help="Toss Sirius a cosmic snack")
    sp_snack.add_argument("item", nargs="?", default=None, help="Snack id: espresso, photon, pretzel, pizza, tea")

    sub.add_parser("flip", help="Flip a cosmic coin offline")

    sp_roll = sub.add_parser("roll", help="Roll an N-sided die offline (default: d20)")
    sp_roll.add_argument("sides", nargs="?", type=int, default=20, help="Number of sides (default: 20)")

    sub.add_parser("oracle", help="Get a sharp offline cosmic decision")

    sp_mood = sub.add_parser("mood", help="Preview Sirius expressions in the CLI")
    sp_mood.add_argument("name", nargs="?", default=None, help="Mood id (omit to list all expressions)")

    sub.add_parser("buddies", help="List Castle buddies, rooms, souls & cores")

    sp_summon = sub.add_parser("summon", help="Directly summon a Castle buddy")
    sp_summon.add_argument("buddy", help="Buddy name, id, or room (e.g. pomo)")
    sp_summon.add_argument("extra", nargs=argparse.REMAINDER, help="Optional arguments for buddy")

    sp_pomo = sub.add_parser("pomo", help="Shortcut to summon Pomo (Clocktower)")
    sp_pomo.add_argument("extra", nargs=argparse.REMAINDER, help="Optional Pomo subcommand/flags")

    sp_log = sub.add_parser("log", help="View recent Castle mission chronicle")
    sp_log.add_argument("--limit", type=int, default=15, help="Max entries to show (default: 15)")

    sp_soul = sub.add_parser("soul", help="Inspect a buddy's soul.md and evolving core")
    sp_soul.add_argument("buddy", nargs="?", default="sirius", help="Buddy id or name (default: sirius)")

    sp_cfg = sub.add_parser("config", help="View or set Castle configuration")
    sp_cfg.add_argument("key", nargs="?", help="Config key to view/set")
    sp_cfg.add_argument("value", nargs="?", help="New value")

    return parser


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)

    cfg = load_config()
    registry = BuddyRegistry()
    display = Display()
    show_shadow = bool(cfg.get("show_shadow", True))

    if args.command is None:
        if sys.stdin.isatty() and sys.stdout.isatty():
            from castle.ui.app import run_interactive

            run_interactive(__version__)
        else:
            snapshots = registry.snapshot_all(cfg)
            greet = registry.sirius.execute("greet", {}, cfg)
            display.print_status_cli(snapshots, greet.message, mood=greet.mood, show_shadow=show_shadow)
            if sys.platform == "win32" and os.environ.get("MSYSTEM") and not os.environ.get("WT_SESSION"):
                display.print_sirius_cli(
                    "✦ Running under Mintty pipe? Open Git Bash inside Windows Terminal (or `winpty sirius`) for the full interactive TUI, dude!",
                    mood="wink",
                    show_shadow=show_shadow,
                )
        return 0

    if args.command == "status":
        snapshots = registry.snapshot_all(cfg)
        greet = registry.sirius.execute("greet", {}, cfg)
        display.print_status_cli(snapshots, greet.message, mood=greet.mood, show_shadow=show_shadow)
        return 0

    if args.command in ("pulse", "vitals"):
        return _execute_cli_buddy("sirius", "pulse", {}, registry, cfg, display)

    if args.command in ("repo", "git"):
        return _execute_cli_buddy("sirius", "repo", {"path": args.path}, registry, cfg, display)

    if args.command == "ports":
        return _execute_cli_buddy("sirius", "ports", {"ports": args.ports or None}, registry, cfg, display)

    if args.command == "sweep":
        return _handle_sweep_cli(args, registry, cfg, display)

    if args.command == "timer":
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            display.print_sirius_cli(
                f"✦ Timer needs an interactive terminal, dude (requested {args.minutes}m).",
                mood="curious",
                show_shadow=show_shadow,
            )
            return 1
        from rich.live import Live
        from castle.ui.app import _run_timer_screen
        from castle.ui.display import console
        from castle.ui.keys import keyboard_session

        with keyboard_session(), Live(console=console, refresh_per_second=12, screen=True) as live:
            _run_timer_screen(display, live, registry, cfg, initial_minutes=args.minutes, auto_start=True)
        return 0

    if args.command == "poke":
        return _execute_cli_buddy("sirius", "poke", {}, registry, cfg, display)

    if args.command == "snack":
        return _execute_cli_buddy("sirius", "snack", {"item": args.item}, registry, cfg, display)

    if args.command == "flip":
        return _execute_cli_buddy("sirius", "flip", {}, registry, cfg, display)

    if args.command == "roll":
        return _execute_cli_buddy("sirius", "roll", {"sides": args.sides}, registry, cfg, display)

    if args.command == "oracle":
        return _execute_cli_buddy("sirius", "oracle", {}, registry, cfg, display)

    if args.command == "mood":
        if not args.name:
            names = ", ".join(f"{m.id} ({m.label})" for m in SIRIUS_MOODS)
            display.print_sirius_cli(
                f"✦ Pick a mood with `sirius mood <name>`, dude:\n{names}",
                mood="wink",
                show_shadow=show_shadow,
            )
            return 0
        spec = get_mood_spec(args.name)
        display.print_sirius_cli(
            f"✦ [{spec.label}] {spec.desc}.",
            mood=spec.id,
            show_shadow=show_shadow,
        )
        return 0

    if args.command == "buddies":
        snapshots = registry.snapshot_all(cfg)
        display.print_buddies_cli(snapshots)
        return 0

    if args.command == "log":
        if args.limit < 1:
            parser.error("--limit must be at least 1")
        display.print_log_cli(get_recent_events(limit=args.limit))
        return 0

    if args.command == "soul":
        buddy = registry.get(args.buddy)
        if buddy is None:
            display.print_sirius_cli(f"✦ No buddy named '{args.buddy}' in the Castle, dude.", mood="curious", show_shadow=show_shadow)
            return 1
        soul = buddy.load_soul()
        core, _ = buddy.load_core()
        display.print_soul_cli(soul, core)
        return 0

    if args.command == "config":
        if args.key is not None and args.value is not None:
            return 0 if set_config(args.key, args.value) else 1
        show_config(args.key)
        return 0

    if args.command == "pomo":
        return _handle_summon_args("pomo", args.extra, registry, cfg, display)

    if args.command == "summon":
        return _handle_summon_args(args.buddy, args.extra, registry, cfg, display)

    return 0


if __name__ == "__main__":
    sys.exit(main())
