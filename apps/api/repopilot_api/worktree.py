from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .git import git_command
from .tools import repository_path


class WorktreeError(RuntimeError):
    """A safe worktree operation could not be completed."""


@dataclass(frozen=True)
class Change:
    path: str
    content: str


def _git(root: Path, *args: str, timeout: int = 30) -> str:
    result = subprocess.run(
        git_command(root, *args),
        check=False,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if result.returncode:
        raise WorktreeError(result.stderr.strip() or "git operation failed")
    return result.stdout


def create_worktree(root: Path, base_commit: str, task_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f-]{36}", task_id) or not re.fullmatch(
        r"[0-9a-f]{40,64}", base_commit
    ):
        raise WorktreeError("invalid task ID or commit")
    parent = root.parent / ".repopilot-worktrees"
    parent.mkdir(parents=True, exist_ok=True)
    path = (parent / task_id).resolve()
    if path.exists():
        raise WorktreeError("worktree path already exists")
    try:
        path.relative_to(root.resolve())
        raise WorktreeError("worktree cannot be nested inside the source repository")
    except ValueError:
        pass
    _git(root, "worktree", "add", "--detach", str(path), base_commit)
    return path


def write_changes(worktree: Path, changes: list[Change]) -> None:
    destinations = [repository_path(worktree, change.path) for change in changes]
    if len(set(destinations)) != len(changes):
        raise WorktreeError("duplicate change paths")
    paths: list[str] = []
    for change in changes:
        if not change.path or change.path.startswith("/") or ".." in Path(change.path).parts:
            raise WorktreeError(f"unsafe change path: {change.path}")
        destination = repository_path(worktree, change.path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(change.content, encoding="utf-8", newline="")
        paths.append(change.path)
    if paths:
        _git(worktree, "add", "-N", "--", *paths)


def diff(worktree: Path) -> tuple[str, str]:
    text = _git(worktree, "diff", "--no-ext-diff", "--no-textconv", "--binary")
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()


def remove_worktree(root: Path, worktree: Path) -> None:
    if worktree.exists():
        _git(root, "worktree", "remove", "--force", str(worktree))


def apply_patch(root: Path, text: str) -> None:
    for check in (True, False):
        result = subprocess.run(
            git_command(root, "apply", *(["--check"] if check else []), "--whitespace=nowarn", "-"),
            input=text.encode("utf-8"),
            cwd=root,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if result.returncode:
            raise WorktreeError(result.stderr.decode("utf-8", errors="replace"))
