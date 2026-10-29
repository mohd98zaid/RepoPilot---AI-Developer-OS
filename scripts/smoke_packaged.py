from __future__ import annotations

import os
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    executable = ROOT / "desktop/src-tauri/resources/repopilot-server/repopilot-server.exe"
    with tempfile.TemporaryDirectory(prefix="repopilot-packaged-") as temp:
        directory = Path(temp)
        repo = directory / "fixture"
        shutil.copytree(ROOT / "evals/fixture", repo)
        for args in (
            ["init", "-q"],
            ["add", "."],
            [
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-qm",
                "fixture",
            ],
        ):
            subprocess.run(["git", *args], cwd=repo, capture_output=True, check=True)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        with (directory / "server.log").open("w+b") as log:
            process = subprocess.Popen(
                [str(executable), "--port", str(port)],
                cwd=directory,
                env={
                    **os.environ,
                    "REPOPILOT_DATABASE_PATH": str(directory / "data.sqlite3"),
                    "REPOPILOT_MODEL_PROVIDER": "mock",
                    "REPOPILOT_SESSION_TOKEN": "packaged-smoke",
                },
                stdout=log,
                stderr=log,
            )
            try:
                with httpx.Client(
                    base_url=f"http://127.0.0.1:{port}",
                    headers={"X-RepoPilot-Token": "packaged-smoke"},
                    timeout=20,
                ) as client:
                    for _ in range(240):
                        if process.poll() is not None:
                            log.seek(0)
                            raise RuntimeError(log.read().decode(errors="replace"))
                        try:
                            if client.get("/health").status_code == 200:
                                break
                        except httpx.HTTPError:
                            time.sleep(0.25)
                    else:
                        raise RuntimeError("packaged backend startup timeout")
                    assert "RepoPilot" in client.get("/").text
                    response = client.post("/repositories", json={"local_path": str(repo)})
                    response.raise_for_status()
                    repository_id = response.json()["id"]
                    client.post(f"/repositories/{repository_id}/index").raise_for_status()
                    result = client.post(
                        "/tasks",
                        json={"repository_id": repository_id, "request": "authenticate_user"},
                    )
                    result.raise_for_status()
                    assert result.json()["status"] == "completed", result.text
                    print(
                        "Packaged backend: UI assets, registration, indexing and LangGraph investigation passed."
                    )
            finally:
                process.terminate()
                process.wait(timeout=10)


if __name__ == "__main__":
    main()
