"""Parser and manager for buddy soul.md personality files."""

from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
import re

from castle.storage import get_data_dir

_REACTION_RE = re.compile(r"^[-*]\s*([a-zA-Z0-9_]+)\s*:\s*(.+)$")


class _SafeFormatDict(dict):
    """Leave missing placeholders intact instead of raising KeyError."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


@dataclass
class SoulProfile:
    """Structured representation of a buddy's soul.md file."""

    buddy_id: str
    metadata: dict[str, str] = field(default_factory=dict)
    identity: str = ""
    traits: list[str] = field(default_factory=list)
    reactions: dict[str, str] = field(default_factory=dict)
    source_path: Path | None = None

    @property
    def name(self) -> str:
        return self.metadata.get("name", self.buddy_id.title())

    @property
    def role(self) -> str:
        return self.metadata.get("role", "Cyber Buddy")

    @property
    def room(self) -> str:
        return self.metadata.get("room", "Castle Hall")

    @property
    def signature(self) -> str:
        return self.metadata.get("signature", "★")

    @property
    def tone(self) -> str:
        return self.metadata.get("tone", "warm, friendly")

    @property
    def soul_version(self) -> int:
        try:
            return int(self.metadata.get("soul_version", "1"))
        except ValueError:
            return 1

    def react(self, event: str | list[str] | tuple[str, ...], fallback: str = "", **context) -> str:
        """Render the first matching reaction template using safe placeholder substitution."""
        keys = [event] if isinstance(event, str) else list(event)
        template = ""
        for key in keys:
            if key in self.reactions:
                template = self.reactions[key]
                break
        if not template:
            template = fallback or f"{self.signature} Ready whenever you are."
        return template.format_map(_SafeFormatDict(context))

    def to_system_prompt(self, core_state: dict | None = None) -> str:
        """Build a local-LLM-ready system prompt combining soul.md and core memory."""
        parts = [f"Name: {self.name} ({self.role})"]
        if self.tone:
            parts.append(f"Tone: {self.tone}")
        if self.identity:
            parts.append(f"Identity:\n{self.identity}")
        if self.traits:
            traits_text = "\n".join(f"- {t}" for t in self.traits)
            parts.append(f"Traits:\n{traits_text}")
        if core_state:
            lvl = core_state.get("level", 1)
            rank = core_state.get("rank", "Spark")
            missions = core_state.get("missions_completed", 0)
            parts.append(f"Core State: Lv.{lvl} {rank}, {missions} missions completed.")
            memory = core_state.get("memory") or {}
            if memory:
                parts.append(f"Memory: {memory}")
        return "\n\n".join(parts)


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def parse_soul_markdown(text: str, buddy_id: str, source_path: Path | None = None) -> SoulProfile:
    """Parse frontmatter and ## Identity / ## Traits / ## Reactions from soul.md."""
    lines = text.splitlines()
    metadata: dict[str, str] = {}
    idx = 0

    if lines and lines[0].strip() == "---":
        idx = 1
        while idx < len(lines) and lines[idx].strip() != "---":
            line = lines[idx].strip()
            if ":" in line:
                k, v = line.split(":", 1)
                metadata[k.strip().lower()] = _strip_quotes(v)
            idx += 1
        if idx < len(lines) and lines[idx].strip() == "---":
            idx += 1

    section = ""
    identity_lines: list[str] = []
    traits: list[str] = []
    reactions: dict[str, str] = {}

    for raw in lines[idx:]:
        stripped = raw.strip()
        if stripped.startswith("## "):
            section = stripped[3:].strip().lower()
            continue
        if not stripped:
            if section == "identity" and identity_lines:
                identity_lines.append("")
            continue
        if section == "identity":
            identity_lines.append(stripped)
        elif section == "traits":
            traits.append(stripped.lstrip("-* ").strip())
        elif section == "reactions":
            match = _REACTION_RE.match(stripped)
            if match:
                reactions[match.group(1).strip().lower()] = _strip_quotes(match.group(2))

    return SoulProfile(
        buddy_id=metadata.get("id", buddy_id),
        metadata=metadata,
        identity="\n".join(identity_lines).strip(),
        traits=traits,
        reactions=reactions,
        source_path=source_path,
    )


def get_local_soul_path(buddy_id: str) -> Path:
    """Return user-customizable soul.md path inside ~/.castle/buddies/<id>/."""
    return get_data_dir() / "buddies" / buddy_id / "soul.md"


def read_bundled_soul_text(buddy_id: str) -> str:
    """Read the default soul.md template shipped inside the castle package."""
    try:
        res = resources.files("castle.buddies").joinpath("souls", f"{buddy_id}.md")
        if res.is_file():
            return res.read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError, OSError):
        pass

    fallback = Path(__file__).parent / "souls" / f"{buddy_id}.md"
    if fallback.exists():
        return fallback.read_text(encoding="utf-8")
    return ""


def load_soul(buddy_id: str) -> SoulProfile:
    """Ensure local soul.md exists (preserving user edits) and parse it."""
    local_path = get_local_soul_path(buddy_id)
    if not local_path.exists():
        template = read_bundled_soul_text(buddy_id)
        if template:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_text(template, encoding="utf-8")

    if local_path.exists():
        try:
            text = local_path.read_text(encoding="utf-8")
            return parse_soul_markdown(text, buddy_id=buddy_id, source_path=local_path)
        except OSError:
            pass

    bundled = read_bundled_soul_text(buddy_id)
    return parse_soul_markdown(bundled, buddy_id=buddy_id, source_path=local_path)
