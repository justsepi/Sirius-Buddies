"""Rich retro terminal UI and CLI output helpers for Sirius & the Castle."""

from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from castle.buddies.base import BuddyResult
from castle.buddies.registry import BuddySnapshot
from castle.buddies.soul import SoulProfile
from castle.ui.sirius_art import (
    COMPACT_WIDTH,
    FULL_WIDTH,
    SIRIUS_MOODS,
    build_sirius_sprite,
    get_mood_spec,
)

console = Console()

PANEL_WIDTH = 76

HOME_MENU = [
    ("pulse", "1", "System Pulse", "OS, CPU, RAM, disk & battery"),
    ("repo", "2", "Repo & Git Scout", "Branch, changes & project stack"),
    ("ports", "3", "Port Inspector", "Listening localhost & dev ports"),
    ("sweep", "4", "Cache Sweep", "Scan & tidy safe dev clutter"),
    ("timer", "5", "Quick Timer", "Built-in offline countdown"),
    ("pomo", "6", "Summon Pomo", "Clocktower · Pomodoro buddy"),
]

CONFIG_ITEMS = [
    ("user_name", "Your name", "text"),
    ("animations_enabled", "Animations", "bool"),
    ("show_shadow", "Floating shadow", "bool"),
    ("pomo_command", "Pomo CLI override", "text"),
]


def _panel_width(preferred: int = PANEL_WIDTH, target_console: Console | None = None) -> int:
    c = target_console or console
    return max(36, min(preferred, c.size.width - 2))


def _clip(text: str, max_len: int) -> str:
    if max_len <= 1:
        return ""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _bar(pct: int, width: int = 8) -> str:
    clamped = max(0, min(100, pct))
    filled = int(round(clamped * width / 100.0))
    return "█" * filled + "░" * (width - filled)


