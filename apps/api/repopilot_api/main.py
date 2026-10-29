from __future__ import annotations

import os
import secrets
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import Settings
from .database import connect
from .git import GitError, recent_commits, repository_metadata, status_summary
from .indexer import index_repository, utc_now
from .instance import instance_lock
from .model import ModelGateway
from .security import redact
from .semantic import LocalEmbeddings, hybrid_search, index_embeddings
from .tasks import TaskService, task_router
from .tools import list_repository_files, read_file_range


class RepositoryCreate(BaseModel):
    local_path: str = Field(min_length=1, max_length=2000)
    display_name: str | None = Field(default=None, max_length=120)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=20, ge=1, le=50)


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(application):
        with instance_lock(config.database_path):
            service.recover()
            try:
                yield
            finally:
                for stop in list(index_jobs.values()):
                    stop.set()
                service.shutdown()

    app = FastAPI(
        title="RepoPilot", version="0.3.0", docs_url=None, redoc_url=None, lifespan=lifespan
    )
    token = config.session_token or secrets.token_urlsafe(32)
    app.state.session_token = token
    app.state.settings = config
    model = ModelGateway(
        config.model_provider,
        config.model_base_url,
        config.model_api_key,
        config.primary_model,
        config.fallback_model,
    )
    app.state.model = model
    service = TaskService(config, model)
    app.state.tasks = service
    index_jobs = {}
    index_lock = threading.Lock()

    @app.middleware("http")
    async def authorize(request, call_next):
        path = request.scope["path"]
        if path.startswith("/api/"):
            path = path[4:]
            request.scope["path"] = path
        protected = path.startswith(("/repositories", "/tasks", "/settings", "/model", "/openapi"))
        origin = request.headers.get("origin")
        host = request.headers.get("host", "")
        allowed_origins = {f"http://{host}", "http://127.0.0.1:5173", "http://localhost:5173"}
        if protected:
            if origin and origin not in allowed_origins:
                return JSONResponse({"detail": "origin not permitted"}, 403)
            supplied_token = request.headers.get("X-RepoPilot-Token") or request.cookies.get(
                "repopilot_session"
            )
            if not supplied_token or not secrets.compare_digest(supplied_token, token):
                return JSONResponse({"detail": "invalid local session token"}, 401)
        if (
            request.headers.get("content-length", "0").isdigit()
            and int(request.headers.get("content-length", "0")) > 3_000_000
        ):
            return JSONResponse({"detail": "request exceeds 3 MB limit"}, 413)
        response = await call_next(request)
        if protected:
            response.set_cookie(
                "repopilot_session",
                token,
                httponly=True,
                samesite="strict",
                secure=False,
                path="/",
            )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ValueError)
    @app.exception_handler(GitError)
    async def invalid_request(request, exc):
        return JSONResponse({"detail": redact(str(exc))[:2000]}, 400)

    @app.get("/health")
    def health():
        return {"status": "ok", "model": model.health()}

    @app.get("/settings")
    def settings_view():
        return {
            "provider": model.provider,
            "model": model.primary_model,
            "base_url": model.base_url,
            "remote": model.provider == "openai_compatible",
            "timeout_seconds": config.task_timeout_seconds,
            "sandbox": config.sandbox_mode,
            "api_key_configured": bool(config.model_api_key),
            "instructions": "Edit .env and restart to change provider, model, sandbox images, or budgets.",
        }

    @app.get("/model/health")
    def model_health():
        return model.probe()

    def db():
        return connect(config.database_path)

    def repo(connection, repository_id):
        row = connection.execute(
            "SELECT * FROM repositories WHERE id = ?", (repository_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(404, "repository not found")
        result = dict(row)
        result["dirty"] = bool(result["dirty"])
        return result

    @app.get("/repositories")
    def repositories():
        with db() as connection:
            return [
                repo(connection, row[0])
                for row in connection.execute(
                    "SELECT id FROM repositories ORDER BY updated_at DESC"
                )
            ]

    @app.post("/repositories", status_code=201)
    def register(payload: RepositoryCreate):
        path = Path(payload.local_path).expanduser().resolve()
        if not path.is_dir():
            raise HTTPException(400, "local_path must be an existing directory")
        metadata = repository_metadata(path)
        with db() as connection:
            row = connection.execute(
                "SELECT id FROM repositories WHERE local_path = ?", (str(path),)
            ).fetchone()
            repository_id = row[0] if row else str(uuid4())
            connection.execute(
                """INSERT INTO repositories(id, display_name, local_path, branch, current_commit, dirty, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(local_path) DO UPDATE SET
                branch=excluded.branch, current_commit=excluded.current_commit, dirty=excluded.dirty, updated_at=excluded.updated_at""",
                (
                    repository_id,
                    payload.display_name or path.name,
                    str(path),
                    metadata["branch"],
                    metadata["current_commit"],
                    int(metadata["dirty"]),
                    utc_now(),
                    utc_now(),
                ),
            )
            return repo(connection, repository_id)

    @app.get("/repositories/{repository_id}")
    def repository(repository_id: str):
        with db() as connection:
            return repo(connection, repository_id)

    @app.post("/repositories/{repository_id}/index")
    def index(repository_id: str, background: bool = False):
        if background:
            repository(repository_id)
            with index_lock:
                if repository_id in index_jobs:
                    raise HTTPException(409, "repository is already indexing")
                if not service.slots.acquire(blocking=False):
                    raise HTTPException(429, "worker budget exhausted")
                stop = threading.Event()
                index_jobs[repository_id] = stop
            with db() as connection:
                connection.execute(
                    "UPDATE repositories SET index_status='indexing' WHERE id=?", (repository_id,)
                )

            def work():
                try:
                    with db() as connection:
                        item = repo(connection, repository_id)
                        metadata = repository_metadata(Path(item["local_path"]))
                        index_repository(
                            connection,
                            repository_id,
                            Path(item["local_path"]),
                            metadata["current_commit"],
                            config.max_file_bytes,
                            stop.is_set,
                        )
                except (OSError, ValueError, RuntimeError) as exc:
                    with db() as connection:
                        connection.execute(
                            "UPDATE repositories SET index_status=?, index_error=? WHERE id=?",
                            (
                                "cancelled" if stop.is_set() else "failed",
                                redact(str(exc)),
                                repository_id,
                            ),
                        )
                finally:
                    with index_lock:
                        index_jobs.pop(repository_id, None)
                    service.slots.release()

            threading.Thread(target=work, daemon=True).start()
            return {"repository_id": repository_id, "status": "indexing"}
        with db() as connection:
            item = repo(connection, repository_id)
            metadata = repository_metadata(Path(item["local_path"]))
            count = index_repository(
                connection,
                repository_id,
                Path(item["local_path"]),
                metadata["current_commit"],
                config.max_file_bytes,
            )
            connection.execute(
                "UPDATE repositories SET branch = ?, current_commit = ?, dirty = ? WHERE id = ?",
                (
                    metadata["branch"],
                    metadata["current_commit"],
                    int(metadata["dirty"]),
                    repository_id,
                ),
            )
        return {"repository_id": repository_id, "status": "ready", "indexed_file_count": count}

    @app.post("/repositories/{repository_id}/index/cancel")
    def cancel_index(repository_id: str):
        with index_lock:
            if repository_id not in index_jobs:
                raise HTTPException(409, "no running index job")
            index_jobs[repository_id].set()
        return {"status": "cancellation_requested"}

    @app.get("/repositories/{repository_id}/index-status")
    def index_status(repository_id: str):
        with db() as connection:
            item = repo(connection, repository_id)
            return {
                key: item[key]
                for key in (
                    "id",
                    "index_status",
                    "indexed_file_count",
                    "index_error",
                    "indexed_commit",
                )
            }

    @app.post("/repositories/{repository_id}/search")
    def search(repository_id: str, payload: SearchRequest):
        with db() as connection:
            item = repo(connection, repository_id)
            if item["index_status"] != "ready":
                raise HTTPException(409, "repository must be indexed before search")
            adapter = (
                LocalEmbeddings(config.embedding_model, config.embedding_endpoint)
                if config.embedding_model
                else None
            )
            evidence = hybrid_search(
                connection, repository_id, payload.query, adapter, payload.limit
            )
        return {
            "repository_id": repository_id,
            "commit_hash": item["indexed_commit"],
            "evidence": evidence,
        }

    @app.post("/repositories/{repository_id}/embeddings")
    def embeddings(repository_id: str):
        adapter = LocalEmbeddings(config.embedding_model, config.embedding_endpoint)
        with db() as connection:
            repo(connection, repository_id)
            return {
                "chunks_updated": index_embeddings(connection, repository_id, adapter),
                "model": adapter.model,
            }

    @app.get("/repositories/{repository_id}/symbols")
    def symbols(repository_id: str, query: str = ""):
        with db() as connection:
            repo(connection, repository_id)
            return [
                dict(row)
                for row in connection.execute(
                    """SELECT s.name, s.kind, s.start_line, s.end_line, s.signature, f.path
                FROM symbols s JOIN files f ON f.id = s.file_id WHERE s.repository_id = ? AND s.name LIKE ? ORDER BY f.path, s.start_line LIMIT 100""",
                    (repository_id, "%" + query + "%"),
                )
            ]

    @app.get("/repositories/{repository_id}/files")
    def files(repository_id: str):
        return {"files": list_repository_files(Path(repository(repository_id)["local_path"]))}

    @app.get("/repositories/{repository_id}/file")
    def file(repository_id: str, path: str, start_line: int = 1, end_line: int = 200):
        return read_file_range(
            Path(repository(repository_id)["local_path"]), path, start_line, end_line
        )

    @app.get("/repositories/{repository_id}/git-status")
    def git_status(repository_id: str):
        root = Path(repository(repository_id)["local_path"])
        return {**repository_metadata(root), "changes": status_summary(root)}

    @app.get("/repositories/{repository_id}/commits")
    def commits(repository_id: str):
        return {"commits": recent_commits(Path(repository(repository_id)["local_path"]))}

    @app.get("/repositories/{repository_id}/tests")
    def tests(repository_id: str):
        return [{"path": p} for p in files(repository_id)["files"] if "test" in p or "spec" in p]

    @app.get("/repositories/{repository_id}/references")
    def references(repository_id: str, symbol: str):
        evidence = search(repository_id, SearchRequest(query=symbol))["evidence"]
        return [
            {
                "path": e["path"],
                "line": e["line_start"],
                "text": e["excerpt"],
                "kind": "lexical_candidate",
            }
            for e in evidence
        ]

    @app.get("/repositories/{repository_id}/structure")
    def structure(repository_id: str):
        with db() as connection:
            repo(connection, repository_id)
            languages = [
                dict(r)
                for r in connection.execute(
                    "SELECT language, COUNT(*) AS files FROM files WHERE repository_id = ? GROUP BY language",
                    (repository_id,),
                )
            ]
            relations = [
                dict(r)
                for r in connection.execute(
                    "SELECT f.path, r.kind, r.source, r.target, r.line FROM relationships r JOIN files f ON f.id=r.file_id WHERE f.repository_id = ? LIMIT 500",
                    (repository_id,),
                )
            ]
            manifests = [
                dict(r)
                for r in connection.execute(
                    "SELECT path FROM files WHERE repository_id = ? AND (path LIKE '%package.json' OR path LIKE '%pyproject.toml')",
                    (repository_id,),
                )
            ]
            return {
                "languages": languages,
                "manifests": manifests,
                "relationships": relations,
                "coverage": "Syntactic Python/JS/TS imports and call candidates; dynamic dispatch is not resolved.",
            }

    app.include_router(task_router(service))
    web = (
        Path(os.environ["REPOPILOT_WEB_DIR"])
        if os.getenv("REPOPILOT_WEB_DIR")
        else Path(__file__).resolve().parents[3] / "web" / "dist"
    )
    if web.is_dir():
        app.mount("/", StaticFiles(directory=web, html=True), name="web")
    return app


app = create_app()
