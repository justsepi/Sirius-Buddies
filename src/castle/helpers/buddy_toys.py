"""Classic cyber-buddy interactions & offline decision micro-tools for Sirius."""

from dataclasses import dataclass
import random

SNACKS: tuple[tuple[str, str, int, str, str], ...] = (
    (
        "espresso",
        "Solar Espresso",
        20,
        "hyped",
        "Mmm—double-shot solar espresso. Now we're cookin', dude!",
    ),
    (
        "photon",
        "Blueberry Photon",
        15,
        "happy",
        "Blueberry photon? Tastes like blue static and good decisions, dude.",
    ),
    (
        "pretzel",
        "Stardust Pretzel",
        12,
        "smug",
        "Crunchy stardust pretzel. Little salty, kinda like a PR review, dude.",
    ),
    (
        "pizza",
        "Cold Cosmic Pizza",
        18,
        "amused",
        "Cold pizza from last orbit? Honestly best fuel in the galaxy, dude.",
    ),
    (
        "tea",
        "Midnight Tea",
        10,
        "chill",
        "Nice warm mug of tea, dude. Even bright stars gotta chill sometimes.",
    ),
)

_ORACLE_ANSWERS: tuple[tuple[str, str], ...] = (
    ("smug", "Yeah dude, send it. Stars are aligned and I'm watchin'."),
    ("unimpressed", "Hard pass, dude. Trust the vibes on this one."),
    ("wink", "Fifty-fifty, dude—flip a coin and blame me if it flops."),
    ("happy", "Outlook's bright blue and cosmic, dude. Do it."),
    ("alarmed", "Whoa, hold up—maybe check your backups first, dude."),
    ("chill", "Honestly? Doesn't matter much either way, dude. Pick the fun one."),
    ("proud", "Lock it in, dude. That's a winner right there."),
    ("curious", "Ask again after coffee, dude—my star-charts are hazy."),
)

_POKE_LINES: tuple[tuple[str, str], ...] = (
    ("wink", "Whoa—easy on the plasma, dude! Tickles."),
    ("happy", "Haha, alright dude, you found the poke button. Feel better?"),
    ("smug", "Look, I could fry a router from orbit, dude—I just don't feel like gettin' up."),
    ("unimpressed", "Seriously, dude? Keep pokin' and I'm convertin' your tabs to spaces."),
    ("alarmed", "HEY! Watch the diffraction spikes, dude, I just polished those!"),
    ("amused", "Okay, respect the persistence, dude. Still not doin' your laundry though."),
)


@dataclass(frozen=True)
class ToyResult:
    """Result from a cyber-buddy interaction or micro-tool."""

    mood: str
    message: str
    headline: str = ""
    charge: int | None = None


def poke_sirius(poke_count: int) -> ToyResult:
    """Return Sirius's escalating cyber-buddy reaction to being poked."""
    idx = max(0, poke_count) % len(_POKE_LINES)
    mood, line = _POKE_LINES[idx]
    return ToyResult(mood=mood, message=f"✦ {line}")


def feed_sirius(current_charge: int, snack_id: str | None = None) -> ToyResult:
    """Feed Sirius a cosmic snack and boost his star-core charge (0..100)."""
    chosen = None
    if snack_id:
        needle = snack_id.strip().lower()
        for entry in SNACKS:
            if entry[0] == needle or needle in entry[1].lower():
                chosen = entry
                break
    if chosen is None:
        chosen = random.choice(SNACKS)

    _, label, boost, mood, line = chosen
    new_charge = min(100, max(0, current_charge) + boost)
    return ToyResult(
        mood=mood,
        message=f"✦ [{label}] {line}",
        headline=f"Charge {new_charge}% (+{boost}%)",
        charge=new_charge,
    )


def flip_coin() -> ToyResult:
    """Flip a cosmic coin offline."""
    side = random.choice(("HEADS", "TAILS"))
    if side == "HEADS":
        return ToyResult(
            mood="smug",
            headline="HEADS ✦",
            message="✦ HEADS, dude. Told ya the bright side wins.",
        )
    return ToyResult(
        mood="wink",
        headline="TAILS ○",
        message="✦ TAILS, dude. Shadow side takes this round.",
    )


def roll_dice(sides: int = 20) -> ToyResult:
    """Roll an N-sided die with Sirius commentary."""
    sides = max(2, min(1000, sides))
    val = random.randint(1, sides)
    if val == sides:
        return ToyResult(
            mood="hyped",
            headline=f"d{sides} → {val}!",
            message=f"✦ Rolled {val} on d{sides}—NAT MAX, DUDE!! Pure starlight!",
        )
    if val == 1:
        return ToyResult(
            mood="alarmed",
            headline=f"d{sides} → 1...",
            message=f"✦ Ooof, rolled a 1 on d{sides}, dude. Even I can't spin that—good luck!",
        )
    if val >= (sides * 0.7):
        return ToyResult(
            mood="happy",
            headline=f"d{sides} → {val}",
            message=f"✦ Rolled {val} on d{sides}. Solid toss, dude.",
        )
    return ToyResult(
        mood="chill",
        headline=f"d{sides} → {val}",
        message=f"✦ Rolled {val} on d{sides}. Could be worse, dude.",
    )


def cosmic_oracle() -> ToyResult:
    """Return a sharp deadpan offline cosmic oracle decision."""
    mood, line = random.choice(_ORACLE_ANSWERS)
    return ToyResult(mood=mood, headline="COSMIC CALL", message=f"✦ {line}")
