from __future__ import annotations

import os
import subprocess
from pathlib import Path

from pathspec import GitIgnoreSpec


class GitError(RuntimeError):
    """Raised when a repository cannot be inspected safely."""


def git_command(repository: Path, *args: str) -> list[str]:
    """Disable repository-configured executable hooks and filters for local operations."""
    command = [
        "git",
        "--no-optional-locks",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.hooksPath=" + ("NUL" if os.name == "nt" else "/dev/null"),
    ]
    filters = subprocess.run(
        [
            *command,
            "config",
            "--local",
            "--null",
            "--name-only",
            "--get-regexp",
            r"^filter\..*\.(clean|smudge|process|required)$",
        ],
        cwd=repository,
        capture_output=True,
        timeout=5,
        check=False,
    )
    for key in filters.stdout.decode("utf-8", errors="strict").split("\0"):
        if key:
            command.extend(["-c", key + ("=false" if key.endswith(".required") else "=")])
    return [*command, *args]


def _run(repository: Path, *args: str) -> str:
    result = subprocess.run(
        git_command(repository, *args),
        cwd=repository,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or "git command failed"
        raise GitError(message)
    return result.stdout.strip()


def repository_metadata(path: Path) -> dict[str, str | bool]:
    root = Path(_run(path, "rev-parse", "--show-toplevel")).resolve()
    if root != path.resolve():
        raise GitError("path must be the root of a Git repository")
    branch = _run(path, "branch", "--show-current") or "detached"
    commit = _run(path, "rev-parse", "HEAD")
    dirty = bool(_run(path, "status", "--porcelain"))
    return {"branch": branch, "current_commit": commit, "dirty": dirty}


def tracked_and_unignored_files(path: Path) -> list[str]:
    output = subprocess.run(
        git_command(path, "ls-files", "--cached", "--others", "--exclude-standard", "-z"),
        cwd=path,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if output.returncode != 0:
        message = output.stderr.decode("utf-8", errors="replace").strip()
        raise GitError(message or "unable to enumerate repository files")
    names = {item for item in output.stdout.decode("utf-8", errors="strict").split("\0") if item}
    ignore = path / ".repopilotignore"
    spec = (
        GitIgnoreSpec.from_lines(ignore.read_text(encoding="utf-8").splitlines())
        if ignore.is_file() and not ignore.is_symlink()
        else None
    )
    return sorted(item for item in names if not spec or not spec.match_file(item))


def status_summary(path: Path) -> list[dict[str, str]]:
    output = _run(path, "status", "--porcelain=v1")
    return [
        {"status": line[:2], "path": line[3:]} for line in output.splitlines() if len(line) >= 4
    ]


def recent_commits(path: Path, limit: int = 20) -> list[dict[str, str]]:
    safe_limit = min(max(limit, 1), 100)
    output = _run(path, "log", f"-{safe_limit}", "--date=iso-strict", "--format=%H%x09%ad%x09%s")
    return [
        {"commit": parts[0], "date": parts[1], "subject": parts[2]}
        for line in output.splitlines()
        if len(parts := line.split("\t", 2)) == 3
    ]
