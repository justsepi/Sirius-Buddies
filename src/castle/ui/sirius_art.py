"""Retro star sprite, expressions, and floating shadow renderer for Sirius."""

from dataclasses import dataclass

from rich.text import Text

FULL_WIDTH = 21
COMPACT_WIDTH = 13


@dataclass(frozen=True)
class MoodSpec:
    """Visual expression spec for Sirius inside the bright-white star core."""

    id: str
    label: str
    eyes: str  # exactly 9 cells for full core
    mouth: str  # exactly 9 cells for full core
    compact_eyes: str  # exactly 5 cells for compact core
    compact_mouth: str  # exactly 5 cells for compact core
    blink_eyes: str = "  ─   ─  "
    desc: str = ""


SIRIUS_MOODS: tuple[MoodSpec, ...] = (
    MoodSpec(
        id="chill",
        label="Chill",
        eyes="  •   •  ",
        mouth="   ╰─╯   ",
        compact_eyes=" • • ",
        compact_mouth=" ╰─╯ ",
        desc="Cruisin' effortless in low-earth orbit",
    ),
    MoodSpec(
        id="happy",
        label="Happy",
        eyes="  ^   ^  ",
        mouth="   ╰◡╯   ",
        compact_eyes=" ^ ^ ",
        compact_mouth=" ╰◡╯ ",
        desc="Bright, warm, firing on all photons",
    ),
    MoodSpec(
        id="smug",
        label="Smug",
        eyes="  ¬   ¬  ",
        mouth="    ─╯   ",
        compact_eyes=" ¬ ¬ ",
        compact_mouth="  ─╯ ",
        desc="Powerful and knows it, dude",
    ),
    MoodSpec(
        id="wink",
        label="Witty",
        eyes="  ;   •  ",
        mouth="   ╰─╯   ",
        compact_eyes=" ; • ",
        compact_mouth=" ╰─╯ ",
        blink_eyes="  ─   •  ",
        desc="Sharp, cheeky, one step ahead",
    ),
    MoodSpec(
        id="curious",
        label="Curious",
        eyes="  o   O  ",
        mouth="    ─    ",
        compact_eyes=" o O ",
        compact_mouth="  ─  ",
        desc="Squinting at weird machine readings",
    ),
    MoodSpec(
        id="working",
        label="Focused",
        eyes="  >   <  ",
        mouth="   ───   ",
        compact_eyes=" > < ",
        compact_mouth=" ─── ",
        blink_eyes="  ◈   ◈  ",
        desc="Core locked in, diffraction rays humming",
    ),
    MoodSpec(
        id="proud",
        label="Proud",
        eyes=" ■▀─▀■   "[:9],  # pixel shades centered: " ■▀─▀■ " -> padded to 9
        mouth="    ─╯   ",
        compact_eyes=" ■─■ ",
        compact_mouth="  ─╯ ",
        blink_eyes="  ■   ■  ",
        desc="Shades on, clean tree on deck",
    ),
    MoodSpec(
        id="amused",
        label="Amused",
        eyes="  ^   ^  ",
        mouth="   ╰▽╯   ",
        compact_eyes=" ^ ^ ",
        compact_mouth=" ╰▽╯ ",
        desc="Cracking up at the cosmic chaos",
    ),
    MoodSpec(
        id="unimpressed",
        label="Deadpan",
        eyes="  ─   ─  ",
        mouth="   ───   ",
        compact_eyes=" ─ ─ ",
        compact_mouth=" ─── ",
        desc="Giving you the 'really, dude?' stare",
    ),
    MoodSpec(
        id="alarmed",
        label="Whoa!",
        eyes="  O   O  ",
        mouth="   ╭─╮   ",
        compact_eyes=" O O ",
        compact_mouth=" ╭─╮ ",
        blink_eyes="  ×   ×  ",
        desc="Knows when stuff is about to go sideways",
    ),
    MoodSpec(
        id="sleepy",
        label="Dozing",
        eyes="  ─   ─  ",
        mouth="    ᴗ    ",
        compact_eyes=" ─ ─ ",
        compact_mouth="  ᴗ  ",
        desc="Low-simmer power-saving hover",
    ),
    MoodSpec(
        id="hyped",
        label="Cosmic",
        eyes="  ✦   ✦  ",
        mouth="   ╰∀╯   ",
        compact_eyes=" ✦ ✦ ",
        compact_mouth=" ╰∀╯ ",
        blink_eyes="  ★   ★  ",
        desc="Binary flare, full dazzling output",
    ),
)

