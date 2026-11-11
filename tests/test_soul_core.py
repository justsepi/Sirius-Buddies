"""Tests for buddy soul.md parsing, customization preservation, and evolving core.json."""

import mansion.buddies.core as core_mod
from mansion.buddies.soul import get_local_soul_path, load_soul, parse_soul_markdown


def test_soul_materializes_and_preserves_user_edits(tmp_path, monkeypatch):
    monkeypatch.setenv("MANSION_DIR", str(tmp_path))

    soul = load_soul("sirius")
    local_file = get_local_soul_path("sirius")
    assert local_file.exists()
    assert soul.name == "Sirius"
    assert soul.room == "Master Study"
    assert "Hey Sepi" in soul.react("greet", user="Sepi", summary="All good.")

    # Customizing local soul.md persists across subsequent loads
    custom_md = local_file.read_text(encoding="utf-8").replace(
        "Hey {user}!",
        "Yo {user}, star-deck ready!",
    )
    local_file.write_text(custom_md, encoding="utf-8")

    reloaded = load_soul("sirius")
    assert "Yo Sepi, star-deck ready!" in reloaded.react("greet", user="Sepi", summary="Ready.")
    # Missing placeholder never raises KeyError
    assert "{missing_var}" in parse_soul_markdown(
        "## Reactions\n- hi: \"Hi {missing_var}\"\n", "x"
    ).react("hi")

    prompt = reloaded.to_system_prompt({"level": 2, "rank": "Lantern", "missions_completed": 5, "memory": {"a": 1}})
    assert "Sirius" in prompt
    assert "Lv.2 Lantern" in prompt


def test_core_awakening_migration_and_level_evolution(tmp_path, monkeypatch):
    monkeypatch.setenv("MANSION_DIR", str(tmp_path))

    core, evolved = core_mod.load_or_evolve_core(
        buddy_id="pomo",
        target_version=1,
        soul_version=1,
        room="Clocktower",
    )
    assert evolved is True
    assert core["core_version"] == 1
    assert core["level"] == 1
    assert core_mod.os_key() in core["machine_facts"]

    # Record missions to trigger XP level-up (threshold 30 -> Lv.2)
    core, leveled = core_mod.record_mission(
        buddy_id="pomo",
        xp_gain=35,
        memory_updates={"last_preset": "deep"},
        machine_updates={"pomo_available": True},
    )
    assert leveled is True
    assert core["level"] == 2
    assert core["rank"] == "Sprout"
    assert core["memory"]["last_preset"] == "deep"
    assert core["machine_facts"][core_mod.os_key()]["pomo_available"] is True

    # Simulate release upgrade v1 -> v2 via migrate_fn without losing XP or memory
    def migrate(data: dict, next_ver: int) -> dict:
        if next_ver == 2:
            data.setdefault("memory", {})["streak_ready"] = True
        return data

    upgraded, did_evolve = core_mod.load_or_evolve_core(
        buddy_id="pomo",
        target_version=2,
        soul_version=1,
        room="Clocktower",
        migrate_fn=migrate,
    )
    assert did_evolve is True
    assert upgraded["core_version"] == 2
    assert upgraded["xp"] == 35
    assert upgraded["memory"]["last_preset"] == "deep"
    assert upgraded["memory"]["streak_ready"] is True
    assert any("v1 -> v2" in line for line in upgraded["evolution_log"])
