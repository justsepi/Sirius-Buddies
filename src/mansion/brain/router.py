"""Deterministic offline intent router driven by buddy soul.md profiles."""

from datetime import datetime
import re
import shlex

from mansion.brain.base import IntentPlan
from mansion.buddies.pomo import POMO_PRESETS
from mansion.buddies.registry import BuddyRegistry

_MINUTES_RE = re.compile(r"\b(\d{1,3})\s*(?:m|min|mins|minute|minutes)\b", re.IGNORECASE)
_DAYS_RE = re.compile(r"\b(\d{1,3})\s*(?:d|day|days)\b", re.IGNORECASE)
_TASK_RE = re.compile(r"\b(?:on|for|about)\s+(.+)$", re.IGNORECASE)

_GREETINGS = {"hi", "hello", "hey", "yo", "sup", "morning", "afternoon", "evening"}
_FAREWELLS = {"quit", "exit", "bye", "goodbye", "sleep", "goodnight"}


def _time_greeting_key(now: datetime | None = None) -> str:
    hour = (now or datetime.now()).hour
    if 5 <= hour < 12:
        return "greet_morning"
    if 12 <= hour < 18:
        return "greet_afternoon"
    return "greet_evening"


def _clean_task(raw: str) -> str:
    cleaned = raw.strip().strip("\"'").strip()
    return cleaned[:80]


