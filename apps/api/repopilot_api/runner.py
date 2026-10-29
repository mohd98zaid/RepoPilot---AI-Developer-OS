from __future__ import annotations

import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .paths import allowed_path
from .security import redact

ALLOWED_COMMANDS = {
    "pytest",
    "python -m pytest",
    "npm test",
    "npm run test",
    "npm run lint",
    "npm run build",
}


@dataclass(frozen=True)
class TestResult:
    command: str
    status: str
    exit_code: int | None
    output: str
    duration_ms: int


def run_approved_test(
    worktree: Path,
    command: str,
    timeout_seconds: int,
    max_output_bytes: int,
    sandbox_mode="docker",
    python_image="python:3.12-slim",
    node_image="node:22-bookworm-slim",
    cancelled=lambda: False,
) -> TestResult:
    normalized = " ".join(command.split())
    if normalized not in ALLOWED_COMMANDS:
        raise ValueError("command is not on the approved test-command list")
    if sandbox_mode != "docker":
        raise ValueError("only Docker sandbox execution is supported")
    docker = shutil.which("docker")
    if not docker:
        raise ValueError("Docker is required for sandboxed execution")
    # Copy only scoped, non-secret source. Never mount the Git worktree metadata or host dependencies.
    copied_bytes = 0

    def excluded(folder, names):
        nonlocal copied_bytes
        result = []
        for name in names:
            path = Path(folder) / name
            if (
                not allowed_path(name)
                or path.is_symlink()
                or (hasattr(path, "is_junction") and path.is_junction())
                or path.is_file()
                and (path.stat().st_size > 2_000_000 or path.stat().st_nlink > 1)
            ):
                result.append(name)
            elif path.is_file():
                raw = path.read_bytes()
                copied_bytes += len(raw)
                if copied_bytes > 100_000_000:
                    raise ValueError("sandbox source exceeds 100 MB staging budget")
                if b"\0" in raw or redact(raw.decode("utf-8", errors="replace")) != raw.decode(
                    "utf-8", errors="replace"
                ):
                    result.append(name)
        return result

    started = time.monotonic()
    name = "repopilot-" + uuid4().hex
    parts = normalized.split()
    image = node_image if parts[0] == "npm" else python_image
    output = bytearray()
    lock = threading.Lock()
    with tempfile.TemporaryDirectory(prefix="repopilot-sandbox-") as temp:
        staged = Path(temp) / "source"
        shutil.copytree(worktree, staged, ignore=excluded)
        args = [
            docker,
            "run",
            "--pull=never",
            "--name",
            name,
            "--rm",
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--pids-limit=128",
            "--cpus=2",
            "--memory=1g",
            "--memory-swap=1g",
            "--tmpfs=/tmp:rw,nosuid,size=128m",
            "--tmpfs=/workspace:rw,nosuid,size=256m,mode=1777",
            "--user=1000:1000",
            "--mount",
            f"type=bind,source={staged},target=/source,readonly",
            "--workdir=/workspace",
            image,
            "sh",
            "-c",
            'cp -R /source/. /workspace/ && exec "$@"',
            "sh",
            *parts,
        ]
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        def drain():
            while chunk := process.stdout.read(4096):
                with lock:
                    output.extend(chunk)
                    if len(output) > max_output_bytes:
                        del output[:-max_output_bytes]

        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        status = "failed"
        try:
            while process.poll() is None:
                if cancelled() or time.monotonic() - started > timeout_seconds:
                    status = "cancelled" if cancelled() else "timeout"
                    subprocess.run(
                        [docker, "rm", "-f", name], capture_output=True, timeout=15, check=False
                    )
                    process.kill()
                    process.wait(timeout=5)
                    break
                time.sleep(0.05)
            else:
                status = "passed" if process.returncode == 0 else "failed"
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            reader.join(timeout=5)
            process.stdout.close()
        return TestResult(
            normalized,
            status,
            process.returncode if status in {"passed", "failed"} else None,
            redact(bytes(output).decode("utf-8", errors="replace")),
            int((time.monotonic() - started) * 1000),
        )
