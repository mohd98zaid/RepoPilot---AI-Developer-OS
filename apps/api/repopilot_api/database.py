from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS repositories (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    local_path TEXT NOT NULL UNIQUE,
    branch TEXT,
    current_commit TEXT NOT NULL,
    dirty INTEGER NOT NULL DEFAULT 0,
    index_status TEXT NOT NULL DEFAULT 'not_indexed',
    indexed_file_count INTEGER NOT NULL DEFAULT 0,
    index_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id TEXT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    language TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    line_count INTEGER NOT NULL,
    indexed_at TEXT NOT NULL,
    UNIQUE(repository_id, path)
);

CREATE VIRTUAL TABLE IF NOT EXISTS file_search USING fts5(
    repository_id UNINDEXED,
    path UNINDEXED,
    content,
    tokenize = 'unicode61'
);

CREATE INDEX IF NOT EXISTS files_repository_idx ON files(repository_id);

CREATE TABLE IF NOT EXISTS symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id TEXT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    signature TEXT,
    UNIQUE(repository_id, file_id, name, start_line)
);

CREATE INDEX IF NOT EXISTS symbols_repository_name_idx ON symbols(repository_id, name);
CREATE TABLE IF NOT EXISTS relationships (
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    kind TEXT NOT NULL, source TEXT NOT NULL, target TEXT NOT NULL, line INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    repository_id TEXT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    task_type TEXT NOT NULL,
    request TEXT NOT NULL,
    status TEXT NOT NULL,
    answer TEXT,
    base_commit TEXT NOT NULL,
    worktree_path TEXT,
    diff_text TEXT,
    diff_hash TEXT,
    approval_status TEXT NOT NULL DEFAULT 'not_required',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    error TEXT
);

CREATE TABLE IF NOT EXISTS task_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(task_id, sequence)
);

CREATE TABLE IF NOT EXISTS test_runs (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    command TEXT NOT NULL,
    exit_code INTEGER,
    status TEXT NOT NULL,
    output TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    action_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    decided_at TEXT,
    UNIQUE(task_id, action_hash)
);
"""


MIGRATIONS = {
    "repositories": {"indexed_commit": "TEXT", "index_version": "INTEGER NOT NULL DEFAULT 0"},
    "tasks": {
        "plan": "TEXT",
        "hypotheses": "TEXT",
        "verification": "TEXT",
        "evidence": "TEXT",
        "checkpoint": "TEXT",
        "model_id": "TEXT",
        "repair_count": "INTEGER NOT NULL DEFAULT 0",
    },
}


class Connection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30, factory=Connection)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.executescript(SCHEMA)
    for table, columns in MIGRATIONS.items():
        existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        for column, column_type in columns.items():
            if column not in existing:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
    connection.commit()
    return connection