def _xp_bar(xp: int, width: int = 10) -> str:
    filled = max(1 if xp > 0 else 0, min(width, (xp % 100) * width // 100))
    return "█" * filled + "░" * (width - filled)


def _render_result_table(result: BuddyResult, max_width: int) -> Table | None:
    if not result.table_headers or not result.table_rows:
        return None
    table = Table(
        box=box.SIMPLE,
        border_style="bright_blue",
        header_style="bold bright_white",
        expand=False,
        pad_edge=False,
    )
    col_count = len(result.table_headers)
    for col in result.table_headers:
        table.add_column(col, overflow="fold")
    cell_cap = max(10, (max_width - col_count * 2) // col_count)
    for row in result.table_rows[:12]:
        table.add_row(*[_clip(str(cell), cell_cap) for cell in row])
    return table


def _sirius_hero_block(
    width: int,
    sirius_reply: str,
    sirius_mood: str,
    frame: int,
    show_shadow: bool,
    sirius_core: dict | None = None,
    subtitle: str = "",
) -> Table:
    """Render Sirius floating with shadow alongside his speech bubble."""
    inner_w = max(28, width - 6)
    compact_sprite = width < 48
    sprite = build_sirius_sprite(
        mood=sirius_mood,
        frame=frame,
        show_shadow=show_shadow,
        compact=compact_sprite,
    )
    spec = get_mood_spec(sirius_mood)

    speech = Text()
    speech.append("Sirius", style="bold bright_white")
    if sirius_core:
        charge = int((sirius_core.get("memory") or {}).get("charge", 85))
        speech.append(f"  Lv.{sirius_core['level']} {sirius_core['rank']}", style="bright_blue")
        speech.append(f" · Charge {_bar(charge, 6)} {charge}%", style="dim bright_blue")
    speech.append(f"\n[{spec.label}]", style="bold bright_blue")
    if subtitle:
        speech.append(f" · {subtitle}", style="dim")
    speech.append("\n" + "─" * max(16, min(42, inner_w - (24 if width >= 58 else 2))) + "\n", style="blue")
    speech.append(sirius_reply, style="bright_white")

    if width >= 58:
        hero = Table.grid(padding=(0, 2))
        hero.add_column(width=FULL_WIDTH if not compact_sprite else COMPACT_WIDTH)
        hero.add_column(width=max(22, inner_w - (FULL_WIDTH + 2)))
        hero.add_row(sprite, speech)
        return hero

    hero = Table.grid()
    hero.add_column()
    hero.add_row(Align.center(sprite))
    hero.add_row(speech)
    return hero


class Display:
    """Responsible for rendering all Sirius & Castle TUI screens and CLI summaries."""

    def frame_center(self, renderable, target_console: Console | None = None):
        c = target_console or console
        return Align.center(renderable, vertical="middle", height=max(1, c.size.height - 1))

    def render_home_screen(
        self,
        version: str,
        snapshots: list[BuddySnapshot],
        sirius_reply: str,
        sirius_mood: str,
        selected_idx: int,
        frame: int = 0,
        show_shadow: bool = True,
        host_label: str = "",
        target_console: Console | None = None,
    ) -> Panel:
        """Render the pure-keyboard Sirius & Castle Home Hub (zero AI/chat clutter)."""
        width = _panel_width(PANEL_WIDTH, target_console)
        inner_w = max(28, width - 6)

        sirius_snap = next((s for s in snapshots if s.buddy.id == "sirius"), None)
        pomo_snap = next((s for s in snapshots if s.buddy.id == "pomo"), None)

        hero = _sirius_hero_block(
            width=width,
            sirius_reply=sirius_reply,
            sirius_mood=sirius_mood,
            frame=frame,
            show_shadow=show_shadow,
            sirius_core=sirius_snap.core if sirius_snap else None,
            subtitle=host_label,
        )

        body = Table.grid(expand=True, padding=(0, 0))
        body.add_column()
        body.add_row(hero)
        body.add_row(Text("─" * inner_w, style="blue"))

        status_line = Text()
        online_count = sum(1 for s in snapshots if s.status.available)
        status_line.append(f"Buddies: {online_count}/{len(snapshots)} ready", style="dim bright_white")
        if pomo_snap:
            pomo_state = pomo_snap.status.summary if pomo_snap.status.available else "not installed (use Quick Timer!)"
            status_line.append("  ·  ", style="dim")
            status_line.append(f"Pomo: {pomo_state}", style="bright_blue")
        body.add_row(status_line)
        body.add_row(Text(""))

        body.add_row(Text("Device Helpers & Buddies", style="bold bright_blue"))
        for idx, (_, hotkey, label, desc) in enumerate(HOME_MENU):
            is_sel = idx == selected_idx
            row_txt = Text()
            row_txt.append(" › " if is_sel else "   ", style="bold bright_white")
            row_txt.append(f"[{hotkey}] ", style="bold bright_blue" if is_sel else "dim bright_blue")
            row_txt.append(label, style="bold bright_white" if is_sel else "white")
            if inner_w >= 48:
                gap = max(2, 20 - len(label))
                row_txt.append(" " * gap + _clip(desc, max(8, inner_w - 28)), style="dim")
            body.add_row(row_txt)

        body.add_row(Text(""))
        body.add_row(Text("─" * inner_w, style="dim blue"))

        # Keyboard hotkey strips (no mouse needed, no chat input!)
        bar1 = Text()
        for key, name in (("p", "Poke"), ("f", "Snack"), ("o", "Flip/Roll/Oracle"), ("m", "Moods")):
            bar1.append(f"[{key}]", style="bold bright_blue")
            bar1.append(f" {name}   ", style="bright_white")
        bar2 = Text()
        for key, name in (("d", "Buddies"), ("l", "Log"), ("s", "Settings"), ("r", "Refresh"), ("q", "Quit")):
            bar2.append(f"[{key}]", style="bold bright_blue")
            bar2.append(f" {name}   ", style="dim bright_white")
        body.add_row(Text(_clip(bar1.plain, inner_w)) if len(bar1.plain) > inner_w else bar1)
        body.add_row(Text(_clip(bar2.plain, inner_w), style="dim") if len(bar2.plain) > inner_w else bar2)

        hints = "↑↓/jk move · Enter run · 1-6 or letter hotkeys · q quit"
        body.add_row(Text(_clip(hints, inner_w), style="dim"))

        return Panel(
            body,
            title=f"[bold bright_white]✦ SIRIUS & THE CASTLE v{version} ✦[/]",
            border_style="bright_blue",
            width=width,
            padding=(1, 2),
        )

    def render_helper_screen(
        self,
        title: str,
        sirius_reply: str,
        sirius_mood: str,
        result: BuddyResult | None,
        frame: int = 0,
        show_shadow: bool = True,
        confirm_prompt: str = "",
        extra_hint: str = "",
        target_console: Console | None = None,
    ) -> Panel:
        """Render a device-helper result screen with Sirius floating at top."""
        width = _panel_width(PANEL_WIDTH, target_console)
        inner_w = max(28, width - 6)

        body = Table.grid(expand=True)
        body.add_column()
        body.add_row(
            _sirius_hero_block(
                width=width,
                sirius_reply=sirius_reply,
                sirius_mood=sirius_mood,
                frame=frame,
                show_shadow=show_shadow,
            )
        )
        body.add_row(Text("─" * inner_w, style="blue"))

        if result and result.table_rows:
            tbl = _render_result_table(result, inner_w)
            if tbl is not None:
                body.add_row(tbl)
        elif result:
            body.add_row(Text(result.message, style="white"))

        if confirm_prompt:
            body.add_row(Text(""))
            body.add_row(
                Panel(
                    Text(confirm_prompt, style="bold bright_white"),
                    border_style="bold bright_blue",
                    padding=(0, 1),
                )
            )

        body.add_row(Text(""))
        hints = f"{extra_hint} · " if extra_hint else ""
        hints += "r refresh · p poke · Esc/b back · q quit"
        body.add_row(Text(_clip(hints, inner_w), style="dim"))

        return Panel(
            body,
            title=f"[bold bright_white]✦ {title} ✦[/]",
            border_style="bright_blue",
            width=width,
            padding=(1, 2),
        )

    def render_timer_screen(
        self,
        minutes_set: int,
        remaining_secs: int,
        running: bool,
        finished: bool,
        frame: int = 0,
        show_shadow: bool = True,
        target_console: Console | None = None,
    ) -> Panel:
        """Render Sirius's built-in pure-offline keyboard Quick Timer."""
        width = _panel_width(68, target_console)
        inner_w = max(28, width - 6)

        total_secs = max(60, minutes_set * 60)
        mins, secs = divmod(max(0, remaining_secs), 60)
        elapsed_pct = int(round(((total_secs - remaining_secs) / total_secs) * 100)) if total_secs else 0

        if finished:
            mood = "hyped"
            msg = f"Time's up, dude! {minutes_set}m locked in clean. Stretch those wrists."
            state_tag = "DONE!"
        elif running:
            mood = "working"
            msg = f"Stayin' sharp on this {minutes_set}m block, dude. I'm keepin' watch."
            state_tag = "RUNNING"
        elif remaining_secs < total_secs:
            mood = "sleepy"
            msg = "Paused—catch your breath, dude. Space to roll again."
            state_tag = "PAUSED"
        else:
            mood = "chill"
            msg = f"Dialed to {minutes_set}m, dude. Hit Space whenever you're ready to roll."
            state_tag = "READY"

        body = Table.grid(expand=True)
        body.add_column()
        body.add_row(
            _sirius_hero_block(
                width=width,
                sirius_reply=msg,
                sirius_mood=mood,
                frame=frame,
                show_shadow=show_shadow,
                subtitle=state_tag,
            )
        )
        body.add_row(Text("─" * inner_w, style="blue"))

        clock = Text()
        clock.append(f"  {mins:02d}:{secs:02d}  ", style="bold bright_white on blue")
        clock.append(f"  {_bar(elapsed_pct, min(20, max(10, inner_w - 22)))}  {elapsed_pct}%", style="bright_blue")
        body.add_row(Text(""))
        body.add_row(Align.center(clock))
        body.add_row(Text(""))

        presets = Text()
        presets.append("Presets: ", style="dim")
        for key, m in (("1", 5), ("2", 15), ("3", 25), ("4", 45)):
            style = "bold bright_white" if minutes_set == m else "bright_blue"
            presets.append(f"[{key}] {m}m   ", style=style)
        body.add_row(Align.center(presets))
        body.add_row(Text(""))

        hints = "Space start/pause · +/- adjust min · 1-4 presets · r reset · Esc/b back"
        body.add_row(Text(_clip(hints, inner_w), style="dim"))

        return Panel(
            body,
            title="[bold bright_white]✦ QUICK TIMER ✦[/]",
            border_style="bright_blue",
            width=width,
            padding=(1, 2),
        )

    def render_moods_screen(
        self,
        mood_idx: int,
        frame: int = 0,
        show_shadow: bool = True,
        target_console: Console | None = None,
    ) -> Panel:
        """Interactive expression showcase cycling through all Sirius moods."""
        width = _panel_width(68, target_console)
        inner_w = max(28, width - 6)
        spec = SIRIUS_MOODS[mood_idx % len(SIRIUS_MOODS)]

        body = Table.grid(expand=True)
        body.add_column()
        body.add_row(
            _sirius_hero_block(
                width=width,
                sirius_reply=f"{spec.desc}. ({mood_idx + 1}/{len(SIRIUS_MOODS)})",
                sirius_mood=spec.id,
                frame=frame,
                show_shadow=show_shadow,
                subtitle=f"id: {spec.id}",
            )
        )
        body.add_row(Text("─" * inner_w, style="blue"))

        roster = Text()
        for idx, m in enumerate(SIRIUS_MOODS):
            if idx == mood_idx:
                roster.append(f" [{m.label}] ", style="bold bright_white on blue")
            else:
                roster.append(f" {m.label} ", style="dim bright_blue")
        body.add_row(roster)
        body.add_row(Text(""))
        body.add_row(Text(_clip("←/→ or ↑/↓ cycle moods · Space next · Esc/b back", inner_w), style="dim"))

        return Panel(
            body,
            title="[bold bright_white]✦ SIRIUS EXPRESSIONS ✦[/]",
            border_style="bright_blue",
            width=width,
            padding=(1, 2),
        )

    def render_toys_screen(
        self,
        sirius_reply: str,
        sirius_mood: str,
        headline: str,
        frame: int = 0,
        show_shadow: bool = True,
        target_console: Console | None = None,
    ) -> Panel:
        """Render Cosmic Flip, Dice Roll, Oracle, Snack & Poke deck."""
        width = _panel_width(68, target_console)
        inner_w = max(28, width - 6)

        body = Table.grid(expand=True)
        body.add_column()
        body.add_row(
            _sirius_hero_block(
                width=width,
                sirius_reply=sirius_reply,
                sirius_mood=sirius_mood,
                frame=frame,
                show_shadow=show_shadow,
                subtitle=headline or "Buddy Deck",
            )
        )
        body.add_row(Text("─" * inner_w, style="blue"))

        actions = [
            ("1", "Flip Cosmic Coin", "Heads or tails"),
            ("2", "Roll d20", "Tabletop critical check"),
            ("3", "Roll d6", "Quick six-sided roll"),
            ("4", "Cosmic Oracle", "Deadpan yes/no call"),
            ("f", "Toss Snack", "Boost Sirius's core charge"),
            ("p", "Poke Sirius", "Test his cosmic patience"),
        ]
        for key, label, desc in actions:
            row = Text()
            row.append(f"  [{key}] ", style="bold bright_blue")
            row.append(f"{label:<18}", style="bold bright_white")
            if inner_w >= 46:
                row.append(_clip(desc, max(8, inner_w - 26)), style="dim")
            body.add_row(row)

        body.add_row(Text(""))
        body.add_row(Text(_clip("Press 1-4, f, or p · Esc/b back · q quit", inner_w), style="dim"))

        return Panel(
            body,
            title="[bold bright_white]✦ COSMIC TOYS & INTERACTIONS ✦[/]",
            border_style="bright_blue",
            width=width,
            padding=(1, 2),
        )

    def render_directory_screen(
        self,
        snapshots: list[BuddySnapshot],
        selected_idx: int,
        frame: int = 0,
        target_console: Console | None = None,
    ) -> Panel:
        """Render the Castle Directory showing every buddy's room, soul, and evolving core."""
        width = _panel_width(74, target_console)
        inner_w = max(28, width - 6)

        grid = Table.grid(expand=True)
        grid.add_column()

        for idx, snap in enumerate(snapshots):
            selected = idx == selected_idx
            badge = snap.buddy.badge_lines(frame=frame)
            state_style = "bright_green" if snap.status.available else "bright_red"

            card = Table.grid(padding=(0, 2))
            card.add_column(width=9)
            card.add_column(width=max(18, inner_w - 13))

            badge_text = Text()
            for line_str, line_style in badge:
                badge_text.append(line_str + "\n", style=line_style)

            info = Text()
            info.append(f"{snap.soul.name} ", style="bold bright_white")
            info.append(f"({snap.soul.room}) ", style="bright_blue")
            info.append(f"[{snap.status.state_label}]\n", style=state_style)
            info.append(f"Task: {_clip(snap.buddy.task_summary, inner_w - 18)}\n", style="white")
            info.append(
                f"Core v{snap.core['core_version']} · Lv.{snap.core['level']} {snap.core['rank']} "
                f"({_xp_bar(snap.core['xp'])} {snap.core['xp']} XP)\n",
                style="bright_blue",
            )
            info.append(f"Status: {_clip(snap.status.summary, inner_w - 20)}", style="dim")

            card.add_row(badge_text, info)
            grid.add_row(
                Panel(
                    card,
                    border_style="bold bright_white" if selected else "dim blue",
                    padding=(0, 1),
                )
            )

        hints = "↑↓/jk choose · Enter summon/inspect · s view soul.md · Esc/b back"
        grid.add_row(Text(_clip(hints, inner_w), style="dim"))

        return Panel(
            grid,
            title="[bold bright_white]✦ CASTLE BUDDIES ✦[/]",
            border_style="bright_blue",
            width=width,
            padding=(1, 2),
        )

    def render_soul_screen(
        self,
        soul: SoulProfile,
        core: dict,
        show_hints: bool = True,
        target_console: Console | None = None,
    ) -> Panel:
        """Render a buddy's soul.md personality and evolving core history."""
        width = _panel_width(72, target_console)
        inner_w = max(28, width - 6)

        txt = Text()
        txt.append(f"{soul.signature} {soul.name} — {soul.role}\n", style="bold bright_white")
        txt.append(f"Room: {soul.room} · Tone: {soul.tone}\n", style="dim")
        if soul.source_path:
            txt.append(f"soul.md: {_clip(str(soul.source_path), inner_w - 10)}\n\n", style="bright_blue")

        txt.append("Identity\n", style="bold bright_blue")
        txt.append((soul.identity or "(none)") + "\n\n", style="white")

        if soul.traits:
            txt.append("Traits\n", style="bold bright_blue")
            for t in soul.traits[:5]:
                txt.append(f"  • {_clip(t, inner_w - 4)}\n", style="bright_white")
            txt.append("\n")

        txt.append(
            f"Core v{core['core_version']} · Lv.{core['level']} {core['rank']} ({core['xp']} XP)\n",
            style="bold bright_blue",
        )
        for entry in (core.get("evolution_log") or [])[-4:]:
            txt.append(f"  › {_clip(entry, inner_w - 4)}\n", style="dim")

        if show_hints:
            txt.append("\nEsc/Enter/b back · q quit", style="dim")
        return Panel(
            txt,
            title=f"[bold bright_white]{soul.signature} SOUL & CORE[/]",
            border_style="bright_blue",
            width=width,
            padding=(1, 2),
        )

    def render_log_screen(
        self,
        events: list[dict],
        target_console: Console | None = None,
    ) -> Panel:
        """Render recent Castle mission chronicle."""
        width = _panel_width(74, target_console)
        inner_w = max(28, width - 6)

        if not events:
            content = Text("No missions logged yet, dude. Run Pulse, Repo, or Pomo!\n\nEsc/b back", style="dim")
        else:
            table = Table(box=box.SIMPLE, border_style="bright_blue", header_style="bold bright_white")
            table.add_column("Time", style="dim", width=11)
            table.add_column("Buddy", style="bright_blue", width=8)
            table.add_column("Action", style="bold bright_white", width=10)
            table.add_column("Summary", style="white")
            for ev in events[:12]:
                stamp = str(ev.get("timestamp", ""))[5:16].replace("T", " ")
                table.add_row(
                    stamp,
                    str(ev.get("buddy", "")),
                    str(ev.get("action", "")),
                    _clip(str(ev.get("summary", "")), max(12, inner_w - 36)),
                )
            grid = Table.grid()
            grid.add_column()
            grid.add_row(table)
            grid.add_row(Text("Esc/Enter/b back · q quit", style="dim"))
            content = grid

        return Panel(
            content,
            title="[bold bright_white]✦ CASTLE MISSION LOG ✦[/]",
            border_style="bright_blue",
            width=width,
            padding=(1, 2),
        )

    def render_config_screen(
        self,
        cfg: dict,
        selected_idx: int,
        editing: bool = False,
        edit_buf: str = "",
        status_msg: str = "",
        target_console: Console | None = None,
    ) -> Panel:
        """Render interactive keyboard Castle settings editor."""
        width = _panel_width(70, target_console)
        inner_w = max(28, width - 6)

        grid = Table.grid(expand=True)
        grid.add_column()

        for idx, (key, label, kind) in enumerate(CONFIG_ITEMS):
            sel = idx == selected_idx
            val = cfg.get(key, "")
            line = Text()
            line.append(" › " if sel else "   ", style="bold bright_white")
            line.append(f"{label:<20}", style="bold bright_white" if sel else "white")

            if sel and editing:
                line.append(f" [{edit_buf}_]", style="bold bright_blue")
            elif kind == "bool":
                line.append(" ON " if val else " OFF", style="bold bright_blue" if val else "dim")
            else:
                shown = str(val) if val else "(auto)"
                line.append(_clip(shown, max(10, inner_w - 26)), style="bright_blue" if sel else "dim white")
            grid.add_row(line)

        if status_msg:
            grid.add_row(Text(""))
            grid.add_row(Text(_clip(status_msg, inner_w), style="bright_blue"))

        grid.add_row(Text(""))
        hints = "Type value · Enter save · Esc cancel" if editing else "↑↓/jk select · Enter/Space toggle or edit · r reset · Esc/b back"
        grid.add_row(Text(_clip(hints, inner_w), style="dim"))

        return Panel(
            grid,
            title="[bold bright_white]⚙  CASTLE SETTINGS[/]",
            border_style="bright_blue",
            width=width,
            padding=(1, 2),
        )

    def render_goodbye_screen(
        self,
        farewell_line: str,
        sirius_core: dict,
        show_shadow: bool = True,
        target_console: Console | None = None,
    ) -> Panel:
        """Render floating sleepy Sirius farewell card."""
        width = _panel_width(66, target_console)
        compact = width < 48
        sprite = build_sirius_sprite(mood="sleepy", frame=1, show_shadow=show_shadow, compact=compact)
        msg = Text()
        msg.append(farewell_line + "\n\n", style="bold bright_white")
        msg.append(
            f"Sirius Core Lv.{sirius_core['level']} {sirius_core['rank']} · "
            f"{sirius_core['missions_completed']} ops logged.",
            style="bright_blue",
        )
        if width >= 54:
            body = Table.grid(padding=(0, 2))
            body.add_column(width=COMPACT_WIDTH if compact else FULL_WIDTH)
            body.add_column()
            body.add_row(sprite, msg)
        else:
            body = Table.grid()
            body.add_column()
            body.add_row(Align.center(sprite))
            body.add_row(msg)
        return Panel(body, border_style="bright_blue", width=width, padding=(1, 2))

    # ── Non-interactive / one-shot CLI printers ──────────────────────

    def print_sirius_cli(
        self,
        message: str,
        mood: str = "chill",
        result: BuddyResult | None = None,
        levelups: list[str] | None = None,
        show_shadow: bool = True,
        target_console: Console | None = None,
    ) -> None:
        """Render Sirius's floating star + visible shadow right in CLI output."""
        out = target_console or console
        width = _panel_width(PANEL_WIDTH, out)
        compact = width < 52
        sprite = build_sirius_sprite(mood=mood, frame=0, show_shadow=show_shadow, compact=compact)

        text_col = Text()
        text_col.append(message, style="bold bright_white")
        if result and result.message and result.message != message:
            style = "white" if result.ok else "bright_red"
            text_col.append(f"\n{result.message}", style=style)

        out.print()
        if width >= 52:
            hero = Table.grid(padding=(0, 2))
            hero.add_column(width=COMPACT_WIDTH if compact else FULL_WIDTH)
            hero.add_column(width=max(20, width - (COMPACT_WIDTH if compact else FULL_WIDTH) - 4))
            hero.add_row(sprite, text_col)
            out.print(hero)
        else:
            out.print(sprite)
            out.print(text_col)

        if result and result.table_rows:
            tbl = _render_result_table(result, width)
            if tbl is not None:
                out.print(tbl)

        for msg in levelups or []:
            out.print(f"  [bold bright_blue]{msg}[/]")
        out.print()

    def print_status_cli(
        self,
        snapshots: list[BuddySnapshot],
        greeting: str,
        mood: str = "chill",
        show_shadow: bool = True,
        target_console: Console | None = None,
    ) -> None:
        out = target_console or console
        self.print_sirius_cli(greeting, mood=mood, show_shadow=show_shadow, target_console=out)
        for snap in snapshots:
            state_style = "bright_green" if snap.status.available else "bright_red"
            out.print(
                f"  {snap.soul.signature} [bold bright_white]{snap.soul.name}[/] ({snap.soul.room}) "
                f"[{state_style}]{snap.status.state_label}[/] — "
                f"Lv.{snap.core['level']} {snap.core['rank']} · {snap.status.summary}"
            )
        out.print()

    def print_buddies_cli(self, snapshots: list[BuddySnapshot], target_console: Console | None = None) -> None:
        out = target_console or console
        table = Table(title="Castle Buddies", border_style="bright_blue", header_style="bold bright_white")
        table.add_column("Buddy", style="bold bright_white")
        table.add_column("Room", style="bright_blue")
        table.add_column("Core", style="bright_blue")
        table.add_column("Task", style="white")
        table.add_column("Status")
        for snap in snapshots:
            tag = "[bright_green]online[/]" if snap.status.available else "[bright_red]not installed[/]"
            table.add_row(
                f"{snap.soul.signature} {snap.soul.name}",
                snap.soul.room,
                f"v{snap.core['core_version']} · Lv.{snap.core['level']} {snap.core['rank']}",
                snap.buddy.task_summary,
                f"{tag} ({snap.status.summary})",
            )
        out.print()
        out.print(table)
        out.print()

    def print_log_cli(self, events: list[dict], target_console: Console | None = None) -> None:
        out = target_console or console
        if not events:
            out.print("\n  [dim]No Castle missions logged yet, dude.[/]\n")
            return
        table = Table(title="Castle Mission Log", border_style="bright_blue", header_style="bold bright_white")
        table.add_column("Timestamp", style="dim")
        table.add_column("Buddy", style="bright_blue")
        table.add_column("Action", style="bold bright_white")
        table.add_column("Summary")
        for ev in events:
            table.add_row(
                str(ev.get("timestamp", "")),
                str(ev.get("buddy", "")),
                str(ev.get("action", "")),
                str(ev.get("summary", "")),
            )
        out.print()
        out.print(table)
        out.print()

    def print_soul_cli(self, soul: SoulProfile, core: dict, target_console: Console | None = None) -> None:
        out = target_console or console
        out.print()
        out.print(self.render_soul_screen(soul, core, show_hints=False, target_console=out))
        out.print()
