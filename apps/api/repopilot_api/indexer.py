from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .git import tracked_and_unignored_files
from .paths import allowed_path, scoped_path
from .security import redact
from .symbols import extract_relationships, extract_symbols

LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".md": "markdown",
    ".json": "json",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
}
IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "coverage",
}
SECRET_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "id_rsa",
    "id_ed25519",
}
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".crt")


@dataclass(frozen=True)
class IndexedFile:
    relative_path: str
    language: str
    text: str
    file_hash: str
    size_bytes: int
    line_count: int


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _is_allowed_path(relative_path: str) -> bool:
    path = Path(relative_path)
    if not allowed_path(relative_path):
        return False
    if any(part in IGNORED_DIRECTORY_NAMES for part in path.parts):
        return False
    if path.name in SECRET_FILE_NAMES or path.name.startswith(".env."):
        return False
    if path.name.lower().endswith(SECRET_SUFFIXES):
        return False
    return path.suffix.lower() in LANGUAGES


def _safe_file(root: Path, relative_path: str) -> Path | None:
    try:
        candidate = scoped_path(root, relative_path)
    except ValueError:
        return None
    if not candidate.is_file() or candidate.is_symlink():
        return None
    return candidate


def _read_file(root: Path, relative_path: str, max_file_bytes: int) -> IndexedFile | None:
    if not _is_allowed_path(relative_path):
        return None
    path = _safe_file(root, relative_path)
    if path is None:
        return None
    size_bytes = path.stat().st_size
    if size_bytes > max_file_bytes:
        return None
    with path.open("rb") as source:
        raw = source.read(max_file_bytes + 1)
    if len(raw) > max_file_bytes or b"\0" in raw:
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if redact(text) != text:
        return None
    return IndexedFile(
        relative_path=relative_path.replace("\\", "/"),
        language=LANGUAGES[path.suffix.lower()],
        text=text,
        file_hash=hashlib.sha256(raw).hexdigest(),
        size_bytes=size_bytes,
        line_count=len(text.splitlines()),
    )


class IndexCancelled(ValueError):
    pass


def load_files(root: Path, max_file_bytes: int, cancelled=lambda: False) -> list[IndexedFile]:
    files: list[IndexedFile] = []
    for relative_path in tracked_and_unignored_files(root):
        if cancelled():
            raise IndexCancelled("indexing cancelled")
        item = _read_file(root, relative_path, max_file_bytes)
        if item is not None:
            files.append(item)
            if len(files) > 10_000 or sum(f.size_bytes for f in files) > 100_000_000:
                raise ValueError("index exceeds 10,000 files or 100 MB budget")
    return files


def index_repository(
    connection: sqlite3.Connection,
    repository_id: str,
    root: Path,
    current_commit: str,
    max_file_bytes: int,
    cancelled=lambda: False,
) -> int:
    now = utc_now()
    connection.execute(
        "UPDATE repositories SET index_status = 'indexing', index_error = NULL, updated_at = ? WHERE id = ?",
        (now, repository_id),
    )
    connection.commit()
    try:
        indexed_files = load_files(root, max_file_bytes, cancelled)
        indexed_by_path = {item.relative_path: item for item in indexed_files}
        existing = {
            row["path"]: row
            for row in connection.execute(
                "SELECT id, path, file_hash FROM files WHERE repository_id = ?", (repository_id,)
            )
        }

        for path, row in existing.items():
            if path not in indexed_by_path:
                connection.execute("DELETE FROM file_search WHERE rowid = ?", (row["id"],))
                connection.execute("DELETE FROM files WHERE id = ?", (row["id"],))

        for item in indexed_files:
            if cancelled():
                raise IndexCancelled("indexing cancelled")
            previous = existing.get(item.relative_path)
            if (
                previous
                and previous["file_hash"] == item.file_hash
                and connection.execute(
                    "SELECT index_version FROM repositories WHERE id = ?", (repository_id,)
                ).fetchone()[0]
                == 3
            ):
                continue
            if previous:
                file_id = previous["id"]
                connection.execute("DELETE FROM symbols WHERE file_id = ?", (file_id,))
                connection.execute("DELETE FROM relationships WHERE file_id = ?", (file_id,))
                connection.execute(
                    """UPDATE files SET file_hash = ?, language = ?, size_bytes = ?,
                       line_count = ?, indexed_at = ? WHERE id = ?""",
                    (
                        item.file_hash,
                        item.language,
                        item.size_bytes,
                        item.line_count,
                        now,
                        file_id,
                    ),
                )
                connection.execute("DELETE FROM file_search WHERE rowid = ?", (file_id,))
            else:
                cursor = connection.execute(
                    """INSERT INTO files
                       (repository_id, path, file_hash, language, size_bytes, line_count, indexed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        repository_id,
                        item.relative_path,
                        item.file_hash,
                        item.language,
                        item.size_bytes,
                        item.line_count,
                        now,
                    ),
                )
                file_id = cursor.lastrowid
            for relation in extract_relationships(item.text, item.language, item.relative_path):
                connection.execute(
                    "INSERT INTO relationships VALUES (?, ?, ?, ?, ?)",
                    (
                        file_id,
                        relation["kind"],
                        relation["source"],
                        relation["target"],
                        relation["line"],
                    ),
                )
            for symbol in extract_symbols(item.text, item.language, item.relative_path):
                connection.execute(
                    """INSERT OR REPLACE INTO symbols
                       (repository_id, file_id, name, kind, start_line, end_line, signature)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        repository_id,
                        file_id,
                        symbol["name"],
                        symbol["kind"],
                        symbol["start_line"],
                        symbol["end_line"],
                        symbol["signature"],
                    ),
                )
            connection.execute(
                "INSERT INTO file_search(rowid, repository_id, path, content) VALUES (?, ?, ?, ?)",
                (file_id, repository_id, item.relative_path, item.text),
            )

        count = connection.execute(
            "SELECT COUNT(*) FROM files WHERE repository_id = ?", (repository_id,)
        ).fetchone()[0]
        connection.execute(
            """UPDATE repositories SET indexed_commit = ?, index_version = 3, index_status = 'ready',
               indexed_file_count = ?, index_error = NULL, updated_at = ? WHERE id = ?""",
            (current_commit, count, now, repository_id),
        )
        connection.commit()
        return int(count)
    except Exception as exc:
        connection.rollback()
        connection.execute(
            "UPDATE repositories SET index_status = ?, index_error = ?, updated_at = ? WHERE id = ?",
            (
                "cancelled" if isinstance(exc, IndexCancelled) else "failed",
                redact(str(exc))[:500],
                utc_now(),
                repository_id,
            ),
        )
        connection.commit()
        raise


