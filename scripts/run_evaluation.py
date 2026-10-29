"""Run the reproducible synthetic retrieval baseline without model inference."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from repopilot_api.database import connect
from repopilot_api.evaluation import evaluate
from repopilot_api.git import repository_metadata
from repopilot_api.indexer import index_repository, search_repository

ROOT = Path(__file__).resolve().parents[1]


def main():
    cases = [
        json.loads(line)
        for line in (ROOT / "evals/datasets/retrieval.jsonl").read_text().splitlines()
    ]
    with tempfile.TemporaryDirectory(prefix="repopilot-eval-") as temp:
        root = Path(temp) / "fixture"
        shutil.copytree(ROOT / "evals/fixture", root, ignore=shutil.ignore_patterns("__pycache__"))
        for args in (
            ["init", "-q"],
            ["add", "."],
            [
                "-c",
                "user.name=RepoPilot evaluation",
                "-c",
                "user.email=evaluation@example.invalid",
                "commit",
                "-qm",
                "Synthetic fixture",
            ],
        ):
            subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
        commit = repository_metadata(root)["current_commit"]
        with connect(Path(temp) / "evaluation.sqlite3") as db:
            db.execute(
                "INSERT INTO repositories(id, display_name, local_path, current_commit, created_at, updated_at) VALUES ('fixture', 'fixture', ?, ?, '', '')",
                (str(root), commit),
            )
            index_repository(db, "fixture", root, commit, 2_000_000)
            report = evaluate(cases, lambda query: search_repository(db, "fixture", query, 20))
        report.update(
            os=platform.platform(),
            python=platform.python_version(),
            commit=commit,
            scope="25 synthetic retrieval queries, 10 MIT fixture modules; no diagnosis or patch-quality claims",
        )
    destination = ROOT / "evals/reports"
    destination.mkdir(exist_ok=True)
    (destination / "retrieval.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (destination / "retrieval.md").write_text(
        f"# Retrieval baseline\n\n{report['scope']}\n\nOS: {report['os']}\n\nPython: {report['python']}\n\n"
        f"Recall@5: {report['recall_at_5']:.3f}\n\nMRR: {report['mrr']:.3f}\n\np50: {report['p50_ms']:.2f} ms; p95: {report['p95_ms']:.2f} ms\n\n"
        "Reproduce: `.venv/Scripts/python.exe scripts/run_evaluation.py`. Fixture code is covered by the project MIT license. Semantic retrieval requires a configured local embedding model and a separate comparison.\n",
        encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))
    if report["recall_at_5"] < 0.9:
        raise SystemExit("Retrieval regression gate failed")


if __name__ == "__main__":
    main()