# Normalize proud shades cleanly to 9 exact cells: "  ■▀─▀■  " -> wait: 2 + 5 + 2 = 9!
_MOOD_MAP: dict[str, MoodSpec] = {m.id: m for m in SIRIUS_MOODS}
_MOOD_MAP["proud"] = MoodSpec(
    id="proud",
    label="Proud",
    eyes=" ■▀───▀■ ",
    mouth="    ─╯   ",
    compact_eyes=" ■─■ ",
    compact_mouth="  ─╯ ",
    blink_eyes=" ■▀───▀■ ",
    desc="Shades on, clean tree on deck",
)
SIRIUS_MOODS = tuple(_MOOD_MAP[m.id] for m in SIRIUS_MOODS)


def get_mood_spec(mood: str) -> MoodSpec:
    """Return the MoodSpec for `mood`, defaulting safely to `chill`."""
    aliases = {
        "idle": "chill",
        "listening": "curious",
        "sleeping": "sleepy",
        "deadpan": "unimpressed",
        "witty": "wink",
        "focused": "working",
        "cosmic": "hyped",
    }
    key = aliases.get(mood.lower().strip(), mood.lower().strip())
    return _MOOD_MAP.get(key, _MOOD_MAP["chill"])


def list_mood_ids() -> list[str]:
    """Return all canonical mood identifiers."""
    return [m.id for m in SIRIUS_MOODS]


def _append_seg(out: Text, segments: list[tuple[str, str]]) -> None:
    for chunk, style in segments:
        if chunk:
            out.append(chunk, style=style)


def _shadow_line(width: int, bob: int, mood_id: str, frame: int) -> list[tuple[str, str]]:
    """Build the floating shadow line anchored beneath Sirius."""
    if width == COMPACT_WIDTH:
        core = "░▒▓▓▓▒░" if bob == 0 else "░▒▓▓▓▓▓▒░"
        pad = (COMPACT_WIDTH - len(core)) // 2
        return [
            (" " * pad, ""),
            (core[:2], "dim blue"),
            (core[2:-2], "blue"),
            (core[-2:], "dim blue"),
            (" " * (COMPACT_WIDTH - pad - len(core)), ""),
        ]

    # Full 21-column shadow: tighter when Sirius floats higher (bob == 0), wider when lower (bob == 1)
    if bob == 0:
        left_pad, edge_l, center, edge_r = 7, "░▒", "▓▓▓", "▒░"
    else:
        left_pad, edge_l, center, edge_r = 6, "░▒", "▓▓▓▓▓", "▒░"

    if mood_id == "alarmed":
        left_pad += -1 if (frame % 2 == 0) else 1

    right_pad = FULL_WIDTH - left_pad - len(edge_l) - len(center) - len(edge_r)
    return [
        (" " * max(0, left_pad), ""),
        (edge_l, "dim blue"),
        (center, "blue"),
        (edge_r, "dim blue"),
        (" " * max(0, right_pad), ""),
    ]