def _fts_query(query: str) -> str:
    terms = re.findall(r"[\w./:-]+", query, flags=re.UNICODE)
    if not terms:
        raise ValueError("search query must contain at least one searchable term")
    stopwords = {
        "where",
        "what",
        "how",
        "is",
        "the",
        "a",
        "an",
        "in",
        "of",
        "to",
        "does",
        "this",
        "implemented",
        "explain",
        "find",
    }
    terms = [t for t in terms if t.lower() not in stopwords] or terms
    return " OR ".join('"' + term.replace('"', '""') + '"' for term in terms[:24])


def _evidence_lines(content: str, query: str) -> tuple[int, int, str]:
    lines = content.splitlines()
    terms = [term.lower() for term in re.findall(r"[\w./:-]+", query, flags=re.UNICODE)]
    matching_line = next(
        (index for index, line in enumerate(lines) if any(term in line.lower() for term in terms)),
        0,
    )
    start = max(0, matching_line - 2)
    end = min(len(lines), matching_line + 3)
    excerpt = "\n".join(f"{index + 1}: {lines[index]}" for index in range(start, end))
    return start + 1, max(start + 1, end), excerpt


def search_repository(
    connection: sqlite3.Connection, repository_id: str, query: str, limit: int = 20
) -> list[dict[str, str | int]]:
    match_query = _fts_query(query)
    safe_limit = min(max(limit, 1), 50)
    symbol_rows = connection.execute(
        """SELECT s.name, s.kind, s.start_line, s.end_line, s.signature, f.path
           FROM symbols s JOIN files f ON f.id = s.file_id
           WHERE s.repository_id = ? AND s.name LIKE ? LIMIT ?""",
        (repository_id, f"%{query.strip()}%", safe_limit),
    ).fetchall()
    rows = connection.execute(
        """SELECT rowid, path, content FROM file_search
           WHERE repository_id = ? AND file_search MATCH ? ORDER BY rank LIMIT ?""",
        (repository_id, match_query, safe_limit),
    ).fetchall()
    results = [
        {
            "path": row["path"],
            "line_start": row["start_line"],
            "line_end": row["end_line"],
            "symbol_name": row["name"],
            "symbol_kind": row["kind"],
            "excerpt": row["signature"] or "",
            "retrieval_method": "symbol",
        }
        for row in symbol_rows
    ]
    for row in rows:
        start, end, excerpt = _evidence_lines(row["content"], query)
        results.append(
            {
                "path": row["path"],
                "line_start": start,
                "line_end": end,
                "excerpt": excerpt,
                "retrieval_method": "fts5",
            }
        )
    unique: dict[tuple[str, int], dict[str, str | int]] = {}
    for result in results:
        unique.setdefault((str(result["path"]), int(result["line_start"])), result)
    repository = connection.execute(
        "SELECT * FROM repositories WHERE id = ?", (repository_id,)
    ).fetchone()
    verified = []
    for result in unique.values():
        path = str(result["path"])
        file = connection.execute(
            "SELECT file_hash FROM files WHERE repository_id = ? AND path = ?",
            (repository_id, path),
        ).fetchone()
        current = _read_file(Path(repository["local_path"]), path, 2_000_000)
        if current is None or current.file_hash != file[0]:
            continue
        start = int(result["line_start"])
        end = min(int(result["line_end"]), start + 79)
        lines = current.text.splitlines()
        excerpt = "\n".join(f"{i + 1}: {lines[i]}" for i in range(start - 1, min(end, len(lines))))
        result.update(
            repository_id=repository_id,
            commit_hash=repository["indexed_commit"] or "",
            file_hash=current.file_hash,
            line_end=end,
            excerpt=excerpt,
            excerpt_hash=hashlib.sha256(excerpt.encode()).hexdigest(),
            snapshot_kind="working_tree",
        )
        verified.append(result)
    return verified[:safe_limit]
