from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from repopilot_api.config import Settings
from repopilot_api.main import create_app


def make_client(tmp_path: Path) -> TestClient:
    settings = Settings(
        database_path=tmp_path / "api.sqlite3",
        max_file_bytes=100_000,
        model_provider="mock",
        model_base_url="http://localhost:11434",
        model_api_key=None,
        primary_model=None,
        fallback_model=None,
        session_token="test-session",
    )
    return TestClient(create_app(settings), headers={"X-RepoPilot-Token": "test-session"})


def test_health_does_not_expose_model_credentials(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "model": {"provider": "mock", "configured": True, "primary_model": None},
    }


def test_register_index_and_search_repository(tmp_path: Path, git_repository: Path) -> None:
    client = make_client(tmp_path)

    registered = client.post("/repositories", json={"local_path": str(git_repository)})
    assert registered.status_code == 201
    repository = registered.json()
    assert repository["display_name"] == "sample-repository"
    assert repository["dirty"] is False

    indexed = client.post(f"/repositories/{repository['id']}/index")
    assert indexed.status_code == 200
    assert indexed.json()["indexed_file_count"] == 3

    searched = client.post(
        f"/repositories/{repository['id']}/search", json={"query": "authenticate"}
    )
    assert searched.status_code == 200
    assert searched.json()["evidence"][0]["path"] == "src/auth.py"


def test_search_requires_index(tmp_path: Path, git_repository: Path) -> None:
    client = make_client(tmp_path)
    registered = client.post("/repositories", json={"local_path": str(git_repository)}).json()

    response = client.post(
        f"/repositories/{registered['id']}/search", json={"query": "authenticate"}
    )

    assert response.status_code == 409


def test_investigation_task_returns_evidence_and_events(
    tmp_path: Path, git_repository: Path
) -> None:
    client = make_client(tmp_path)
    repository = client.post("/repositories", json={"local_path": str(git_repository)}).json()
    client.post(f"/repositories/{repository['id']}/index")

    response = client.post(
        "/tasks",
        json={
            "repository_id": repository["id"],
            "task_type": "investigate",
            "request": "authenticate",
        },
    )

    assert response.status_code == 201
    task = response.json()
    assert task["status"] == "completed"
    assert "src/auth.py" in task["answer"]
    events = client.get(f"/tasks/{task['id']}/events")
    assert events.status_code == 200
    assert [event["event_type"] for event in events.json()] == [
        "task_started",
        "validate",
        "plan",
        "retrieve",
        "analyze",
        "verify",
        "task_completed",
    ]


def test_patch_task_requires_matching_approval_hash(tmp_path: Path, git_repository: Path) -> None:
    client = make_client(tmp_path)
    repository = client.post("/repositories", json={"local_path": str(git_repository)}).json()
    client.post(f"/repositories/{repository['id']}/index")
    response = client.post(
        "/tasks",
        json={
            "repository_id": repository["id"],
            "task_type": "patch",
            "request": "update authentication",
            "changes": [
                {
                    "path": "src/auth.py",
                    "content": "def authenticate(token: str) -> bool:\n    return True\n",
                }
            ],
        },
    )

    assert response.status_code == 201
    task = response.json()
    assert task["status"] == "awaiting_approval"
    diff = client.get(f"/tasks/{task['id']}/diff").json()
    rejected = client.post(
        f"/tasks/{task['id']}/approval",
        json={"action_hash": diff["diff_hash"], "decision": "rejected"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