def _extract_pomo_start_params(text: str) -> dict:
    """Extract preset, focus minutes, and task label from natural text or CLI flags."""
    params: dict = {}
    lower = text.lower()

    if "deep work" in lower:
        params["preset"] = "deep"
    else:
        for preset in POMO_PRESETS:
            if re.search(rf"\b{preset}\b", lower):
                params["preset"] = preset
                break

    min_match = _MINUTES_RE.search(lower)
    if min_match:
        minutes = int(min_match.group(1))
        if minutes >= 1:
            params["focus"] = min(minutes, 180)

    # Support explicit `-t "label"` or `--task label`
    try:
        tokens = shlex.split(text)
    except ValueError:
        tokens = text.split()
    for idx, tok in enumerate(tokens):
        if tok in ("-t", "--task") and idx + 1 < len(tokens):
            params["task"] = _clean_task(tokens[idx + 1])
            return params

    # Strip time modifier (and orphaned preposition before it like "... for 25m")
    text_for_task = re.sub(
        r"\b(?:for|on|about)?\s*\d{1,3}\s*(?:m|min|mins|minute|minutes)\b",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    task_match = _TASK_RE.search(text_for_task)
    if task_match:
        candidate = _clean_task(task_match.group(1))
        candidate = re.sub(r"\s+\b(?:for|on|about)$", "", candidate, flags=re.IGNORECASE).strip()
        if candidate and candidate.lower() not in POMO_PRESETS:
            params["task"] = candidate

    return params


def _extract_pomo_action(text: str, registry: BuddyRegistry, config: dict) -> IntentPlan:
    """Route a Pomo-related utterance to open, start, status, history, or config."""
    lower = text.lower().strip()
    sirius_soul = registry.sirius.load_soul()
    pomo_buddy = registry.get("pomo")
    pomo_soul = pomo_buddy.load_soul() if pomo_buddy else sirius_soul
    dispatch_reply = sirius_soul.react(
        "dispatch",
        buddy=pomo_soul.name,
        room=pomo_soul.room,
    )

    if any(w in lower for w in ("config", "setting", "settings")):
        return IntentPlan("pomo", "config", {}, dispatch_reply, mood="happy")

    if any(w in lower for w in ("history", "past", "week", "last ")):
        day_match = _DAYS_RE.search(lower)
        days = int(day_match.group(1)) if day_match else (14 if "two week" in lower else 7)
        return IntentPlan("pomo", "history", {"days": max(1, days)}, dispatch_reply, mood="happy")

    wants_start = any(
        w in lower for w in ("start", "begin", "focus", "timer", "deep work", "sprint", "classic", "quick")
    ) or bool(_MINUTES_RE.search(lower))

    if any(w in lower for w in ("status", "stats", "today", "how many")) and "start" not in lower:
        return IntentPlan("pomo", "status", {}, dispatch_reply, mood="happy")

    if lower in ("pomo", "/pomo", "open pomo", "summon pomo", "launch pomo") or (
        any(w in lower for w in ("open", "launch", "summon")) and not wants_start
    ):
        return IntentPlan("pomo", "open", {}, dispatch_reply, mood="working")

    params = _extract_pomo_start_params(text)
    return IntentPlan("pomo", "start", params, dispatch_reply, mood="working")


class DeterministicBrain:
    """Fast, offline rule & intent router backed by buddy soul.md templates."""

    name = "deterministic"

    def plan(self, text: str, registry: BuddyRegistry, config: dict) -> IntentPlan:
        raw = text.strip()
        lower = raw.lower()
        sirius = registry.sirius
        sirius_soul = sirius.load_soul()
        sirius_core, _ = sirius.load_core()
        user = config.get("user_name", "friend")

        pomo = registry.get("pomo")
        pomo_summary = pomo.check_status(config).summary if pomo else "Mansion ready."

        if not raw:
            key = _time_greeting_key()
            reply = sirius_soul.react([key, "greet"], user=user, summary=pomo_summary)
            return IntentPlan("sirius", "greet", {}, reply, mood="happy")

        # ── Explicit slash commands ───────────────────────────────────
        if lower.startswith("/"):
            parts = raw[1:].strip().split(None, 1)
            cmd = parts[0].lower() if parts else ""
            rest = parts[1].strip() if len(parts) > 1 else ""

            if cmd in ("help", "?"):
                return IntentPlan("sirius", "help", {}, sirius_soul.react("help", user=user), mood="happy")
            if cmd in ("buddies", "residents", "roster", "rooms", "dir", "directory"):
                return IntentPlan("sirius", "buddies", {}, f"{sirius_soul.signature} Opening Mansion Directory.", mood="happy")
            if cmd in ("status", "today"):
                return IntentPlan("sirius", "status", {}, f"{sirius_soul.signature} Checking Mansion pulse.", mood="happy")
            if cmd in ("log", "journal", "missions"):
                return IntentPlan("sirius", "log", {}, f"{sirius_soul.signature} Opening Mission Log.", mood="happy")
            if cmd in ("config", "settings"):
                return IntentPlan("sirius", "config", {}, f"{sirius_soul.signature} Opening Settings.", mood="happy")
            if cmd == "soul":
                return IntentPlan("sirius", "soul", {"buddy": rest or "sirius"}, f"{sirius_soul.signature} Reading soul.md.", mood="curious")
            if cmd == "clear":
                return IntentPlan("sirius", "clear", {}, f"{sirius_soul.signature} Screen tidied up!", mood="happy")
            if cmd in _FAREWELLS or cmd == "q":
                return IntentPlan("sirius", "quit", {}, sirius_soul.react("farewell", user=user), mood="sleeping")
            if cmd in ("pomo", "focus"):
                return _extract_pomo_action(f"pomo {rest}".strip(), registry, config)
            if cmd == "summon" and rest:
                target_name = rest.split()[0]
                if registry.get(target_name) and registry.get(target_name).id == "pomo":
                    return _extract_pomo_action(rest, registry, config)
                return IntentPlan("sirius", "unknown", {"query": raw}, sirius_soul.react("unknown", query=raw), mood="curious", confidence=0.0)
            return IntentPlan("sirius", "unknown", {"query": raw}, sirius_soul.react("unknown", query=raw), mood="curious", confidence=0.0)

        # ── Conversational greetings / farewells / help ───────────────
        cleaned_words = re.sub(r"[^\w\s]", "", lower).split()
        if lower in ("?", "help") or any(
            phrase in lower for phrase in ("who are you", "what can you do", "help me", "commands")
        ):
            return IntentPlan("sirius", "help", {}, sirius_soul.react("help", user=user), mood="happy")

        if cleaned_words and cleaned_words[0] in _GREETINGS and len(cleaned_words) <= 3:
            key = _time_greeting_key()
            reply = sirius_soul.react([key, "greet"], user=user, summary=pomo_summary)
            return IntentPlan("sirius", "greet", {}, reply, mood="happy")

        if lower in _FAREWELLS:
            return IntentPlan("sirius", "quit", {}, sirius_soul.react("farewell", user=user), mood="sleeping")

        if re.match(r"^(?:view|show|inspect|read)?\s*soul\b", lower):
            tokens = raw.split()
            target = tokens[-1] if len(tokens) > 1 and tokens[-1].lower() != "soul" else "sirius"
            return IntentPlan(
                "sirius",
                "soul",
                {"buddy": target},
                f"{sirius_soul.signature} Inspecting {target}'s soul.md.",
                mood="curious",
            )

        # ── Specialist buddy intents (Pomo / Focus) ───────────────────
        pomo_keywords = (
            "pomo",
            "pomidor",
            "pomodoro",
            "pomodoros",
            "focus",
            "timer",
            "clocktower",
            "deep work",
            "sprint",
        )
        if any(k in lower for k in pomo_keywords) or bool(_MINUTES_RE.search(lower)):
            return _extract_pomo_action(raw, registry, config)

        # ── Mansion-level intents ─────────────────────────────────────
        if any(k in lower for k in ("buddies", "residents", "roster", "who lives", "mansion", "rooms", "cores")):
            return IntentPlan(
                "sirius",
                "buddies",
                {},
                f"{sirius_soul.signature} Here's everyone living in the Mansion (Sirius Lv.{sirius_core['level']}).",
                mood="happy",
            )

        if any(k in lower for k in ("log", "journal", "missions", "activity", "history")):
            return IntentPlan("sirius", "log", {}, f"{sirius_soul.signature} Checking the Mansion chronicle.", mood="happy")

        if any(k in lower for k in ("config", "settings")):
            return IntentPlan("sirius", "config", {}, f"{sirius_soul.signature} Checking Mansion settings.", mood="happy")

        if any(k in lower for k in ("status", "today", "summary", "how am i doing")):
            return IntentPlan(
                "sirius",
                "status",
                {},
                f"{sirius_soul.signature} Mansion pulse for {user}: {pomo_summary}",
                mood="happy",
            )

        return IntentPlan(
            "sirius",
            "unknown",
            {"query": raw},
            sirius_soul.react("unknown", query=raw, user=user),
            mood="curious",
            confidence=0.0,
        )
