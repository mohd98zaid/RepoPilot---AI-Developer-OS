from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import subprocess
import threading
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Literal
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .database import connect
from .git import git_command, repository_metadata
from .indexer import _read_file, utc_now
from .model import ModelError
from .runner import run_approved_test
from .security import redact
from .semantic import LocalEmbeddings, hybrid_search
from .workflow import run_investigation
from .worktree import Change, apply_patch, create_worktree, diff, remove_worktree, write_changes


class ChangeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=100000)


class PatchOutput(BaseModel):
    changes: list[ChangeInput] = Field(min_length=1, max_length=20)


class TaskInput(BaseModel):
    repository_id: str
    task_type: Literal["explain", "investigate", "patch"] = "investigate"
    request: str = Field(min_length=1, max_length=10000)
    changes: list[ChangeInput] = Field(default_factory=list, max_length=20)
    background: bool = False
    allow_remote: bool = False


class ApprovalInput(BaseModel):
    action_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: Literal["approved", "rejected"]


class ResumeInput(BaseModel):
    answer: str = Field(min_length=1, max_length=10000)
    allow_remote: bool = False


class TestInput(BaseModel):
    command: str
    compare_baseline: bool = True


class RepairInput(BaseModel):
    allow_remote: bool = False


class TaskService:
    def __init__(self, settings, model):
        self.settings, self.model = settings, model
        self.locks: dict[str, threading.RLock] = {}
        self.cancelled: dict[str, threading.Event] = {}
        self.slots = threading.BoundedSemaphore(2)
        self.workers: list[threading.Thread] = []
        with self.db():
            pass

    def recover(self):
        with self.db() as db:
            db.execute(
                "UPDATE tasks SET status = 'interrupted', error = 'Application stopped during execution' WHERE status IN ('running', 'testing')"
            )
            db.execute(
                "UPDATE repositories SET index_status='failed', index_error='Indexing interrupted; re-index' WHERE index_status='indexing'"
            )

    def start(self, task_id, payload, resume=None):
        thread = threading.Thread(target=self.execute, args=(task_id, payload, resume), daemon=True)
        self.workers = [worker for worker in self.workers if worker.is_alive()]
        self.workers.append(thread)
        thread.start()

    def shutdown(self):
        for stop in self.cancelled.values():
            stop.set()
        for worker in self.workers:
            worker.join(timeout=5)

    def db(self):
        return connect(self.settings.database_path)

    def get(self, task_id):
        with self.db() as db:
            row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(404, "task not found")
        result = dict(row)
        for key in ("plan", "hypotheses", "verification", "evidence", "checkpoint"):
            result[key] = json.loads(result[key]) if result.get(key) else None
        return result

    def save(self, task_id, **fields):
        fields["updated_at"] = utc_now()
        values = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in fields.values()]
        with self.db() as db:
            db.execute(
                "UPDATE tasks SET " + ", ".join(f"{key} = ?" for key in fields) + " WHERE id = ?",
                [*values, task_id],
            )

    def event(self, task_id, kind, payload):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            seq = db.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM task_events WHERE task_id = ?",
                (task_id,),
            ).fetchone()[0]
            db.execute(
                "INSERT INTO task_events(task_id, sequence, event_type, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                (task_id, seq, kind, json.dumps(payload), utc_now()),
            )

    def repository(self, repository_id):
        with self.db() as db:
            row = db.execute("SELECT * FROM repositories WHERE id = ?", (repository_id,)).fetchone()
        if not row:
            raise HTTPException(404, "repository not found")
        return dict(row)

    def consent(self, allowed):
        if self.model.provider == "openai_compatible" and not allowed:
            raise HTTPException(
                409,
                "Remote inference sends the request and retrieved excerpts to the configured provider. Explicit consent is required.",
            )

    def submit(self, payload):
        repo = self.repository(payload.repository_id)
        if repo["index_status"] != "ready":
            raise HTTPException(409, "index repository first")
        if not payload.changes:
            self.consent(payload.allow_remote)
        root = Path(repo["local_path"])
        metadata = repository_metadata(root)
        if payload.task_type == "patch" and metadata["dirty"]:
            raise HTTPException(
                409, "Patch generation requires a clean base; commit or stash your work first"
            )
        if not self.slots.acquire(blocking=False):
            raise HTTPException(429, "Two tasks are already running")
        task_id = str(uuid4())
        self.cancelled[task_id] = threading.Event()
        self.locks[task_id] = threading.RLock()
        with self.db() as db:
            db.execute(
                """INSERT INTO tasks(id, repository_id, task_type, request, status, base_commit, created_at, updated_at, model_id)
                          VALUES (?, ?, ?, ?, 'running', ?, ?, ?, ?)""",
                (
                    task_id,
                    payload.repository_id,
                    payload.task_type,
                    redact(payload.request),
                    metadata["current_commit"],
                    utc_now(),
                    utc_now(),
                    self.model.primary_model or self.model.provider,
                ),
            )
        if payload.background:
            self.start(task_id, payload)
        else:
            self.execute(task_id, payload)
        return self.get(task_id)

    def execute(self, task_id, payload, resume=None):
        worktree = None
        repo = self.repository(payload.repository_id)
        root = Path(repo["local_path"])
        cancelled = self.cancelled[task_id].is_set
        last_progress = [0]

        def model_text(text):
            if len(text) - last_progress[0] >= 256:
                self.event(task_id, "model_progress", {"characters_received": len(text)})
                last_progress[0] = len(text)

        model = replace(
            self.model,
            cancelled=cancelled,
            on_text=model_text,
            deadline=time.monotonic() + self.settings.task_timeout_seconds,
        )
        try:
            self.event(task_id, "task_started", {"task_type": payload.task_type})

            def retrieve(query):
                with self.db() as db:
                    adapter = (
                        LocalEmbeddings(
                            self.settings.embedding_model, self.settings.embedding_endpoint
                        )
                        if self.settings.embedding_model
                        else None
                    )
                    return hybrid_search(db, payload.repository_id, query, adapter, 12)

            def fresh(evidence):
                for item in evidence:
                    current = _read_file(root, item["path"], self.settings.max_file_bytes)
                    if not current or current.file_hash != item["file_hash"]:
                        return False
                return True

            def progress(node, state):
                public = {
                    k: v
                    for k, v in state.items()
                    if k in {"plan", "evidence", "hypotheses", "answer", "verification"}
                }
                if public:
                    self.save(task_id, **public)
                self.event(
                    task_id,
                    node,
                    {"step_count": state.get("step_count"), "status": state.get("status")},
                )

            if payload.task_type != "patch":
                result = run_investigation(
                    retrieve,
                    model,
                    redact(payload.request),
                    checkpoint_path=self.settings.database_path.parent / "checkpoints.sqlite3",
                    task_id=task_id,
                    resume=resume,
                    cancelled=cancelled,
                    timeout=self.settings.task_timeout_seconds,
                    on_event=progress,
                    verifier=fresh,
                )
                if cancelled():
                    raise ValueError("task cancelled")
                self.save(
                    task_id,
                    status=result["status"],
                    answer=result.get("answer"),
                    checkpoint={k: v for k, v in result.items() if k != "__interrupt__"},
                    evidence=result.get("evidence", []),
                    plan=result.get("plan", []),
                    hypotheses=result.get("hypotheses", []),
                    verification=result.get("verification", {}),
                )
            else:
                evidence = retrieve(payload.request)
                changes = payload.changes
                if not changes:
                    if model.provider == "mock":
                        raise ModelError(
                            "Mock mode cannot generate code. Configure a real model or provide manual changes."
                        )
                    prompt = (
                        "Propose a minimal patch as JSON matching "
                        + json.dumps(PatchOutput.model_json_schema())
                        + ". Each content is the complete new UTF-8 file, not a diff. Only use supplied context. Request: "
                        + payload.request
                    )
                    changes = PatchOutput.model_validate(model.structured(prompt, evidence)).changes
                if cancelled() or not fresh(evidence):
                    raise ValueError("task cancelled or evidence changed")
                worktree = create_worktree(root, self.get(task_id)["base_commit"], task_id)
                write_changes(worktree, [Change(c.path, c.content) for c in changes])
                text, digest = diff(worktree)
                if not text.strip():
                    raise ValueError("proposed changes produced an empty diff")
                if cancelled():
                    raise ValueError("task cancelled")
                self.save(
                    task_id,
                    status="awaiting_approval",
                    worktree_path=str(worktree),
                    diff_text=text,
                    diff_hash=digest,
                    approval_status="pending",
                    evidence=evidence,
                    verification={"tests_run": False, "diff_validated": True},
                )
                self.event(task_id, "approval_required", {"action_hash": digest})
            self.event(task_id, "task_completed", {"status": self.get(task_id)["status"]})
        except (
            ModelError,
            OSError,
            ValueError,
            RuntimeError,
            sqlite3.Error,
            httpx.HTTPError,
            HTTPException,
        ) as exc:
            # Worker boundary: always persist terminal state, and never report success on an exception.
            logging.getLogger(__name__).error("Task %s failed: %s", task_id, redact(str(exc)))
            if worktree:
                try:
                    remove_worktree(root, worktree)
                except (OSError, RuntimeError):
                    self.save(task_id, worktree_path=str(worktree))
            error = redact(str(exc))[:2000]
            self.save(task_id, status="cancelled" if cancelled() else "failed", error=error)
            self.event(task_id, "task_failed", {"error": error})
        finally:
            self.slots.release()

    def approve(self, task_id, payload):
        with self.locks.setdefault(task_id, threading.RLock()):
            # SQLite serializes approvals across processes as well as threads.
            with self.db() as db:
                db.execute("BEGIN IMMEDIATE")
                task = dict(
                    db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone() or {}
                )
                if not task:
                    raise HTTPException(404, "task not found")
                if (
                    task["status"] != "awaiting_approval"
                    or task["approval_status"] != "pending"
                    or task["diff_hash"] != payload.action_hash
                ):
                    raise HTTPException(409, "approval is stale, replayed, or task is busy")
                root = Path(
                    db.execute(
                        "SELECT local_path FROM repositories WHERE id = ?", (task["repository_id"],)
                    ).fetchone()[0]
                )
                worktree = Path(task["worktree_path"])
                if payload.decision == "approved":
                    current = repository_metadata(root)
                    if current["current_commit"] != task["base_commit"] or current["dirty"]:
                        raise HTTPException(409, "source repository changed; no patch applied")
                    text, digest = diff(worktree)
                    if (
                        digest != task["diff_hash"]
                        or hashlib.sha256(task["diff_text"].encode()).hexdigest() != digest
                    ):
                        raise HTTPException(409, "worktree changed since review; no patch applied")
                    apply_patch(root, text)
                db.execute(
                    "INSERT INTO approvals(id, task_id, action_hash, status, decided_at) VALUES (?, ?, ?, ?, ?)",
                    (str(uuid4()), task_id, payload.action_hash, payload.decision, utc_now()),
                )
                db.execute(
                    "UPDATE tasks SET status = ?, approval_status = ?, updated_at = ? WHERE id = ?",
                    (payload.decision, payload.decision, utc_now(), task_id),
                )
            # Persist the decision before cleanup so a cleanup error cannot cause duplicate application.
            try:
                remove_worktree(root, worktree)
                self.save(task_id, worktree_path=None)
            except (OSError, RuntimeError) as exc:
                self.event(task_id, "cleanup_failed", {"error": redact(str(exc))})
            self.event(
                task_id, "approval_" + payload.decision, {"action_hash": payload.action_hash}
            )
            return self.get(task_id)

    def cancel(self, task_id):
        task = self.get(task_id)
        if task["status"] in {"approved", "rejected", "completed", "failed"}:
            raise HTTPException(409, "task is already terminal")
        self.cancelled.setdefault(task_id, threading.Event()).set()
        if task["status"] in {"running", "testing"}:
            self.event(task_id, "cancellation_requested", {})
            return {**task, "cancellation_requested": True}
        with self.locks.setdefault(task_id, threading.RLock()):
            if task["worktree_path"]:
                root = Path(self.repository(task["repository_id"])["local_path"])
                remove_worktree(root, Path(task["worktree_path"]))
            self.save(task_id, status="cancelled", approval_status="rejected", worktree_path=None)
        return self.get(task_id)

    def resume(self, task_id, payload):
        task = self.get(task_id)
        if task["status"] != "awaiting_input":
            raise HTTPException(409, "only a clarification checkpoint can be resumed")
        self.consent(payload.allow_remote)
        if not self.slots.acquire(blocking=False):
            raise HTTPException(429, "task concurrency budget exceeded")
        self.cancelled[task_id] = threading.Event()
        self.save(task_id, status="running")
        request = TaskInput(
            repository_id=task["repository_id"],
            task_type=task["task_type"],
            request=task["request"],
            allow_remote=payload.allow_remote,
        )
        self.start(task_id, request, redact(payload.answer))
        return self.get(task_id)

    def test(self, task_id, payload):
        with self.locks.setdefault(task_id, threading.RLock()):
            task = self.get(task_id)
            if task["status"] != "awaiting_approval" or not task["worktree_path"]:
                raise HTTPException(409, "tests require a pending isolated patch")
            self.save(task_id, status="testing")
            stop = self.cancelled.setdefault(task_id, threading.Event()).is_set
            root = Path(self.repository(task["repository_id"])["local_path"])
            baseline = None

            def run(path, kind):
                result = run_approved_test(
                    path,
                    payload.command,
                    self.settings.task_timeout_seconds,
                    self.settings.max_output_bytes,
                    self.settings.sandbox_mode,
                    self.settings.sandbox_python_image,
                    self.settings.sandbox_node_image,
                    stop,
                )
                with self.db() as db:
                    db.execute(
                        "INSERT INTO test_runs(id, task_id, command, exit_code, status, output, duration_ms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            str(uuid4()),
                            task_id,
                            kind + ": " + result.command,
                            result.exit_code,
                            result.status,
                            result.output,
                            result.duration_ms,
                            utc_now(),
                        ),
                    )
                return asdict(result)

            try:
                base_result = None
                if payload.compare_baseline:
                    baseline = create_worktree(root, task["base_commit"], str(uuid4()))
                    base_result = run(baseline, "baseline")
                patch_result = (
                    run(Path(task["worktree_path"]), "patch")
                    if not stop()
                    else {"status": "cancelled"}
                )
                verification = {
                    "baseline": base_result,
                    "patch": patch_result,
                    "tests_run": True,
                    "regression": bool(
                        base_result
                        and base_result["status"] == "passed"
                        and patch_result["status"] == "failed"
                    ),
                    "diff_hash": task["diff_hash"],
                    "claims_verified": False,
                }
                self.save(task_id, verification=verification)
                self.event(task_id, "tests_finished", {"status": patch_result["status"]})
                return verification
            finally:
                if baseline:
                    remove_worktree(root, baseline)
                self.save(task_id, status="awaiting_approval")
                if stop():
                    self.cancel(task_id)

    def repair(self, task_id, payload):
        self.consent(payload.allow_remote)
        if self.model.provider == "mock":
            raise HTTPException(409, "Repair requires a real model")
        with self.locks.setdefault(task_id, threading.RLock()):
            task = self.get(task_id)
            verification = task["verification"] or {}
            if task["status"] != "awaiting_approval" or not verification.get("regression"):
                raise HTTPException(
                    409, "Repair requires a passing baseline and failing patch test"
                )
            if task["repair_count"] >= 2:
                raise HTTPException(409, "Two-attempt repair budget exhausted")
            worktree = Path(task["worktree_path"])
            paths = (
                subprocess.run(
                    git_command(worktree, "diff", "--name-only", "-z"),
                    cwd=worktree,
                    capture_output=True,
                    check=True,
                    timeout=15,
                )
                .stdout.decode()
                .split("\0")
            )
            context = []
            for path in filter(None, paths):
                item = _read_file(worktree, path, self.settings.max_file_bytes)
                if item:
                    context.append(
                        {
                            "path": path,
                            "line_start": 1,
                            "line_end": item.line_count,
                            "excerpt": item.text,
                        }
                    )
            self.save(task_id, status="running", repair_count=task["repair_count"] + 1)
            stop = self.cancelled.setdefault(task_id, threading.Event()).is_set
            try:
                prompt = (
                    "Repair the regression with minimal changes. Return JSON matching "
                    + json.dumps(PatchOutput.model_json_schema())
                    + ". Test output: "
                    + verification["patch"]["output"][-12000:]
                )
                changes = PatchOutput.model_validate(
                    replace(self.model, cancelled=stop).structured(prompt, context)
                ).changes
                if stop():
                    raise ValueError("repair cancelled")
                write_changes(worktree, [Change(c.path, c.content) for c in changes])
                text, digest = diff(worktree)
                self.save(
                    task_id,
                    diff_text=text,
                    diff_hash=digest,
                    verification={"tests_run": False},
                    status="awaiting_approval",
                )
                self.event(
                    task_id,
                    "patch_repaired",
                    {"action_hash": digest, "attempt": task["repair_count"] + 1},
                )
                self.test(task_id, TestInput(command=verification["patch"]["command"]))
            finally:
                current = self.get(task_id)
                if current["status"] == "running":
                    # Rehash even on a partial write failure; the old approval must never survive edits.
                    text, digest = diff(worktree)
                    self.save(
                        task_id,
                        status="awaiting_approval",
                        diff_text=text,
                        diff_hash=digest,
                        verification={"tests_run": False},
                    )
                if stop() and self.get(task_id)["status"] != "cancelled":
                    self.cancel(task_id)
            return self.get(task_id)


