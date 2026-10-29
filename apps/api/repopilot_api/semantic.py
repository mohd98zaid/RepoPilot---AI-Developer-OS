"""Optional local embedding retrieval; never downloads models or calls hosted endpoints."""

from __future__ import annotations

import hashlib
import json
import math
from urllib.parse import urlparse

import httpx


class LocalEmbeddings:
    def __init__(self, model: str, endpoint: str = "http://127.0.0.1:11434"):
        parsed = urlparse(endpoint)
        if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.scheme not in {
            "http",
            "https",
        }:
            raise ValueError("embeddings must use a local loopback runtime")
        if not model:
            raise ValueError("configure REPOPILOT_EMBEDDING_MODEL first")
        self.model, self.endpoint = model, endpoint.rstrip("/")

    def embed(self, text):
        response = httpx.post(
            self.endpoint + "/api/embed",
            json={"model": self.model, "input": text},
            timeout=60,
            trust_env=False,
        )
        response.raise_for_status()
        values = response.json()["embeddings"][0]
        if (
            not values
            or len(values) > 8192
            or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in values)
        ):
            raise ValueError("invalid embedding response")
        norm = math.sqrt(sum(v * v for v in values))
        if not norm:
            raise ValueError("zero-length embedding")
        return [v / norm for v in values]


def schema(db):
    db.execute("""CREATE TABLE IF NOT EXISTS embeddings (
        repository_id TEXT NOT NULL, path TEXT NOT NULL, file_hash TEXT NOT NULL,
        model TEXT NOT NULL, start_line INTEGER NOT NULL, end_line INTEGER NOT NULL,
        excerpt TEXT NOT NULL, vector TEXT NOT NULL,
        PRIMARY KEY(repository_id, path, model, start_line))""")


def index_embeddings(db, repository_id, adapter):
    schema(db)
    rows = db.execute(
        "SELECT f.path, f.file_hash, s.content FROM files f JOIN file_search s ON s.rowid = f.id WHERE f.repository_id = ?",
        (repository_id,),
    ).fetchall()
    current_paths = {r["path"] for r in rows}
    for row in db.execute(
        "SELECT DISTINCT path FROM embeddings WHERE repository_id = ?", (repository_id,)
    ).fetchall():
        if row[0] not in current_paths:
            db.execute(
                "DELETE FROM embeddings WHERE repository_id = ? AND path = ?",
                (repository_id, row[0]),
            )
    chunks = 0
    for row in rows:
        old = db.execute(
            "SELECT file_hash FROM embeddings WHERE repository_id = ? AND path = ? AND model = ? LIMIT 1",
            (repository_id, row["path"], adapter.model),
        ).fetchone()
        if old and old[0] == row["file_hash"]:
            continue
        db.execute(
            "DELETE FROM embeddings WHERE repository_id = ? AND path = ?",
            (repository_id, row["path"]),
        )
        lines = row["content"].splitlines()
        for start in range(0, len(lines), 60):
            end = min(start + 60, len(lines))
            excerpt = "\n".join(f"{i + 1}: {lines[i]}" for i in range(start, end))[:12000]
            vector = adapter.embed(row["path"] + "\n" + excerpt)
            db.execute(
                "INSERT INTO embeddings VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    repository_id,
                    row["path"],
                    row["file_hash"],
                    adapter.model,
                    start + 1,
                    end,
                    excerpt,
                    json.dumps(vector),
                ),
            )
            chunks += 1
            if chunks > 5000:
                raise ValueError("embedding indexing budget exceeded")
    return chunks


def semantic_search(db, repository_id, query, adapter, limit=12):
    from pathlib import Path

    from .indexer import _read_file

    schema(db)
    vector = adapter.embed(query)
    repo = db.execute("SELECT * FROM repositories WHERE id = ?", (repository_id,)).fetchone()
    ranked = []
    for row in db.execute(
        "SELECT * FROM embeddings WHERE repository_id = ? AND model = ?",
        (repository_id, adapter.model),
    ):
        stored = json.loads(row["vector"])
        if len(stored) != len(vector):
            raise ValueError("embedding dimension changed; re-index with a versioned model name")
        score = sum(a * b for a, b in zip(stored, vector, strict=True))
        ranked.append((score, dict(row)))
    evidence = []
    for score, row in sorted(ranked, key=lambda x: x[0], reverse=True):
        current = _read_file(Path(repo["local_path"]), row["path"], 2_000_000)
        if not current or current.file_hash != row["file_hash"]:
            continue
        evidence.append(
            {
                "repository_id": repository_id,
                "path": row["path"],
                "line_start": row["start_line"],
                "line_end": row["end_line"],
                "excerpt": row["excerpt"],
                "file_hash": row["file_hash"],
                "commit_hash": repo["indexed_commit"],
                "excerpt_hash": hashlib.sha256(row["excerpt"].encode()).hexdigest(),
                "retrieval_method": "local_embedding",
                "score": score,
            }
        )
        if len(evidence) >= limit:
            break
    return evidence


def hybrid_search(db, repository_id, query, adapter=None, limit=12):
    from .indexer import search_repository

    lexical = search_repository(db, repository_id, query, limit)
    if not adapter:
        return lexical
    semantic = semantic_search(db, repository_id, query, adapter, limit)
    scores, items = {}, {}
    for results in (lexical, semantic):
        for rank, result in enumerate(results, 1):
            key = (result["path"], result["line_start"])
            items.setdefault(key, result)
            scores[key] = scores.get(key, 0) + 1 / (60 + rank)
    return [items[key] for key in sorted(scores, key=scores.get, reverse=True)[:limit]]
