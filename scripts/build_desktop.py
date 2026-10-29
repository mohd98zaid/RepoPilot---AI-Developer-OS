from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    npm = shutil.which("npm.cmd" if sys.platform == "win32" else "npm")
    if not npm:
        raise SystemExit("npm is required")

    def run(args, cwd=ROOT):
        subprocess.run(args, cwd=cwd, check=True)

    run([npm, "ci"], ROOT / "web")
    run([npm, "run", "build"], ROOT / "web")
    resources = ROOT / "desktop/src-tauri/resources"
    resources.mkdir(exist_ok=True)
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--name",
        "repopilot-server",
        "--distpath",
        str(resources),
        "--workpath",
        str(ROOT / "build/backend"),
        "--specpath",
        str(ROOT / "build"),
        "--add-data",
        f"{ROOT / 'web/dist'};web/dist",
        "--collect-submodules",
        "langgraph",
        "--collect-submodules",
        "langchain_core",
        "--collect-submodules",
        "uvicorn",
        "--recursive-copy-metadata",
        "langgraph",
        "--recursive-copy-metadata",
        "langgraph-checkpoint-sqlite",
        str(ROOT / "scripts/server_entry.py"),
    ]
    run(args)
    run([npm, "ci"], ROOT / "desktop")
    run([npm, "run", "build"], ROOT / "desktop")
    artifacts = list((ROOT / "desktop/src-tauri/target/release/bundle/nsis").glob("*.exe"))
    checksums = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts}
    (ROOT / "desktop/checksums.json").write_text(json.dumps(checksums, indent=2), encoding="utf-8")
    print(json.dumps(checksums, indent=2))


if __name__ == "__main__":
    main()