def task_router(service: TaskService):
    router = APIRouter()

    @router.post("/tasks", status_code=201)
    def create(payload: TaskInput):
        return service.submit(payload)

    @router.get("/tasks")
    def tasks(repository_id: str | None = None):
        with service.db() as db:
            rows = db.execute(
                "SELECT id FROM tasks WHERE (? IS NULL OR repository_id = ?) ORDER BY created_at DESC LIMIT 100",
                (repository_id, repository_id),
            ).fetchall()
        return [service.get(row[0]) for row in rows]

    @router.get("/tasks/{task_id}")
    def task(task_id: str):
        return service.get(task_id)

    @router.get("/tasks/{task_id}/events")
    def events(task_id: str, after: int = 0):
        service.get(task_id)
        with service.db() as db:
            rows = db.execute(
                "SELECT * FROM task_events WHERE task_id = ? AND sequence > ? ORDER BY sequence LIMIT 500",
                (task_id, after),
            ).fetchall()
        return [{**dict(row), "payload": json.loads(row["payload"])} for row in rows]

    @router.get("/tasks/{task_id}/evidence")
    def evidence(task_id: str):
        task = service.get(task_id)
        return {
            "task_id": task_id,
            "base_commit": task["base_commit"],
            "evidence": task["evidence"] or [],
        }

    @router.get("/tasks/{task_id}/diff")
    def patch_diff(task_id: str):
        task = service.get(task_id)
        return {key: task[key] for key in ("diff_text", "diff_hash", "approval_status")}

    @router.post("/tasks/{task_id}/approval")
    def approval(task_id: str, payload: ApprovalInput):
        return service.approve(task_id, payload)

    @router.post("/tasks/{task_id}/cancel")
    def cancel(task_id: str):
        return service.cancel(task_id)

    @router.post("/tasks/{task_id}/resume")
    def resume(task_id: str, payload: ResumeInput):
        return service.resume(task_id, payload)

    @router.post("/tasks/{task_id}/tests")
    def run_tests(task_id: str, payload: TestInput):
        return service.test(task_id, payload)

    @router.post("/tasks/{task_id}/repair")
    def repair(task_id: str, payload: RepairInput):
        return service.repair(task_id, payload)

    @router.get("/tasks/{task_id}/tests")
    def tests(task_id: str):
        service.get(task_id)
        with service.db() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM test_runs WHERE task_id = ? ORDER BY created_at", (task_id,)
                )
            ]

    @router.get("/tasks/{task_id}/report")
    def report(task_id: str):
        from fastapi.responses import PlainTextResponse

        task = service.get(task_id)
        body = f"# RepoPilot report\n\nStatus: {task['status']}\n\nBase commit: {task['base_commit']}\n\n{task['answer'] or task['error'] or 'Patch awaiting review'}\n\n## Verification\n\n```json\n{json.dumps(task['verification'], indent=2)}\n```\n"
        return PlainTextResponse(
            body,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{task_id}.md"'},
        )

    return router
