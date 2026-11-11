"""Offline Git & workspace project scout."""

from dataclasses import dataclass, field
from pathlib import Path
import re
import shutil
import subprocess

STACK_MARKERS: tuple[tuple[str, str], ...] = (
    ("pyproject.toml", "Python (pyproject)"),
    ("requirements.txt", "Python (pip)"),
    ("package.json", "Node.js"),
    ("tsconfig.json", "TypeScript"),
    ("Cargo.toml", "Rust"),
    ("go.mod", "Go"),
    ("Makefile", "Make"),
    ("Dockerfile", "Docker"),
    ("install.sh", "Shell Installer"),
)


@dataclass
class RepoReport:
    """Structured workspace and Git status snapshot."""

    path: Path
    is_git: bool
    git_available: bool
    root: Path | None = None
    branch: str = ""
    detached: bool = False
    ahead: int = 0
    behind: int = 0
    staged: int = 0
    modified: int = 0
    untracked: int = 0
    changed_samples: list[str] = field(default_factory=list)
    last_commit: str = ""
    remote_url: str = ""
    stack: list[str] = field(default_factory=list)
    file_count: int = 0
    dir_count: int = 0
    mood: str = "chill"
    comment: str = ""
    rows: list[tuple[str, str]] = field(default_factory=list)


def _git(cwd: Path, *args: str, timeout: float = 2.5, strip: bool = True) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        out = proc.stdout.strip() if strip else proc.stdout.rstrip("\r\n")
        return proc.returncode == 0, out
    except (OSError, subprocess.SubprocessError):
        return False, ""


def _sanitize_remote(url: str) -> str:
    return re.sub(r"://([^/@:]+):([^/@]+)@", r"://\1:***@", url.strip())


