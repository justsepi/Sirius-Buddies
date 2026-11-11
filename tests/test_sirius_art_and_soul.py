"""Tests for Sirius retro star sprite, 12 expressions, floating shadow, and soul."""

from pathlib import Path

from rich.cells import cell_len

from castle.buddies.soul import load_soul, parse_soul_markdown
from castle.ui.sirius_art import (
    COMPACT_WIDTH,
    FULL_WIDTH,
    SIRIUS_MOODS,
    build_sirius_badge,
    build_sirius_sprite,
    get_mood_spec,
)


def test_sirius_sprite_all_moods_widths_colors_and_shadow():
    for compact in (False, True):
        expected_w = COMPACT_WIDTH if compact else FULL_WIDTH
        for spec in SIRIUS_MOODS:
            for frame in range(4):
                sprite = build_sirius_sprite(
                    mood=spec.id,
                    frame=frame,
                    show_shadow=True,
                    compact=compact,
                )
                lines = sprite.plain.splitlines()
                assert len(lines) >= 6
                for line in lines:
                    assert cell_len(line) == expected_w
                # Floating shadow must be visible on bottom line
                assert any(ch in lines[-1] for ch in ("░", "▒", "▓"))

                # Colors must stay strictly bright white and blue
                for span in sprite.spans:
                    style = str(span.style).lower()
                    assert "red" not in style
                    assert "green" not in style
                    assert "yellow" not in style
                    assert "magenta" not in style

    # Alias lookup falls back cleanly
    assert get_mood_spec("idle").id == "chill"
    assert get_mood_spec("unknown_mood").id == "chill"

    badge = build_sirius_badge(frame=0)
    assert len(badge) == 4
    assert any("░" in line for line, _ in badge)


def test_sirius_soul_personality_variants_and_clean_docs(tmp_path, monkeypatch):
    monkeypatch.setenv("CASTLE_DIR", str(tmp_path))

    soul = load_soul("sirius")
    assert soul.name == "Sirius"
    assert "dude" in soul.react("greet", variant_index=0, user="Sepi", summary="Ready.").lower()
    assert len(soul.reaction_variants.get("idle", [])) >= 3

    # Check multi-variant rotation deterministically
    v0 = soul.react("idle", variant_index=0)
    v1 = soul.react("idle", variant_index=1)
    assert v0 != v1

    # Missing placeholder never raises KeyError
    parsed = parse_soul_markdown("## Reactions\n- hi: \"Yo {missing_var}, dude\"\n", "x")
    assert "{missing_var}" in parsed.react("hi")

    # Ensure no disallowed inspiration or AI/chat references appear in Sirius docs or source
    repo_root = Path(__file__).resolve().parents[1]
    for path in (
        repo_root / "README.md",
        repo_root / "src" / "castle" / "buddies" / "souls" / "sirius.md",
    ):
        text = path.read_text(encoding="utf-8").lower()
        assert "jake" not in text
        assert "adventure time" not in text
        assert "ollama" not in text