def build_sirius_sprite(
    mood: str = "chill",
    frame: int = 0,
    show_shadow: bool = True,
    compact: bool = False,
) -> Text:
    """Render Sirius as a floating bright-white & blue retro star with visible shadow."""
    spec = get_mood_spec(mood)
    alt = frame % 2
    pulse = frame % 4
    blink = (frame % 18) == 17 and spec.id not in ("alarmed", "sleepy", "proud")

    if spec.id == "sleepy":
        bob = 1
    elif spec.id in ("amused", "hyped"):
        bob = alt
    elif spec.id == "alarmed":
        bob = 0
    else:
        bob = (frame // 2) % 2

    top_glint = ("✦" if alt == 0 else "·") if spec.id not in ("sleepy",) else "·"
    side_glint = "✦" if pulse == 0 else ("+" if pulse == 2 else "·")
    sirius_b = "✦" if (frame % 6) in (0, 1) else "·"  # companion dot in lower-left quadrant

    if spec.id in ("hyped", "working") and alt == 1:
        outer_ray_style = "bold bright_white"
        mid_ray_style = "bold bright_blue"
    elif spec.id == "sleepy":
        outer_ray_style = "blue"
        mid_ray_style = "bright_blue"
    elif spec.id == "alarmed" and alt == 1:
        outer_ray_style = "bold bright_white"
        mid_ray_style = "bold bright_white"
    else:
        outer_ray_style = "bright_blue"
        mid_ray_style = "bold bright_blue"

    face_style = "bold blue on bright_white"
    core_cap_style = "bold bright_white on blue"
    halo_style = "bright_blue"
    ray_root_style = "bold bright_white"

    if compact:
        eyes = spec.compact_eyes
        mouth = spec.compact_mouth
        if blink:
            eyes = " ─ ─ "

        ray_tl = "*" if (spec.id == "alarmed" and alt == 1) else "╲"
        ray_tr = "*" if (spec.id == "alarmed" and alt == 1) else "╱"
        top_orbit = "z" if (spec.id == "sleepy" and alt == 0) else ("Z" if spec.id == "sleepy" else " ")
        top_orbit = "?" if spec.id == "curious" else top_orbit

        sprite_rows: list[list[tuple[str, str]]] = [
            [
                (" ", ""),
                (ray_tl, outer_ray_style),
                ("    ", ""),
                (top_glint, "bold bright_white"),
                ("  ", ""),
                (top_orbit, "bright_blue"),
                (" ", ""),
                (ray_tr, outer_ray_style),
                (" ", ""),
            ],
            [
                ("  ", ""),
                ("╲", mid_ray_style),
                (" ", ""),
                ("▄███▄", core_cap_style),
                (" ", ""),
                ("╱", mid_ray_style),
                ("  ", ""),
            ],
            [
                (" ", ""),
                (side_glint, "bright_blue"),
                (" ", ""),
                ("╲", ray_root_style),
                (eyes, face_style),
                ("╱", ray_root_style),
                (" ", ""),
                (side_glint, "bright_blue"),
                (" ", ""),
            ],
            [
                (" ", ""),
                (side_glint, "blue"),
                (" ", ""),
                ("╱", ray_root_style),
                (mouth, face_style),
                ("╲", ray_root_style),
                (" ", ""),
                (side_glint, "blue"),
                (" ", ""),
            ],
            [
                ("  ", ""),
                ("╱", mid_ray_style),
                (" ", ""),
                ("▀███▀", core_cap_style),
                (" ", ""),
                ("╲", mid_ray_style),
                ("  ", ""),
            ],
        ]
        empty_row = [(" " * COMPACT_WIDTH, "")]
        rows = (sprite_rows + [empty_row]) if bob == 0 else ([empty_row] + sprite_rows)
        if show_shadow:
            rows.append(_shadow_line(COMPACT_WIDTH, bob, spec.id, frame))
    else:
        eyes = spec.blink_eyes if blink else spec.eyes
        mouth = spec.mouth
        if spec.id in ("working", "hyped") and alt == 1 and not blink:
            eyes = spec.blink_eyes

        ray_tl = "*" if (spec.id == "alarmed" and alt == 1) else "╲"
        ray_tr = "*" if (spec.id == "alarmed" and alt == 1) else "╱"
        ray_bl = "*" if (spec.id == "alarmed" and alt == 1) else "╱"
        ray_br = "*" if (spec.id == "alarmed" and alt == 1) else "╲"

        sky_mark = " "
        if spec.id == "sleepy":
            sky_mark = "z" if alt == 0 else "Z"
        elif spec.id == "curious":
            sky_mark = "?"

        sprite_rows = [
            # Row 0: outer upper diffraction spikes + top zenith spark (21 cols)
            [
                (" ", ""),
                (ray_tl, outer_ray_style),
                ("        ", ""),
                (top_glint, "bold bright_white"),
                ("     ", ""),
                (sky_mark, "bold bright_blue"),
                ("  ", ""),
                (ray_tr, outer_ray_style),
                (" ", ""),
            ],
            # Row 1: inner upper spikes + blue halo + top white core curve (21 cols)
            [
                ("   ", ""),
                ("╲", mid_ray_style),
                ("  ", ""),
                ("░", halo_style),
                ("▄█████▄", core_cap_style),
                ("░", halo_style),
                ("  ", ""),
                ("╱", mid_ray_style),
                ("   ", ""),
            ],
            # Row 2: horizontal flare + bright white core eyes row (21 cols)
            [
                ("  ", ""),
                (side_glint, "bright_blue"),
                ("  ", ""),
                ("╲", ray_root_style),
                (eyes, face_style),
                ("╱", ray_root_style),
                ("  ", ""),
                (side_glint, "bright_blue"),
                ("  ", ""),
            ],
            # Row 3: horizontal flare + bright white core mouth row (21 cols)
            [
                ("  ", ""),
                (side_glint, "blue"),
                ("  ", ""),
                ("╱", ray_root_style),
                (mouth, face_style),
                ("╲", ray_root_style),
                ("  ", ""),
                (side_glint, "blue"),
                ("  ", ""),
            ],
            # Row 4: inner lower spikes + blue halo + bottom white core curve (21 cols)
            [
                ("   ", ""),
                ("╱", mid_ray_style),
                ("  ", ""),
                ("░", halo_style),
                ("▀█████▀", core_cap_style),
                ("░", halo_style),
                ("  ", ""),
                ("╲", mid_ray_style),
                ("   ", ""),
            ],
            # Row 5: outer lower diffraction spikes + companion Sirius B star at col 4 (21 cols)
            [
                (" ", ""),
                (ray_bl, outer_ray_style),
                ("  ", ""),
                (sirius_b, "bold bright_white" if sirius_b == "✦" else "bright_blue"),
                ("     ", ""),
                ("·", "blue"),
                ("        ", ""),
                (ray_br, outer_ray_style),
                (" ", ""),
            ],
        ]

        empty_row = [(" " * FULL_WIDTH, "")]
        rows = (sprite_rows + [empty_row]) if bob == 0 else ([empty_row] + sprite_rows)
        if show_shadow:
            rows.append(_shadow_line(FULL_WIDTH, bob, spec.id, frame))

    out = Text()
    for idx, row in enumerate(rows):
        _append_seg(out, row)
        if idx < len(rows) - 1:
            out.append("\n")
    return out


def build_sirius_badge(frame: int = 0) -> list[tuple[str, str]]:
    """Return a 4-line floating white-and-blue star badge with shadow for directory cards."""
    alt = frame % 2
    eyes = " ─ ─ " if (frame % 12) == 11 else (" ^ ^ " if alt == 1 else " • • ")
    shadow = "  ░░░  " if alt == 0 else " ░▒▒▒░ "
    return [
        (" ╲ ✦ ╱ " if alt == 0 else " ╲ · ╱ ", "bold bright_blue"),
        (f" ·{eyes[1:4]}· ", "bold bright_white"),
        (" ╱ ◡ ╲ ", "bright_blue"),
        (shadow, "dim blue"),
    ]
