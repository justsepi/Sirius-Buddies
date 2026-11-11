"""Interactive BMO-style TUI controller for Sirius & the Castle."""

import subprocess
from rich.live import Live

from castle.brain import create_brain, record_mission_outcome
from castle.buddies.base import BuddyResult
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
    PromptBuffer,
    flush_keys,
    keyboard_session,
    pause_keyboard_session,
    read_key,
)


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
    """Interactive settings editor; returns updated config dict (or signals quit via None)."""
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
            if cur_kind in ("bool", "cycle"):
                cfg = toggle_or_cycle_config(cfg, cur_key)
                status_msg = f"✓ {cur_label} = {cfg[cur_key]}"
            elif key == "ENTER":
                editing = True
                edit_buf = str(cfg.get(cur_key, ""))
                status_msg = ""
        elif low == "r":
            cfg = reset_config()
            status_msg = "✓ Defaults restored"


def _summon_buddy_interactive(
    live: Live,
    registry: BuddyRegistry,
    cfg: dict,
    buddy_id: str,
    action: str,
    params: dict,
) -> tuple[str, str, BuddyResult | None]:
    """Execute a buddy action from the TUI and return (sirius_reply, mood, inline_result)."""
    buddy = registry.get(buddy_id)
    if buddy is None:
        return f"★ Buddy '{buddy_id}' isn't in the Castle yet.", "curious", None

    result = buddy.execute(action, params, cfg)
    if not result.ok:
        record_mission_outcome(buddy.id, action, result.message, registry, xp_gain=0, ok=False)
        return result.message, result.mood, None

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
        soul = buddy.load_soul()
        msg = soul.react("success", detail="Returned to the Castle!")
        if levelups:
            msg = f"{msg}\n{levelups[0]}"
        return msg, "happy", None

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
    msg = result.message
    if levelups:
        msg = f"{msg}\n{levelups[0]}"
    return msg, result.mood, result


def run_interactive(version: str) -> None:
    """Launch the BMO-inspired Castle TUI Hub with Sirius and Pomo."""
    display = Display()
    registry = BuddyRegistry()
    cfg = load_config()
    brain, notice = create_brain(cfg)

    snapshots = registry.snapshot_all(cfg)
    initial_plan = brain.plan("", registry, cfg)
    sirius_reply = f"{notice}\n{initial_plan.reply}" if notice else initial_plan.reply
    sirius_mood = initial_plan.mood

    prompt = PromptBuffer()
    focus_zone = "prompt"
    selected_idx = 0
    inline_result: BuddyResult | None = None
    frame = 0
    last_size = console.size

    route = "home"
    soul_target = "sirius"

    try:
        with (
            keyboard_session(),
            Live(console=console, refresh_per_second=16, screen=True) as live,
        ):
            flush_keys()
            while route != "quit":
                if route == "buddies":
                    next_route, picked_id = _run_directory_screen(display, live, registry, cfg)
                    if next_route == "soul":
                        soul_target = picked_id
                        route = "soul"
                    elif next_route == "summon_pomo":
                        sirius_reply, sirius_mood, inline_result = _summon_buddy_interactive(
                            live, registry, cfg, "pomo", "open", {}
                        )
                        snapshots = registry.snapshot_all(cfg)
                        route = "home"
                    else:
                        route = next_route
                    continue

                if route == "soul":
                    route = _run_soul_screen(display, live, registry, soul_target)
                    continue

                if route == "log":
                    route = _run_log_screen(display, live)
                    continue

                if route == "config":
                    updated = _run_config_screen(display, live)
                    if updated.pop("_quit", False):
                        route = "quit"
                        break
                    cfg = updated
                    brain, notice = create_brain(cfg)
                    snapshots = registry.snapshot_all(cfg)
                    sirius_reply = notice or "★ Settings saved in the Master Study."
                    sirius_mood = "happy"
                    route = "home"
                    continue

                # ── Home Hub screen ───────────────────────────────────
                last_size = _sync_resize(last_size)
                anim_frame = (frame // 2) if cfg.get("animations_enabled", True) else 0
                live.update(
                    display.frame_center(
                        display.render_home_screen(
                            version=version,
                            snapshots=snapshots,
                            sirius_reply=sirius_reply,
                            sirius_mood=sirius_mood,
                            prompt_text=prompt.text,
                            prompt_cursor=prompt.cursor,
                            focus_zone=focus_zone,
                            selected_idx=selected_idx,
                            inline_result=inline_result,
                            frame=anim_frame,
                        )
                    )
                )
                key = read_key(timeout=0.25)
                frame += 1
                if key is None:
                    continue

                if key == "CTRL_C":
                    route = "quit"
                    break

                if key == "TAB":
                    focus_zone = "menu" if focus_zone == "prompt" else "prompt"
                    continue

                if focus_zone == "menu":
                    low = key.lower()
                    if key == "ESC" or low == "q":
                        route = "quit"
                        break
                    if key == "UP" or low == "k":
                        selected_idx = (selected_idx - 1) % len(HOME_MENU)
                    elif key == "DOWN" or low == "j":
                        selected_idx = (selected_idx + 1) % len(HOME_MENU)
                    elif key in ("/", "i"):
                        focus_zone = "prompt"
                    else:
                        chosen = None
                        if key in ("ENTER", "SPACE"):
                            chosen = HOME_MENU[selected_idx][0]
                        else:
                            for action_id, hotkey, _, _ in HOME_MENU:
                                if low == hotkey:
                                    chosen = action_id
                                    break
                        if chosen == "quit":
                            route = "quit"
                            break
                        if chosen == "pomo":
                            sirius_reply, sirius_mood, inline_result = _summon_buddy_interactive(
                                live, registry, cfg, "pomo", "open", {}
                            )
                            snapshots = registry.snapshot_all(cfg)
                        elif chosen in ("buddies", "log", "config"):
                            route = chosen
                    continue

                # ── Prompt focus mode ─────────────────────────────────
                if key == "ESC":
                    if prompt.text:
                        prompt.text = ""
                        prompt.cursor = 0
                    else:
                        focus_zone = "menu"
                    continue

                submitted = prompt.handle_key(key)
                if submitted is None:
                    continue

                plan = brain.plan(submitted, registry, cfg)
                if plan.target == "sirius":
                    if plan.action == "quit":
                        route = "quit"
                        break
                    if plan.action in ("buddies", "log", "config"):
                        route = plan.action
                        sirius_reply = plan.reply
                        sirius_mood = plan.mood
                        continue
                    if plan.action == "soul":
                        soul_target = plan.params.get("buddy", "sirius")
                        route = "soul"
                        continue
                    inline_result = None
                    sirius_reply = plan.reply
                    sirius_mood = plan.mood
                    if plan.action not in ("unknown", "clear"):
                        record_mission_outcome("sirius", plan.action, submitted or plan.action, registry, xp_gain=2)
                        snapshots = registry.snapshot_all(cfg)
                else:
                    sirius_reply, sirius_mood, inline_result = _summon_buddy_interactive(
                        live, registry, cfg, plan.target, plan.action, plan.params
                    )
                    snapshots = registry.snapshot_all(cfg)

    except KeyboardInterrupt:
        pass

    sirius_soul = registry.sirius.load_soul()
    sirius_core, _ = registry.sirius.load_core()
    farewell = sirius_soul.react("farewell", user=cfg.get("user_name", "friend"))
    console.print(display.render_goodbye_screen(farewell, sirius_core))
