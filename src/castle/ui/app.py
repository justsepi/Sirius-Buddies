"""Interactive pure-keyboard TUI controller for Sirius & the Castle."""

import socket
import subprocess
import time
from rich.live import Live

from castle.buddies.base import BuddyResult
from castle.buddies.missions import record_mission_outcome
from castle.buddies.registry import BuddyRegistry
from castle.storage.config import (
    load_config,
    parse_config_value,
    reset_config,
    save_config,
    toggle_or_cycle_config,
)
from castle.storage.journal import get_recent_events
from castle.ui.display import CONFIG_ITEMS, HOME_MENU, Display, console
from castle.ui.keys import (
    flush_keys,
    keyboard_session,
    pause_keyboard_session,
    read_key,
)
from castle.ui.sirius_art import SIRIUS_MOODS


def _sync_resize(last_size):
    if console.size != last_size:
        console.clear()
        return console.size
    return last_size


def _launch_interactive_cmd(live: Live, cmd: list[str]) -> tuple[bool, str]:
    """Suspend Sirius's Live TUI and raw terminal mode to hand TTY cleanly to a buddy."""
    live.stop()
    try:
        with pause_keyboard_session():
            proc = subprocess.run(cmd)
        return proc.returncode == 0, f"exit code {proc.returncode}"
    except OSError as exc:
        return False, str(exc)
    finally:
        console.clear()
        live.start(refresh=True)
        flush_keys()


def _run_buddy_action(
    registry: BuddyRegistry,
    cfg: dict,
    buddy_id: str,
    action: str,
    params: dict | None = None,
    log_mission: bool = True,
) -> tuple[str, str, BuddyResult | None]:
    """Execute a buddy action and optionally log mission/XP."""
    buddy = registry.get(buddy_id) or registry.sirius
    res = buddy.execute(action, params or {}, cfg)
    msg = res.message
    if log_mission and res.ok:
        levelups = record_mission_outcome(
            buddy_id=buddy.id,
            action=action,
            summary=res.message,
            registry=registry,
            xp_gain=int(res.meta.get("xp_gain", 2)),
            memory_updates=res.meta.get("memory_updates"),
            machine_updates=res.meta.get("machine_updates"),
            ok=True,
        )
        if levelups:
            msg = f"{msg}\n{levelups[0]}"
    return msg, res.mood, res


