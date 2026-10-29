from __future__ import annotations

import hashlib
from pathlib import Path

from .git import tracked_and_unignored_files
from .paths import scoped_path
from .security import redact


class ToolError(ValueError):
    """A requested read-only tool operation is not permitted."""


def repository_path(root: Path, relative_path: str) -> Path:
    try:
        return scoped_path(root, relative_path)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


def list_repository_files(root: Path, max_files: int = 5000) -> list[str]:
    files: list[str] = []
    for name in tracked_and_unignored_files(root):
        if len(files) >= max_files:
            break
        try:
            candidate = repository_path(root, name)
        except ToolError:
            continue
        if candidate.is_file():
            files.append(name.replace("\\", "/"))
    return sorted(files)


def read_file_range(
    root: Path, relative_path: str, start_line: int = 1, end_line: int = 200
) -> dict[str, object]:
    if start_line < 1 or end_line < start_line or end_line - start_line >= 500:
        raise ToolError("line range must be 1..500 lines")
    path = repository_path(root, relative_path)
    if not path.is_file():
        raise ToolError("file not found")
    if relative_path.replace("\\", "/") not in list_repository_files(root):
        raise ToolError("file is ignored or outside the supported file list")
    with path.open("rb") as source:
        raw = source.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ToolError("file is too large")
    if b"\0" in raw:
        raise ToolError("binary files are not readable")
    lines = redact(raw.decode("utf-8", errors="replace")).splitlines()
    if start_line > len(lines):
        raise ToolError("start line exceeds file length")
    selected = lines[start_line - 1 : end_line]
    return {
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "line_start": start_line,
        "line_end": min(end_line, len(lines)),
        "content": "\n".join(
            f"{line_number}: {line}" for line_number, line in enumerate(selected, start_line)
        ),
        "content_hash": hashlib.sha256(raw).hexdigest(),
    }
