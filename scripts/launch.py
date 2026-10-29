"""Single-process local app launcher, with readiness checks and owned-process cleanup."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args, cwd=ROOT):
    subprocess.run(args, cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--smoke", action="store_true", help="Verify launch and shut down automatically"
    )
    parser.add_argument("--desktop", action="store_true")
    args = parser.parse_args()
    os.chdir(ROOT)
    if sys.version_info < (3, 11):  # noqa: UP036 - bootstrap runs before package requirements are checked
        raise RuntimeError("Python 3.11 or newer is required")
    if not shutil.which("git"):
        raise RuntimeError("Install Git before launching RepoPilot")
    python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        run([sys.executable, "-m", "venv", str(ROOT / ".venv")])
    stamp = ROOT / ".venv" / "repopilot-dependencies.sha256"
    dependency_files = [ROOT / "pyproject.toml", ROOT / "requirements.lock"]
    digest = hashlib.sha256(
        b"".join(p.read_bytes() for p in dependency_files if p.exists())
    ).hexdigest()
    if not stamp.exists() or stamp.read_text() != digest:
        if (ROOT / "requirements.lock").exists():
            run([str(python), "-m", "pip", "install", "-r", "requirements.lock"])
        run([str(python), "-m", "pip", "install", "-e", "."])
        stamp.write_text(digest)
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise RuntimeError("Node.js and npm are required to build the web UI")
    web = ROOT / "web"
    if not (web / "node_modules").exists():
        run([npm, "ci"], web)
    run([npm, "run", "build"], web)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    token = secrets.token_urlsafe(32)
    env = {
        **os.environ,
        "REPOPILOT_SESSION_TOKEN": token,
        "LANGCHAIN_TRACING_V2": "false",
        "LANGSMITH_TRACING": "false",
    }
    process = subprocess.Popen(
        [
            str(python),
            "-m",
            "uvicorn",
            "repopilot_api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
        ],
        cwd=ROOT,
        env=env,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(120):
            if process.poll() is not None:
                raise RuntimeError("API stopped before becoming ready")
            try:
                with urllib.request.urlopen(url + "/health", timeout=1) as response:
                    if json.load(response)["status"] == "ok":
                        break
            except (OSError, ValueError):
                time.sleep(0.25)
        else:
            raise RuntimeError("API readiness timed out")
        request = urllib.request.Request(
            url + "/api/repositories", headers={"X-RepoPilot-Token": token}
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            json.load(response)
        print(f"RepoPilot is ready at {url}. Press Ctrl+C here to stop.", flush=True)
        if args.smoke:
            print("Launcher smoke check passed.")
            return
        private_url = url + "/#token=" + token
        if args.desktop:
            executable = ROOT / "desktop/src-tauri/target/release/repopilot-desktop.exe"
            if not executable.exists():
                raise RuntimeError("Build desktop first with build-desktop.bat")
            subprocess.run([str(executable)], env={**env, "REPOPILOT_URL": private_url}, check=True)
        else:
            webbrowser.open(private_url)
            process.wait()
    except KeyboardInterrupt:
        pass
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    main()
