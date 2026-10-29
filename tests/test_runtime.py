from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest
from repopilot_api.model import ModelGateway
from repopilot_api.tools import ToolError, read_file_range, repository_path
from test_api import make_client


def ready(tmp_path, git_repository):
    client = make_client(tmp_path)
    repo = client.post("/repositories", json={"local_path": str(git_repository)}).json()
    assert client.post(f"/repositories/{repo['id']}/index").status_code == 200
    return client, repo["id"]


def wait_task(client, task_id):
    for _ in range(100):
        task = client.get(f"/tasks/{task_id}").json()
        if task["status"] not in {"running", "testing"}:
            return task
        time.sleep(0.05)
    pytest.fail("Task did not terminate")


def patch_task(client, repo):
    response = client.post(
        "/tasks",
        json={
            "repository_id": repo,
            "task_type": "patch",
            "request": "Fix auth",
            "changes": [
                {
                    "path": "src/auth.py",
                    "content": "def authenticate(token):\n    return bool(token)\n",
                }
            ],
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "awaiting_approval"
    return response.json()


def test_auth_and_origin_are_enforced(tmp_path):
    client = make_client(tmp_path)
    assert (
        client.get("/api/repositories", headers={"X-RepoPilot-Token": "wrong"}).status_code == 401
    )
    assert (
        client.get("/repositories", headers={"Origin": "https://attacker.test"}).status_code == 403
    )
    assert client.get("/api/repositories").status_code == 200


def test_valid_session_cookie_survives_tab_reload(tmp_path):
    client = make_client(tmp_path)
    first = client.get("/api/repositories")
    assert first.status_code == 200
    assert "repopilot_session" in first.cookies

    reloaded = type(client)(client.app, headers={})
    reloaded.cookies.update(first.cookies)
    assert reloaded.get("/api/repositories").status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "../x.py",
        "C:\\secret.py",
        "src/../auth.py",
        "src/auth.py:stream",
        ".env.staging",
        ".git/config",
        "src./x.py",
    ],
)
def test_path_policy_on_windows_and_posix(git_repository, path):
    with pytest.raises(ToolError):
        repository_path(git_repository, path)


def test_parent_symlink_is_blocked(git_repository, tmp_path):
    target = tmp_path / "outside"
    target.mkdir()
    (target / "a.py").write_text("private")
    link = git_repository / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("Windows symlink privilege unavailable")
    with pytest.raises(ToolError):
        read_file_range(git_repository, "link/a.py")


def test_stale_evidence_and_snapshot_history(tmp_path, git_repository):
    client, repo = ready(tmp_path, git_repository)
    task = client.post(
        "/tasks", json={"repository_id": repo, "request": "Where is authenticate implemented?"}
    ).json()
    assert task["status"] == "completed"
    original = client.get(f"/tasks/{task['id']}/evidence").json()
    (git_repository / "src/auth.py").write_text("def renamed(): pass\n")
    results = client.post(f"/repositories/{repo}/search", json={"query": "authenticate"}).json()
    assert results["evidence"] == []
    assert client.get(f"/tasks/{task['id']}/evidence").json() == original


def test_approval_replay_and_source_preservation(tmp_path, git_repository):
    client, repo = ready(tmp_path, git_repository)
    task = patch_task(client, repo)
    original = (git_repository / "src/auth.py").read_bytes()
    request = {"decision": "approved", "action_hash": "0" * 64}
    assert client.post(f"/tasks/{task['id']}/approval", json=request).status_code == 409
    assert (git_repository / "src/auth.py").read_bytes() == original
    request["action_hash"] = task["diff_hash"]
    assert client.post(f"/tasks/{task['id']}/approval", json=request).status_code == 200
    assert "bool(token)" in (git_repository / "src/auth.py").read_text()
    assert client.post(f"/tasks/{task['id']}/approval", json=request).status_code == 409


def test_modified_worktree_invalidates_approval(tmp_path, git_repository):
    client, repo = ready(tmp_path, git_repository)
    task = patch_task(client, repo)
    (Path(task["worktree_path"]) / "src/auth.py").write_text("malicious replacement")
    response = client.post(
        f"/tasks/{task['id']}/approval",
        json={"action_hash": task["diff_hash"], "decision": "approved"},
    )
    assert response.status_code == 409
    assert client.post(f"/tasks/{task['id']}/cancel").json()["status"] == "cancelled"
    assert not Path(task["worktree_path"]).exists()


def test_async_cancellation_and_db_remains_responsive(tmp_path, git_repository, monkeypatch):
    client, repo = ready(tmp_path, git_repository)
    entered, release = threading.Event(), threading.Event()

    def slow(self, request, context):
        entered.set()
        release.wait(5)
        return "This late result must not become success"

    monkeypatch.setattr(ModelGateway, "complete", slow)
    task = client.post(
        "/tasks", json={"repository_id": repo, "request": "authenticate", "background": True}
    ).json()
    assert entered.wait(3)
    try:
        assert client.get("/repositories").status_code == 200
        assert client.post(f"/tasks/{task['id']}/cancel").status_code == 200
    finally:
        release.set()
    assert wait_task(client, task["id"])["status"] == "cancelled"


def test_clarification_checkpoint_survives_restart(tmp_path, git_repository):
    client, repo = ready(tmp_path, git_repository)
    task = client.post(
        "/tasks", json={"repository_id": repo, "request": "nonexistent_identifier"}
    ).json()
    assert task["status"] == "awaiting_input"
    restarted = make_client(tmp_path)
    response = restarted.post(f"/tasks/{task['id']}/resume", json={"answer": "authenticate"})
    assert response.status_code == 200
    result = wait_task(restarted, task["id"])
    assert result["status"] == "completed"
    assert "src/auth.py" in result["answer"]