def _run_helper_screen(
    display: Display,
    live: Live,
    registry: BuddyRegistry,
    cfg: dict,
    helper_action: str,
) -> str:
    """Interactive result viewer for Pulse, Repo Scout, Port Inspector & Cache Sweep."""
    titles = {
        "pulse": "SYSTEM PULSE",
        "repo": "REPO & GIT SCOUT",
        "ports": "PORT INSPECTOR",
        "sweep": "CACHE SWEEP",
    }
    title = titles.get(helper_action, helper_action.upper())
    show_shadow = bool(cfg.get("show_shadow", True))

    def _run_scan(clean: bool = False):
        return _run_buddy_action(
            registry,
            cfg,
            "sirius",
            helper_action,
            {"clean": clean} if helper_action == "sweep" and clean else {},
            log_mission=True,
        )

    sirius_reply, sirius_mood, result = _run_scan()
    confirm_clean = False
    frame = 0
    last_size = console.size
    flush_keys()

    while True:
        last_size = _sync_resize(last_size)
        anim_frame = (frame // 2) if cfg.get("animations_enabled", True) else 0
        report = (result.meta or {}).get("report") if result else None
        can_clean = bool(
            helper_action == "sweep"
            and report is not None
            and getattr(report, "safe_count", 0) > 0
        )

        confirm_prompt = ""
        if confirm_clean and can_clean:
            confirm_prompt = (
                f"Vaporize {report.safe_count} safe cache item(s)? Press [y] to confirm, [n/Esc] to cancel."
            )
        extra_hint = "c sweep safe caches" if can_clean and not confirm_clean else ""

        live.update(
            display.frame_center(
                display.render_helper_screen(
                    title=title,
                    sirius_reply=sirius_reply,
                    sirius_mood=sirius_mood,
                    result=result,
                    frame=anim_frame,
                    show_shadow=show_shadow,
                    confirm_prompt=confirm_prompt,
                    extra_hint=extra_hint,
                )
            )
        )
        key = read_key(timeout=0.25)
        frame += 1
        if key is None:
            continue
        low = key.lower()

        if confirm_clean:
            if key == "CTRL_C":
                return "quit"
            if low == "y":
                sirius_reply, sirius_mood, result = _run_scan(clean=True)
                confirm_clean = False
            elif key == "ESC" or low in ("n", "b"):
                confirm_clean = False
                sirius_reply = "✦ Chill—kept everything intact, dude."
                sirius_mood = "chill"
            continue

        if key == "CTRL_C" or low == "q":
            return "quit"
        if key == "ESC" or low == "b":
            return "home"
        if low == "r":
            sirius_reply, sirius_mood, result = _run_scan()
        elif low == "p":
            sirius_reply, sirius_mood, _ = _run_buddy_action(registry, cfg, "sirius", "poke", log_mission=False)
        elif low == "c" and can_clean:
            confirm_clean = True


def _run_timer_screen(
    display: Display,
    live: Live,
    registry: BuddyRegistry,
    cfg: dict,
    initial_minutes: int = 25,
    auto_start: bool = False,
) -> str:
    """Built-in pure-offline keyboard countdown timer hosted by Sirius."""
    minutes_set = max(1, min(180, initial_minutes))
    remaining_secs = minutes_set * 60
    running = auto_start
    finished = False
    last_tick = time.monotonic()
    frame = 0
    last_size = console.size
    show_shadow = bool(cfg.get("show_shadow", True))
    flush_keys()

    while True:
        last_size = _sync_resize(last_size)
        now = time.monotonic()
        if running and not finished:
            elapsed = now - last_tick
            if elapsed >= 1.0:
                step = int(elapsed)
                last_tick += step
                remaining_secs = max(0, remaining_secs - step)
                if remaining_secs == 0:
                    running = False
                    finished = True
                    try:
                        print("\a", end="", flush=True)
                    except Exception:
                        pass
                    record_mission_outcome(
                        buddy_id="sirius",
                        action="timer",
                        summary=f"Quick timer {minutes_set}m completed",
                        registry=registry,
                        xp_gain=8,
                        ok=True,
                    )
        else:
            last_tick = now

        anim_frame = (frame // 2) if cfg.get("animations_enabled", True) else 0
        live.update(
            display.frame_center(
                display.render_timer_screen(
                    minutes_set=minutes_set,
                    remaining_secs=remaining_secs,
                    running=running,
                    finished=finished,
                    frame=anim_frame,
                    show_shadow=show_shadow,
                )
            )
        )
        key = read_key(timeout=0.25)
        frame += 1
        if key is None:
            continue
        low = key.lower()

        if key == "CTRL_C" or low == "q":
            return "quit"
        if key == "ESC" or low == "b":
            return "home"
        if key in ("SPACE", "ENTER"):
            if finished:
                remaining_secs = minutes_set * 60
                finished = False
                running = True
                last_tick = time.monotonic()
            else:
                running = not running
                last_tick = time.monotonic()
        elif low == "r":
            running = False
            finished = False
            remaining_secs = minutes_set * 60
        elif not running and key in ("1", "2", "3", "4"):
            presets = {"1": 5, "2": 15, "3": 25, "4": 45}
            minutes_set = presets[key]
            remaining_secs = minutes_set * 60
            finished = False
        elif not running and key in ("+", "="):
            minutes_set = min(180, minutes_set + 1)
            remaining_secs = minutes_set * 60
            finished = False
        elif not running and key in ("-", "_"):
            minutes_set = max(1, minutes_set - 1)
            remaining_secs = minutes_set * 60
            finished = False


def _run_moods_screen(display: Display, live: Live, cfg: dict) -> str:
    """Browse all of Sirius's CLI expressions with keyboard arrows."""
    mood_idx = 0
    frame = 0
    last_size = console.size
    show_shadow = bool(cfg.get("show_shadow", True))
    flush_keys()

    while True:
        last_size = _sync_resize(last_size)
        anim_frame = (frame // 2) if cfg.get("animations_enabled", True) else 0
        live.update(
            display.frame_center(
                display.render_moods_screen(
                    mood_idx=mood_idx,
                    frame=anim_frame,
                    show_shadow=show_shadow,
                )
            )
        )
        key = read_key(timeout=0.25)
        frame += 1
        if key is None:
            continue
        low = key.lower()
        if key == "CTRL_C" or low == "q":
            return "quit"
        if key == "ESC" or low == "b":
            return "home"
        if key in ("LEFT", "UP") or low in ("h", "k"):
            mood_idx = (mood_idx - 1) % len(SIRIUS_MOODS)
        elif key in ("RIGHT", "DOWN", "SPACE", "ENTER") or low in ("l", "j"):
            mood_idx = (mood_idx + 1) % len(SIRIUS_MOODS)


def _run_toys_screen(
    display: Display,
    live: Live,
    registry: BuddyRegistry,
    cfg: dict,
) -> str:
    """Interactive Cosmic Flip, Dice Roll, Oracle, Snack & Poke deck."""
    sirius_reply = "✦ Pick somethin', dude—coin flip, dice roll, cosmic call, or snacks."
    sirius_mood = "smug"
    headline = "Buddy Deck"
    frame = 0
    last_size = console.size
    show_shadow = bool(cfg.get("show_shadow", True))
    flush_keys()

    while True:
        last_size = _sync_resize(last_size)
        anim_frame = (frame // 2) if cfg.get("animations_enabled", True) else 0
        live.update(
            display.frame_center(
                display.render_toys_screen(
                    sirius_reply=sirius_reply,
                    sirius_mood=sirius_mood,
                    headline=headline,
                    frame=anim_frame,
                    show_shadow=show_shadow,
                )
            )
        )
        key = read_key(timeout=0.25)
        frame += 1
        if key is None:
            continue
        low = key.lower()
        if key == "CTRL_C" or low == "q":
            return "quit"
        if key == "ESC" or low == "b":
            return "home"

        action_map = {
            "1": ("flip", {}),
            "2": ("roll", {"sides": 20}),
            "3": ("roll", {"sides": 6}),
            "4": ("oracle", {}),
            "f": ("snack", {}),
            "p": ("poke", {}),
        }
        if low in action_map:
            act, params = action_map[low]
            msg, mood, res = _run_buddy_action(registry, cfg, "sirius", act, params, log_mission=(low != "p"))
            sirius_reply = msg
            sirius_mood = mood
            headline = (res.meta or {}).get("headline", "Buddy Deck") if res else "Buddy Deck"


def _run_soul_screen(
    display: Display,
    live: Live,
    registry: BuddyRegistry,
    buddy_id: str,
) -> str:
    buddy = registry.get(buddy_id) or registry.sirius
    soul = buddy.load_soul()
    core, _ = buddy.load_core()
    last_size = console.size
    flush_keys()

    while True:
        last_size = _sync_resize(last_size)
        live.update(display.frame_center(display.render_soul_screen(soul, core)))
        key = read_key(timeout=0.25)
        if key is None:
            continue
        low = key.lower()
        if key in ("ESC", "ENTER", "SPACE") or low == "b":
            return "home"
        if key == "CTRL_C" or low == "q":
            return "quit"


def _run_directory_screen(
    display: Display,
    live: Live,
    registry: BuddyRegistry,
    cfg: dict,
) -> tuple[str, str]:
    """Browse Castle residents, view souls, or summon a buddy. Returns (route, buddy_id)."""
    selected = 0
    frame = 0
    last_size = console.size
    snapshots = registry.snapshot_all(cfg)
    flush_keys()

    while True:
        last_size = _sync_resize(last_size)
        anim_frame = (frame // 2) if cfg.get("animations_enabled", True) else 0
        live.update(
            display.frame_center(
                display.render_directory_screen(snapshots, selected_idx=selected, frame=anim_frame)
            )
        )
        key = read_key(timeout=0.25)
        frame += 1
        if key is None:
            continue
        low = key.lower()
        if key == "CTRL_C" or low == "q":
            return "quit", ""
        if key == "ESC" or low == "b":
            return "home", ""
        if key == "UP" or low == "k":
            selected = (selected - 1) % len(snapshots)
        elif key == "DOWN" or low == "j":
            selected = (selected + 1) % len(snapshots)
        elif low == "s":
            return "soul", snapshots[selected].buddy.id
        elif key in ("ENTER", "SPACE"):
            target = snapshots[selected].buddy
            if target.id == "sirius":
                return "soul", "sirius"
            return "summon_pomo", target.id


def _run_log_screen(display: Display, live: Live) -> str:
    last_size = console.size
    events = get_recent_events(limit=15)
    flush_keys()

    while True:
        last_size = _sync_resize(last_size)
        live.update(display.frame_center(display.render_log_screen(events)))
        key = read_key(timeout=0.25)
        if key is None:
            continue
        low = key.lower()
        if key in ("ESC", "ENTER", "SPACE") or low == "b":
            return "home"
        if key == "CTRL_C" or low == "q":
            return "quit"


def _run_config_screen(display: Display, live: Live) -> dict:
    """Interactive settings editor; returns updated config dict (with `_quit` if quitting)."""
    cfg = load_config()
    selected = 0
    editing = False
    edit_buf = ""
    status_msg = ""
    last_size = console.size
    flush_keys()

    while True:
        last_size = _sync_resize(last_size)
        live.update(
            display.frame_center(
                display.render_config_screen(
                    cfg,
                    selected_idx=selected,
                    editing=editing,
                    edit_buf=edit_buf,
                    status_msg=status_msg,
                )
            )
        )
        key = read_key(timeout=0.25)
        if key is None:
            continue

        cur_key, cur_label, cur_kind = CONFIG_ITEMS[selected]
        if editing:
            if key == "CTRL_C":
                return {"_quit": True, **cfg}
            if key == "ESC":
                editing = False
                edit_buf = ""
                status_msg = ""
            elif key == "BACKSPACE":
                edit_buf = edit_buf[:-1]
            elif key == "ENTER":
                ok, parsed, err = parse_config_value(cur_key, edit_buf)
                if ok:
                    cfg[cur_key] = parsed
                    save_config(cfg)
                    status_msg = f"✓ {cur_label} updated"
                else:
                    status_msg = err
                editing = False
                edit_buf = ""
            else:
                char = " " if key == "SPACE" else key
                if len(char) == 1 and char.isprintable() and len(edit_buf) < 60:
                    edit_buf += char
            continue

        low = key.lower()
        if key == "CTRL_C" or low == "q":
            return {"_quit": True, **cfg}
        if key == "ESC" or low == "b":
            return cfg
        if key == "UP" or low == "k":
            selected = (selected - 1) % len(CONFIG_ITEMS)
            status_msg = ""
        elif key == "DOWN" or low == "j":
            selected = (selected + 1) % len(CONFIG_ITEMS)
            status_msg = ""
        elif key in ("ENTER", "SPACE", "LEFT", "RIGHT"):
            if cur_kind == "bool":
                cfg = toggle_or_cycle_config(cfg, cur_key)
                status_msg = f"✓ {cur_label} = {cfg[cur_key]}"
            elif key == "ENTER":
                editing = True
                edit_buf = str(cfg.get(cur_key, ""))
                status_msg = ""
        elif low == "r":
            cfg = reset_config()
            status_msg = "✓ Defaults restored"


def _summon_pomo_interactive(
    live: Live,
    registry: BuddyRegistry,
    cfg: dict,
    action: str = "open",
    params: dict | None = None,
) -> tuple[str, str]:
    """Hand off interactive TTY cleanly to Pomo if installed, else guide user to Quick Timer."""
    buddy = registry.get("pomo")
    if buddy is None:
        return "✦ Pomo isn't registered in this Castle yet, dude.", "curious"

    result = buddy.execute(action, params or {}, cfg)
    if not result.ok:
        record_mission_outcome(buddy.id, action, result.message, registry, xp_gain=0, ok=False)
        return "✦ Pomo isn't installed here yet, dude—try Quick Timer [5] instead!", "wink"

    if result.interactive_cmd:
        ok, detail = _launch_interactive_cmd(live, result.interactive_cmd)
        xp = int(result.meta.get("xp_gain", 10)) if ok else 2
        levelups = record_mission_outcome(
            buddy_id=buddy.id,
            action=action,
            summary=f"{action} ({detail})",
            registry=registry,
            xp_gain=xp,
            memory_updates=result.meta.get("memory_updates"),
            machine_updates=result.meta.get("machine_updates"),
            ok=ok,
        )
        msg = "✦ Welcome back from the Clocktower, dude! Solid focus."
        if levelups:
            msg = f"{msg}\n{levelups[0]}"
        return msg, "happy"

    return result.message, result.mood


def run_interactive(version: str) -> None:
    """Launch the pure-keyboard Sirius & Castle retro TUI Hub."""
    display = Display()
    registry = BuddyRegistry()
    cfg = load_config()

    snapshots = registry.snapshot_all(cfg)
    greet_res = registry.sirius.execute("greet", {}, cfg)
    sirius_reply = greet_res.message
    sirius_mood = greet_res.mood
    host_label = socket.gethostname()

    selected_idx = 0
    frame = 0
    idle_ticks = 0
    last_size = console.size
    route = "home"
    soul_target = "sirius"

    try:
        with (
            keyboard_session(),
            Live(console=console, refresh_per_second=12, screen=True) as live,
        ):
            flush_keys()
            while route != "quit":
                if route in ("pulse", "repo", "ports", "sweep"):
                    route = _run_helper_screen(display, live, registry, cfg, route)
                    snapshots = registry.snapshot_all(cfg)
                    idle_ticks = 0
                    continue

                if route == "timer":
                    route = _run_timer_screen(display, live, registry, cfg)
                    snapshots = registry.snapshot_all(cfg)
                    idle_ticks = 0
                    continue

                if route == "moods":
                    route = _run_moods_screen(display, live, cfg)
                    idle_ticks = 0
                    continue

                if route == "toys":
                    route = _run_toys_screen(display, live, registry, cfg)
                    snapshots = registry.snapshot_all(cfg)
                    idle_ticks = 0
                    continue

                if route == "buddies":
                    next_route, picked_id = _run_directory_screen(display, live, registry, cfg)
                    if next_route == "soul":
                        soul_target = picked_id
                        route = "soul"
                    elif next_route == "summon_pomo":
                        sirius_reply, sirius_mood = _summon_pomo_interactive(live, registry, cfg)
                        snapshots = registry.snapshot_all(cfg)
                        route = "home"
                    else:
                        route = next_route
                    idle_ticks = 0
                    continue

                if route == "soul":
                    route = _run_soul_screen(display, live, registry, soul_target)
                    idle_ticks = 0
                    continue

                if route == "log":
                    route = _run_log_screen(display, live)
                    idle_ticks = 0
                    continue

                if route == "config":
                    updated = _run_config_screen(display, live)
                    if updated.pop("_quit", False):
                        route = "quit"
                        break
                    cfg = updated
                    snapshots = registry.snapshot_all(cfg)
                    sirius_reply = "✦ Settings locked in, dude."
                    sirius_mood = "smug"
                    route = "home"
                    idle_ticks = 0
                    continue

                # ── Home Hub screen ───────────────────────────────────
                last_size = _sync_resize(last_size)
                anim_frame = (frame // 2) if cfg.get("animations_enabled", True) else 0
                show_shadow = bool(cfg.get("show_shadow", True))

                live.update(
                    display.frame_center(
                        display.render_home_screen(
                            version=version,
                            snapshots=snapshots,
                            sirius_reply=sirius_reply,
                            sirius_mood=sirius_mood,
                            selected_idx=selected_idx,
                            frame=anim_frame,
                            show_shadow=show_shadow,
                            host_label=host_label,
                        )
                    )
                )
                key = read_key(timeout=0.25)
                frame += 1
                if key is None:
                    idle_ticks += 1
                    if idle_ticks == 48:
                        quip = registry.sirius.execute("idle", {}, cfg)
                        sirius_reply = quip.message
                        sirius_mood = "smug"
                    elif idle_ticks == 140:
                        sirius_mood = "sleepy"
                        sirius_reply = "✦ Low-power hover mode, dude. Tap any key when you're ready."
                    continue

                if idle_ticks >= 140:
                    sirius_mood = "chill"
                    sirius_reply = "✦ Oh—we're rollin' again? Cool, what's up dude?"
                idle_ticks = 0

                if key == "CTRL_C" or key == "ESC":
                    route = "quit"
                    break

                low = key.lower()
                if low == "q":
                    route = "quit"
                    break
                if key == "UP" or low == "k":
                    selected_idx = (selected_idx - 1) % len(HOME_MENU)
                    continue
                if key == "DOWN" or low == "j":
                    selected_idx = (selected_idx + 1) % len(HOME_MENU)
                    continue

                chosen = None
                if key in ("ENTER", "SPACE"):
                    chosen = HOME_MENU[selected_idx][0]
                else:
                    for action_id, hotkey, _, _ in HOME_MENU:
                        if low == hotkey:
                            chosen = action_id
                            break

                if chosen == "pomo":
                    sirius_reply, sirius_mood = _summon_pomo_interactive(live, registry, cfg)
                    snapshots = registry.snapshot_all(cfg)
                    continue
                if chosen in ("pulse", "repo", "ports", "sweep", "timer"):
                    route = chosen
                    continue

                if low == "p":
                    sirius_reply, sirius_mood, _ = _run_buddy_action(
                        registry, cfg, "sirius", "poke", log_mission=False
                    )
                    snapshots = registry.snapshot_all(cfg)
                elif low == "f":
                    sirius_reply, sirius_mood, _ = _run_buddy_action(
                        registry, cfg, "sirius", "snack", log_mission=True
                    )
                    snapshots = registry.snapshot_all(cfg)
                elif low == "o":
                    route = "toys"
                elif low == "m":
                    route = "moods"
                elif low == "d":
                    route = "buddies"
                elif low == "l":
                    route = "log"
                elif low == "s":
                    route = "config"
                elif low == "r":
                    greet_res = registry.sirius.execute("greet", {}, cfg)
                    sirius_reply = greet_res.message
                    sirius_mood = greet_res.mood

    except KeyboardInterrupt:
        pass

    sirius_soul = registry.sirius.load_soul()
    sirius_core, _ = registry.sirius.load_core()
    farewell = sirius_soul.react("farewell", user=cfg.get("user_name", "dude"))
    console.print(
        display.render_goodbye_screen(
            farewell,
            sirius_core,
            show_shadow=bool(cfg.get("show_shadow", True)),
        )
    )
