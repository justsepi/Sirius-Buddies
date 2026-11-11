"""Rich BMO-inspired retro terminal UI and CLI output helpers for Sirius & the Castle."""

from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from castle.buddies.base import BuddyResult
from castle.buddies.registry import BuddySnapshot
from castle.buddies.soul import SoulProfile

console = Console()

PANEL_WIDTH = 70

HOME_MENU = [
    ("pomo", "1", "Summon Pomo", "Clocktower · Focus timer & stats"),
    ("buddies", "2", "Castle Directory", "Residents, rooms, souls & cores"),
    ("log", "3", "Mission Log", "Recent dispatches & evolutions"),
    ("config", "4", "Sirius Settings", "Name, brain, animations & paths"),
    ("quit", "q", "Sleep / Quit", "Rest the Castle console"),
]

CONFIG_ITEMS = [
    ("user_name", "Your name", "text"),
    ("brain_provider", "Sirius brain", "cycle"),
    ("animations_enabled", "Animations", "bool"),
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


def build_sirius_face(mood: str = "idle", frame: int = 0) -> Text:
    """Render Sirius's animated 5-row BMO-style CRT face."""
    alt = frame % 2
    blink = (frame % 20) == 19

    if mood == "working":
        crest = "  ✦  │  ✦  " if alt == 0 else "  ★  │  ★  "
        eyes = " >   < " if alt == 0 else " ★   ★ "
        mouth = "  ╰─◡─╯  "
        screen_style = "bold bright_green"
    elif mood == "happy":
        crest = "  ✦  │  ✦  " if alt == 0 else "  ·  │  ·  "
        eyes = " -   - " if blink else " ^   ^ "
        mouth = "  ╰─◡─╯  "
        screen_style = "bold bright_cyan"
    elif mood == "curious":
        crest = "  ?  │  ★  "
        eyes = " o   O "
        mouth = "   ───   "
        screen_style = "bold bright_yellow"
    elif mood == "sleeping":
        crest = "     │  zZ " if alt == 0 else "     │ zZ  "
        eyes = " -   - "
        mouth = "   ───   "
        screen_style = "dim bright_cyan"
    else:
        crest = "  ★  │  ✦  " if alt == 0 else "  ✦  │  ★  "
        eyes = " -   - " if blink else " ★   ★ "
        mouth = "  ╰───╯  "
        screen_style = "bold bright_cyan"

    face = Text()
    face.append(crest + "\n", style="bold bright_yellow")
    face.append("╭─────────╮\n", style="bright_cyan")
    face.append("│ ", style="bright_cyan")
    face.append(eyes, style=screen_style)
    face.append(" │\n", style="bright_cyan")
    face.append("│", style="bright_cyan")
    face.append(mouth, style=screen_style)
    face.append("│\n", style="bright_cyan")
    face.append("╰─▣─────▣─╯", style="bright_cyan")
    return face


def _xp_bar(xp: int, width: int = 10) -> str:
    """Render a compact progress bar toward the next core milestone."""
    filled = max(1 if xp > 0 else 0, min(width, (xp % 100) * width // 100))
    return "█" * filled + "░" * (width - filled)


def _render_result_table(result: BuddyResult, max_width: int) -> Table | None:
    if not result.table_headers or not result.table_rows:
        return None
    table = Table(
        box=box.SIMPLE,
        border_style="bright_cyan",
        header_style="bold bright_cyan",
        expand=False,
        pad_edge=False,
    )
    for col in result.table_headers:
        table.add_column(col, overflow="fold")
    for row in result.table_rows[:8]:
        table.add_row(*[_clip(str(cell), max(10, max_width // len(result.table_headers))) for cell in row])
    return table


class Display:
    """Responsible for rendering all Castle TUI screens and CLI summaries."""

    def frame_center(self, renderable, target_console: Console | None = None):
        c = target_console or console
        return Align.center(renderable, vertical="middle", height=max(1, c.size.height - 1))

    def render_home_screen(
        self,
        version: str,
        snapshots: list[BuddySnapshot],
        sirius_reply: str,
        sirius_mood: str,
        prompt_text: str,
        prompt_cursor: int,
        focus_zone: str,
        selected_idx: int,
        inline_result: BuddyResult | None = None,
        frame: int = 0,
        target_console: Console | None = None,
    ) -> Panel:
        """Render the BMO-inspired Castle Hub (face + speech + menu + prompt)."""
        width = _panel_width(72, target_console)
        inner_w = max(28, width - 6)

        sirius_snap = next((s for s in snapshots if s.buddy.id == "sirius"), None)
        pomo_snap = next((s for s in snapshots if s.buddy.id == "pomo"), None)

        face = build_sirius_face(mood=sirius_mood, frame=frame)
        speech = Text()
        speech.append("Sirius", style="bold bright_cyan")
        if sirius_snap:
            core = sirius_snap.core
            speech.append(f"  Lv.{core['level']} {core['rank']}", style="bright_yellow")
        speech.append("\n")
        speech.append(sirius_reply, style="bright_white")

        if width >= 56:
            hero = Table.grid(padding=(0, 2))
            hero.add_column(width=13)
            hero.add_column(width=max(20, inner_w - 15))
            hero.add_row(face, speech)
        else:
            hero = Table.grid()
            hero.add_column()
            hero.add_row(Align.center(face))
            hero.add_row(speech)

        body = Table.grid(expand=True, padding=(0, 0))
        body.add_column()
        body.add_row(hero)

        if inline_result and inline_result.table_rows:
            tbl = _render_result_table(inline_result, inner_w)
            if tbl is not None:
                body.add_row(Text(""))
                body.add_row(tbl)

        body.add_row(Text("─" * inner_w, style="dim bright_cyan"))

        status_line = Text()
        online_count = sum(1 for s in snapshots if s.status.available)
        status_line.append(f"Residents: {online_count}/{len(snapshots)} online", style="dim white")
        if pomo_snap:
            status_line.append("  ·  ", style="dim")
            status_line.append(f"Pomo: {pomo_snap.status.summary}", style="bright_green")
        body.add_row(status_line)
        body.add_row(Text(""))

        menu_badge = " [ACTIVE]" if focus_zone == "menu" else ""
        menu_hdr = Text(f"Castle Rooms{menu_badge}", style="bold bright_yellow" if focus_zone == "menu" else "dim bright_cyan")
        body.add_row(menu_hdr)

        for idx, (_, hotkey, label, desc) in enumerate(HOME_MENU):
            is_sel = focus_zone == "menu" and idx == selected_idx
            row_txt = Text()
            row_txt.append(" › " if is_sel else "   ", style="bold bright_cyan")
            row_txt.append(f"[{hotkey}] ", style="bold bright_yellow" if is_sel else "dim bright_yellow")
            row_txt.append(label, style="bold bright_white" if is_sel else "white")
            if inner_w >= 48:
                gap = max(2, 22 - len(label))
                row_txt.append(" " * gap + _clip(desc, max(8, inner_w - 30)), style="dim")
            body.add_row(row_txt)

        body.add_row(Text(""))
        prompt_active = focus_zone == "prompt"
        prompt_line = Text()
        prompt_line.append("sirius › ", style="bold bright_cyan" if prompt_active else "dim bright_cyan")
        if prompt_active:
            before = prompt_text[:prompt_cursor]
            at_cur = prompt_text[prompt_cursor : prompt_cursor + 1] or " "
            after = prompt_text[prompt_cursor + 1 :]
            prompt_line.append(before, style="bright_white")
            prompt_line.append(at_cur, style="black on bright_cyan")
            prompt_line.append(after, style="bright_white")
        else:
            shown = prompt_text or "press Tab or / to talk to Sirius..."
            prompt_line.append(_clip(shown, max(12, inner_w - 10)), style="dim")
        body.add_row(Panel(prompt_line, border_style="bright_cyan" if prompt_active else "dim", padding=(0, 1)))

        if prompt_active:
            hints = "Enter send · Tab menu · ↑↓ history · /help · Ctrl+C quit"
        else:
            hints = "↑↓ move · Enter select · 1-4 hotkeys · Tab or / prompt · q quit"
        body.add_row(Text(_clip(hints, inner_w), style="dim"))

        return Panel(
            body,
            title=f"[bold bright_cyan]★ THE CASTLE v{version} ★[/]",
            border_style="bright_cyan",
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
            info.append(f"({snap.soul.room}) ", style="bright_cyan")
            info.append(f"[{snap.status.state_label}]\n", style=state_style)
            info.append(f"Task: {_clip(snap.buddy.task_summary, inner_w - 18)}\n", style="white")
            info.append(
                f"Core v{snap.core['core_version']} · Lv.{snap.core['level']} {snap.core['rank']} "
                f"({_xp_bar(snap.core['xp'])} {snap.core['xp']} XP)\n",
                style="bright_yellow",
            )
            info.append(f"Status: {_clip(snap.status.summary, inner_w - 20)}", style="dim")

            card.add_row(badge_text, info)
            grid.add_row(
                Panel(
                    card,
                    border_style="bold bright_cyan" if selected else "dim",
                    padding=(0, 1),
                )
            )

        hints = "↑↓ choose · Enter summon/inspect · s view soul.md · Esc back"
        grid.add_row(Text(_clip(hints, inner_w), style="dim"))

        return Panel(
            grid,
            title="[bold bright_cyan]★ CASTLE DIRECTORY ★[/]",
            border_style="bright_cyan",
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
        txt.append(f"{soul.signature} {soul.name} — {soul.role}\n", style="bold bright_cyan")
        txt.append(f"Room: {soul.room} · Tone: {soul.tone}\n", style="dim")
        if soul.source_path:
            txt.append(f"soul.md: {_clip(str(soul.source_path), inner_w - 10)}\n\n", style="bright_yellow")

        txt.append("Identity\n", style="bold bright_white")
        txt.append((soul.identity or "(none)") + "\n\n", style="white")

        if soul.traits:
            txt.append("Traits\n", style="bold bright_white")
            for t in soul.traits[:5]:
                txt.append(f"  • {_clip(t, inner_w - 4)}\n", style="bright_green")
            txt.append("\n")

        txt.append(
            f"Core v{core['core_version']} · Lv.{core['level']} {core['rank']} ({core['xp']} XP)\n",
            style="bold bright_yellow",
        )
        for entry in (core.get("evolution_log") or [])[-4:]:
            txt.append(f"  › {_clip(entry, inner_w - 4)}\n", style="dim")

        if show_hints:
            txt.append("\nEsc/Enter/b back · q quit", style="dim")
        return Panel(
            txt,
            title=f"[bold bright_cyan]{soul.signature} SOUL & CORE[/]",
            border_style="bright_cyan",
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
            content = Text("No missions logged yet. Ask Sirius or summon Pomo!\n\nEsc/b back", style="dim")
        else:
            table = Table(box=box.SIMPLE, border_style="bright_cyan", header_style="bold bright_cyan")
            table.add_column("Time", style="dim", width=11)
            table.add_column("Buddy", style="bright_cyan", width=8)
            table.add_column("Action", style="bright_yellow", width=10)
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
            title="[bold bright_cyan]★ CASTLE MISSION LOG ★[/]",
            border_style="bright_cyan",
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
        """Render interactive Castle settings editor."""
        width = _panel_width(70, target_console)
        inner_w = max(28, width - 6)

        grid = Table.grid(expand=True)
        grid.add_column()

        for idx, (key, label, kind) in enumerate(CONFIG_ITEMS):
            sel = idx == selected_idx
            val = cfg.get(key, "")
            line = Text()
            line.append(" › " if sel else "   ", style="bold bright_cyan")
            line.append(f"{label:<20}", style="bold bright_white" if sel else "white")

            if sel and editing:
                line.append(f" [{edit_buf}_]", style="bold bright_yellow")
            elif kind == "bool":
                line.append(" ON " if val else " OFF", style="bold bright_green" if val else "dim")
            else:
                shown = str(val) if val else "(auto)"
                line.append(_clip(shown, max(10, inner_w - 26)), style="bright_cyan" if sel else "dim white")
            grid.add_row(line)

        if status_msg:
            grid.add_row(Text(""))
            grid.add_row(Text(_clip(status_msg, inner_w), style="bright_green"))

        grid.add_row(Text(""))
        hints = "Type value · Enter save · Esc cancel" if editing else "↑↓ select · Enter/Space toggle or edit · r reset · Esc back"
        grid.add_row(Text(_clip(hints, inner_w), style="dim"))

        return Panel(
            grid,
            title="[bold bright_cyan]⚙  SIRIUS SETTINGS[/]",
            border_style="bright_cyan",
            width=width,
            padding=(1, 2),
        )

    def render_goodbye_screen(
        self,
        farewell_line: str,
        sirius_core: dict,
        target_console: Console | None = None,
    ) -> Panel:
        """Render BMO-style goodbye card when leaving the Castle."""
        width = _panel_width(64, target_console)
        face = build_sirius_face(mood="sleeping", frame=0)
        body = Table.grid(padding=(0, 2))
        body.add_column(width=13)
        body.add_column()
        msg = Text()
        msg.append(farewell_line + "\n", style="bold bright_cyan")
        msg.append(
            f"Sirius Core Lv.{sirius_core['level']} {sirius_core['rank']} · "
            f"{sirius_core['missions_completed']} missions logged.",
            style="dim",
        )
        body.add_row(face, msg)
        return Panel(body, border_style="bright_cyan", width=width, padding=(1, 2))

    # ── Non-interactive CLI printers ─────────────────────────────────

    def print_status_cli(self, snapshots: list[BuddySnapshot], greeting: str, target_console: Console | None = None) -> None:
        out = target_console or console
        out.print()
        out.print(f"  [bold bright_cyan]{greeting}[/]")
        for snap in snapshots:
            state_style = "bright_green" if snap.status.available else "bright_red"
            out.print(
                f"  {snap.soul.signature} [bold]{snap.soul.name}[/] ({snap.soul.room}) "
                f"[{state_style}]{snap.status.state_label}[/] — "
                f"Lv.{snap.core['level']} {snap.core['rank']} · {snap.status.summary}"
            )
        out.print()

    def print_buddies_cli(self, snapshots: list[BuddySnapshot], target_console: Console | None = None) -> None:
        out = target_console or console
        table = Table(title="Castle Residents", border_style="bright_cyan", header_style="bold bright_cyan")
        table.add_column("Buddy", style="bold bright_white")
        table.add_column("Room", style="bright_cyan")
        table.add_column("Core", style="bright_yellow")
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
            out.print("\n  [dim]No Castle missions logged yet.[/]\n")
            return
        table = Table(title="Castle Mission Log", border_style="bright_cyan", header_style="bold bright_cyan")
        table.add_column("Timestamp", style="dim")
        table.add_column("Buddy", style="bright_cyan")
        table.add_column("Action", style="bright_yellow")
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

    def print_result_cli(
        self,
        sirius_reply: str,
        result: BuddyResult | None = None,
        levelups: list[str] | None = None,
        notice: str | None = None,
        target_console: Console | None = None,
    ) -> None:
        out = target_console or console
        out.print()
        if notice:
            out.print(f"  [dim yellow]{notice}[/]")
        out.print(f"  [bold bright_cyan]{sirius_reply}[/]")
        if result and result.message and result.message != sirius_reply:
            style = "bright_white" if result.ok else "bright_red"
            out.print(f"  [{style}]{result.message}[/]")
        if result and result.table_rows:
            tbl = _render_result_table(result, _panel_width(74, out))
            if tbl is not None:
                out.print(tbl)
        for msg in levelups or []:
            out.print(f"  [bold bright_yellow]{msg}[/]")
        out.print()
