"""Brain provider protocol and structured intent plans for Sirius."""

from dataclasses import dataclass, field
from typing import Protocol

from mansion.buddies.registry import BuddyRegistry


@dataclass
class IntentPlan:
    """Structured decision produced by Sirius's brain."""

    target: str
    action: str
    params: dict = field(default_factory=dict)
    reply: str = ""
    mood: str = "happy"
    confidence: float = 1.0


class BrainProvider(Protocol):
    """Interface implemented by DeterministicBrain and future local LLM providers."""

    name: str

    def plan(self, text: str, registry: BuddyRegistry, config: dict) -> IntentPlan:
        """Interpret `text` into an IntentPlan targeting Sirius or a Mansion buddy."""
