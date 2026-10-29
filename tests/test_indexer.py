from __future__ import annotations

from pathlib import Path

from repopilot_api.database import connect
from repopilot_api.git import repository_metadata
from repopilot_api.indexer import index_repository, load_files, search_repository


def test_load_files_respects_git_and_secret_exclusions(git_repository: Path) -> None:
    files = load_files(git_repository, 100_000)
    paths = {item.relative_path for item in files}

    assert "src/auth.py" in paths
    assert "src/client.ts" in paths
    assert ".env" not in paths
    assert "ignored.py" not in paths


def test_index_and_search_return_line_evidence(git_repository: Path, tmp_path: Path) -> None:
    connection = connect(tmp_path / "test.sqlite3")
    metadata = repository_metadata(git_repository)
    connection.execute(
        """INSERT INTO repositories
           (id, display_name, local_path, branch, current_commit, created_at, updated_at)
           VALUES ('repo-1', 'sample', ?, ?, ?, 'now', 'now')""",
        (str(git_repository), metadata["branch"], metadata["current_commit"]),
    )
    connection.commit()

    count = index_repository(
        connection,
        "repo-1",
        git_repository,
        str(metadata["current_commit"]),
        100_000,
    )
    results = search_repository(connection, "repo-1", "authenticate")

    assert count == 3
    assert results[0]["path"] == "src/auth.py"
    assert results[0]["line_start"] == 1
    assert "authenticate" in str(results[0]["excerpt"])


def test_search_rejects_empty_search_terms(tmp_path: Path) -> None:
    connection = connect(tmp_path / "test.sqlite3")
    try:
        search_repository(connection, "repo-1", "!!!")
    except ValueError as exc:
        assert "search query" in str(exc)
    else:
        raise AssertionError("expected empty search terms to be rejected")
