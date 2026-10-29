from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def git_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "sample-repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.name", "RepoPilot Test"], cwd=repository, check=True)
    (repository / "src").mkdir()
    (repository / "src" / "auth.py").write_text(
        "def authenticate(token: str) -> bool:\n    return token == 'valid'\n",
        encoding="utf-8",
    )
    (repository / "src" / "client.ts").write_text(
        "export function createClient() { return { ready: true }; }\n",
        encoding="utf-8",
    )
    (repository / "README.md").write_text(
        "Authentication lives in src/auth.py.\n", encoding="utf-8"
    )
    (repository / ".env").write_text("SECRET=do-not-index\n", encoding="utf-8")
    (repository / ".gitignore").write_text("ignored.py\n.env\n", encoding="utf-8")
    (repository / "ignored.py").write_text("def should_not_appear(): pass\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=repository, check=True)
    return repository
