"""Offline safe dev-cache & workspace clutter scanner/sweeper."""

from dataclasses import dataclass, field
import os
from pathlib import Path
import shutil

from castle.helpers.vitals import format_bytes_human

SAFE_CACHE_DIRS = frozenset({
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
})

SAFE_JUNK_FILES = frozenset({
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
})

HEAVY_REPORT_DIRS = frozenset({
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "target",
})

format_bytes = format_bytes_human


@dataclass
class ClutterItem:
    """Single discovered cache or heavy build directory/file."""

    path: Path
    category: str
    size_bytes: int
    safe_to_clean: bool


@dataclass
class SweepReport:
    """Summary of discovered workspace caches and reclaimable bytes."""

    root: Path
    items: list[ClutterItem] = field(default_factory=list)
    safe_bytes: int = 0
    safe_count: int = 0
    heavy_bytes: int = 0
    heavy_count: int = 0
    mood: str = "chill"
    comment: str = ""
    rows: list[tuple[str, str, str, str]] = field(default_factory=list)


def _dir_size(path: Path, max_entries: int = 4000) -> int:
    total = 0
    count = 0
    stack = [path]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for entry in it:
                    count += 1
                    if count > max_entries:
                        return total
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return total


def scan_clutter(target: Path | str | None = None, max_depth: int = 5) -> SweepReport:
    """Scan a workspace directory for safe-to-clean dev caches and heavy build folders."""
    root = Path(target).expanduser().resolve() if target else Path.cwd().resolve()
    if not root.exists() or not root.is_dir():
        return SweepReport(
            root=root,
            mood="alarmed",
            comment=f"Dude, `{root}` isn't a valid directory to scan.",
            rows=[("Path", "-", "-", "Not found")],
        )

    items: list[ClutterItem] = []
    stack: list[tuple[Path, int]] = [(root, 0)]

    while stack:
        cur, depth = stack.pop()
        try:
            with os.scandir(cur) as it:
                for entry in it:
                    name = entry.name
                    if name == ".git":
                        continue
                    try:
                        if entry.is_symlink():
                            continue
                        p = Path(entry.path)
                        if entry.is_dir(follow_symlinks=False):
                            if name in SAFE_CACHE_DIRS:
                                sz = _dir_size(p)
                                items.append(ClutterItem(p, name, sz, safe_to_clean=True))
                                continue
                            if name in HEAVY_REPORT_DIRS:
                                sz = _dir_size(p)
                                items.append(ClutterItem(p, name, sz, safe_to_clean=False))
                                continue
                            if depth < max_depth:
                                stack.append((p, depth + 1))
                        elif entry.is_file(follow_symlinks=False):
                            if name in SAFE_JUNK_FILES or name.endswith(".pyc"):
                                sz = entry.stat(follow_symlinks=False).st_size
                                cat = "junk file" if name in SAFE_JUNK_FILES else "*.pyc"
                                items.append(ClutterItem(p, cat, sz, safe_to_clean=True))
                    except OSError:
                        continue
        except OSError:
            continue

    safe_items = [i for i in items if i.safe_to_clean]
    heavy_items = [i for i in items if not i.safe_to_clean]
    safe_bytes = sum(i.size_bytes for i in safe_items)
    heavy_bytes = sum(i.size_bytes for i in heavy_items)

    # Aggregate summary rows by category for clean display
    by_cat: dict[tuple[str, bool], list[ClutterItem]] = {}
    for item in items:
        by_cat.setdefault((item.category, item.safe_to_clean), []).append(item)

    rows: list[tuple[str, str, str, str]] = []
    sorted_groups = sorted(
        by_cat.items(),
        key=lambda kv: (not kv[0][1], -sum(i.size_bytes for i in kv[1])),
    )
    for (cat, safe), group in sorted_groups[:10]:
        sz = sum(i.size_bytes for i in group)
        tag = "safe cache" if safe else "keep (manual)"
        rows.append((cat, str(len(group)), format_bytes_human(sz), tag))

    if not items:
        mood = "proud"
        comment = "Spotless, dude! Not even a single `__pycache__` tumbleweed in sight."
    elif safe_items:
        mood = "curious"
        comment = (
            f"Found {format_bytes_human(safe_bytes)} of safe cache clutter "
            f"({len(safe_items)} spot(s)), dude. Ready to vaporize whenever."
        )
    else:
        mood = "smug"
        comment = (
            f"Caches look tidy, dude—just {len(heavy_items)} heavy folder(s) "
            f"({format_bytes_human(heavy_bytes)}) sitting around."
        )

    return SweepReport(
        root=root,
        items=items,
        safe_bytes=safe_bytes,
        safe_count=len(safe_items),
        heavy_bytes=heavy_bytes,
        heavy_count=len(heavy_items),
        mood=mood,
        comment=comment,
        rows=rows,
    )


def clean_safe_caches(report: SweepReport) -> tuple[int, int, list[str]]:
    """Remove only verified `safe_to_clean` targets inside `report.root`.

    Returns `(removed_count, freed_bytes, errors)`.
    """
    root_resolved = report.root.resolve()
    removed = 0
    freed = 0
    errors: list[str] = []

    for item in report.items:
        if not item.safe_to_clean:
            continue
        try:
            resolved = item.path.resolve()
            if resolved == root_resolved or not resolved.is_relative_to(root_resolved):
                continue
            if resolved.is_dir():
                shutil.rmtree(resolved)
                removed += 1
                freed += item.size_bytes
            elif resolved.is_file():
                resolved.unlink()
                removed += 1
                freed += item.size_bytes
        except OSError as exc:
            errors.append(f"{item.path.name}: {exc}")

    return removed, freed, errors
