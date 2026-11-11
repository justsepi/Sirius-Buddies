"""CLI entry point for `sirius` and `mansion`."""

import argparse
import subprocess
import sys

from mansion import __version__
from mansion.brain import create_brain, record_mission_outcome
from mansion.buddies.registry import BuddyRegistry
from mansion.storage.config import load_config, set_config, show_config
from mansion.storage.journal import get_recent_events
from mansion.ui.display import Display


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
    sirius_reply: str | None = None,
    notice: str | None = None,
) -> int:
    """Execute a buddy action from one-shot CLI mode and record evolution/journal."""
    buddy = registry.get(buddy_id)
    if buddy is None:
        display.print_result_cli(f"★ Buddy '{buddy_id}' isn't registered in the Mansion yet.")
        return 1

    result = buddy.execute(action, params, cfg)
    if not result.ok:
        record_mission_outcome(buddy.id, action, result.message, registry, xp_gain=0, ok=False)
        display.print_result_cli(sirius_reply or result.message, result=result, notice=notice)
        return 1

    if result.interactive_cmd:
        if sirius_reply:
            display.print_result_cli(sirius_reply, notice=notice)
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
            display.print_result_cli(msg)
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
    display.print_result_cli(
        sirius_reply or result.message,
        result=result,
        levelups=levelups,
        notice=notice,
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
        display.print_result_cli(f"★ No resident named '{buddy_name}' in the Mansion.")
        return 1
    if buddy.id == "sirius":
        snapshots = registry.snapshot_all(cfg)
        display.print_status_cli(snapshots, buddy.execute("greet", {}, cfg).message)
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sirius",
        description="★ Sirius & the Mansion — Retro CLI Cyber-Buddy Hub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  sirius                              Open interactive BMO Mansion TUI\n"
            "  sirius ask start deep focus on api  Ask Sirius in natural language\n"
            "  sirius status                       Mansion & today's focus summary\n"
            "  sirius buddies                      List residents, rooms & cores\n"
            "  sirius pomo start -p sprint -t dev  Summon Pomo directly\n"
            "  sirius soul sirius                  Inspect Sirius's soul.md & core\n"
            "  sirius log                          Show recent Mansion missions\n"
            "  sirius config                       View or set Mansion settings\n"
        ),
    )
    parser.add_argument("-v", "--version", action="version", version=f"Mansion {__version__}")

    sub = parser.add_subparsers(dest="command")

    sp_ask = sub.add_parser("ask", help="Ask Sirius to route a natural-language request")
    sp_ask.add_argument("words", nargs="+", help="Message or task for Sirius")

    sub.add_parser("status", help="Show Mansion and resident summary")
    sub.add_parser("buddies", help="List Mansion residents, rooms, souls, and cores")

    sp_summon = sub.add_parser("summon", help="Directly summon a Mansion buddy")
    sp_summon.add_argument("buddy", help="Buddy name, id, or room (e.g. pomo)")
    sp_summon.add_argument("extra", nargs=argparse.REMAINDER, help="Optional arguments for buddy")

    sp_pomo = sub.add_parser("pomo", help="Shortcut to summon Pomo (Clocktower)")
    sp_pomo.add_argument("extra", nargs=argparse.REMAINDER, help="Optional Pomo subcommand/flags")

    sp_log = sub.add_parser("log", help="View recent Mansion mission chronicle")
    sp_log.add_argument("--limit", type=int, default=15, help="Max entries to show (default: 15)")

    sp_soul = sub.add_parser("soul", help="Inspect a buddy's soul.md and evolving core")
    sp_soul.add_argument("buddy", nargs="?", default="sirius", help="Buddy id or name (default: sirius)")

    sp_cfg = sub.add_parser("config", help="View or set Mansion configuration")
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

    if args.command is None:
        if sys.stdin.isatty() and sys.stdout.isatty():
            from mansion.ui.app import run_interactive

            run_interactive(__version__)
        else:
            snapshots = registry.snapshot_all(cfg)
            brain, _ = create_brain(cfg)
            greeting = brain.plan("", registry, cfg).reply
            display.print_status_cli(snapshots, greeting)
        return 0

    if args.command == "status":
        snapshots = registry.snapshot_all(cfg)
        brain, _ = create_brain(cfg)
        greeting = brain.plan("", registry, cfg).reply
        display.print_status_cli(snapshots, greeting)
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
            display.print_result_cli(f"★ No buddy named '{args.buddy}' in the Mansion.")
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

    if args.command == "ask":
        query = " ".join(args.words).strip()
        brain, notice = create_brain(cfg)
        plan = brain.plan(query, registry, cfg)
        if plan.target == "sirius":
            if plan.action == "buddies":
                display.print_buddies_cli(registry.snapshot_all(cfg))
                record_mission_outcome("sirius", "buddies", query, registry, xp_gain=2)
                return 0
            if plan.action == "log":
                display.print_log_cli(get_recent_events(limit=15))
                record_mission_outcome("sirius", "log", query, registry, xp_gain=2)
                return 0
            if plan.action == "soul":
                target = registry.get(plan.params.get("buddy", "sirius")) or registry.sirius
                core, _ = target.load_core()
                display.print_soul_cli(target.load_soul(), core)
                record_mission_outcome("sirius", "soul", query, registry, xp_gain=2)
                return 0
            if plan.action == "config":
                show_config()
                return 0
            if plan.action == "status":
                display.print_status_cli(registry.snapshot_all(cfg), plan.reply)
                record_mission_outcome("sirius", "status", query, registry, xp_gain=2)
                return 0

            levelups: list[str] = []
            if plan.action != "unknown":
                levelups = record_mission_outcome("sirius", plan.action, query, registry, xp_gain=2)
            display.print_result_cli(plan.reply, levelups=levelups, notice=notice)
            return 0 if plan.action != "unknown" else 1

        return _execute_cli_buddy(
            plan.target,
            plan.action,
            plan.params,
            registry,
            cfg,
            display,
            sirius_reply=plan.reply,
            notice=notice,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