def inspect_workspace(target: Path | str | None = None) -> RepoReport:
    """Inspect a project folder and its Git state completely offline."""
    path = Path(target).expanduser().resolve() if target else Path.cwd().resolve()
    if not path.exists():
        return RepoReport(
            path=path,
            is_git=False,
            git_available=bool(shutil.which("git")),
            mood="alarmed",
            comment=f"Dude, `{path}` doesn't even exist on this drive.",
            rows=[("Path", str(path)), ("Status", "Directory not found")],
        )

    stack = [label for marker, label in STACK_MARKERS if (path / marker).exists()]
    file_count = 0
    dir_count = 0
    try:
        for entry in path.iterdir():
            if entry.name == ".git":
                continue
            if entry.is_dir():
                dir_count += 1
            else:
                file_count += 1
    except OSError:
        pass

    git_exe = shutil.which("git")
    if not git_exe:
        rows = [
            ("Folder", str(path)),
            ("Entries", f"{file_count} files · {dir_count} dirs"),
            ("Stack", ", ".join(stack) if stack else "Plain folder"),
            ("Git", "git CLI not found on PATH"),
        ]
        return RepoReport(
            path=path,
            is_git=False,
            git_available=False,
            stack=stack,
            file_count=file_count,
            dir_count=dir_count,
            mood="curious",
            comment="No `git` CLI on PATH, dude—just gave ya the raw folder rundown.",
            rows=rows,
        )

    ok_root, root_out = _git(path, "rev-parse", "--show-toplevel")
    if not ok_root or not root_out:
        rows = [
            ("Folder", str(path)),
            ("Entries", f"{file_count} files · {dir_count} dirs"),
            ("Stack", ", ".join(stack) if stack else "Loose workspace"),
            ("Git", "Not a git repository"),
        ]
        return RepoReport(
            path=path,
            is_git=False,
            git_available=True,
            stack=stack,
            file_count=file_count,
            dir_count=dir_count,
            mood="chill",
            comment="No `.git` in here, dude—just raw loose files flyin' free in the void.",
            rows=rows,
        )

    repo_root = Path(root_out)
    # Refresh stack from repo root if inspecting a subfolder
    if repo_root != path:
        for marker, label in STACK_MARKERS:
            if (repo_root / marker).exists() and label not in stack:
                stack.append(label)

    ok_br, branch_out = _git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    detached = branch_out == "HEAD" or not ok_br
    branch = branch_out if ok_br and branch_out != "HEAD" else "HEAD (detached)"
    if detached:
        ok_sha, sha = _git(repo_root, "rev-parse", "--short", "HEAD")
        if ok_sha and sha:
            branch = f"detached@{sha}"

    ahead = behind = 0
    ok_ab, ab_out = _git(repo_root, "rev-list", "--left-right", "--count", "@{u}...HEAD")
    if ok_ab and ab_out:
        parts = ab_out.split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            behind, ahead = int(parts[0]), int(parts[1])

    staged = modified = untracked = 0
    changed_samples: list[str] = []
    ok_st, st_out = _git(repo_root, "status", "--porcelain", strip=False)
    if ok_st and st_out:
        for line in st_out.splitlines():
            if len(line) < 4:
                continue
            x, y = line[0], line[1]
            rel = line[3:].strip()
            tag = (x + y).strip() or "?"
            if x == "?" and y == "?":
                untracked += 1
                tag = "??"
            else:
                if x not in (" ", "?"):
                    staged += 1
                if y not in (" ", "?"):
                    modified += 1
            if len(changed_samples) < 6:
                changed_samples.append(f"{tag} {rel}")

    ok_log, log_out = _git(repo_root, "log", "-1", "--format=%h · %ar · %s")
    last_commit = log_out if ok_log and log_out else "(no commits yet)"

    ok_rem, rem_out = _git(repo_root, "remote", "get-url", "origin")
    remote_url = _sanitize_remote(rem_out) if ok_rem and rem_out else "(local only)"

    dirty_total = staged + modified + untracked
    sync_label = "in sync" if (ahead == 0 and behind == 0) else f"↑{ahead} ahead · ↓{behind} behind"
    dirty_label = (
        "clean working tree"
        if dirty_total == 0
        else f"{staged} staged · {modified} modified · {untracked} untracked"
    )

    rows: list[tuple[str, str]] = [
        ("Repo Root", str(repo_root)),
        ("Branch", f"{branch} ({sync_label})"),
        ("Worktree", dirty_label),
        ("Last Commit", last_commit),
        ("Stack", ", ".join(stack) if stack else "Generic"),
        ("Origin", remote_url),
    ]
    if changed_samples:
        rows.append(("Changes", ", ".join(changed_samples[:4])))

    if detached:
        mood = "alarmed"
        comment = f"Whoa, detached HEAD ({branch}), dude! Watch your step before committing."
    elif dirty_total == 0 and ahead == 0:
        mood = "proud"
        comment = f"Clean tree on `{branch}`, dude. Not a stray byte out of place. Respect."
    elif dirty_total == 0 and ahead > 0:
        mood = "smug"
        comment = f"Tree's clean on `{branch}`, dude—got {ahead} local commit(s) waitin' to push."
    elif dirty_total > 10:
        mood = "unimpressed"
        comment = f"{dirty_total} changed files hangin' loose on `{branch}`, dude?! Bold strategy."
    else:
        mood = "curious"
        comment = f"{dirty_total} uncommitted bit(s) on `{branch}`, dude. Livin' dangerously—just don't forget to commit."

    return RepoReport(
        path=path,
        is_git=True,
        git_available=True,
        root=repo_root,
        branch=branch,
        detached=detached,
        ahead=ahead,
        behind=behind,
        staged=staged,
        modified=modified,
        untracked=untracked,
        changed_samples=changed_samples,
        last_commit=last_commit,
        remote_url=remote_url,
        stack=stack,
        file_count=file_count,
        dir_count=dir_count,
        mood=mood,
        comment=comment,
        rows=rows,
    )
