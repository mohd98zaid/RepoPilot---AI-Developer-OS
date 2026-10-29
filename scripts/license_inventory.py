"""Generate version/license metadata inventory and retain distributed license texts."""

from __future__ import annotations

import importlib.metadata
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    rows = []
    destination = ROOT / "docs/licenses"
    for entry in (ROOT / "requirements.lock").read_text().splitlines():
        if not entry or entry.startswith("#"):
            continue
        name = entry.split("==")[0]
        distribution = importlib.metadata.distribution(name)
        metadata = distribution.metadata
        license_name = (
            metadata.get("License-Expression") or metadata.get("License") or "Not declared"
        )
        license_name = license_name.splitlines()[0][:160]
        rows.append(("Python", name, distribution.version, license_name))
        for file in distribution.files or []:
            if Path(file).name.lower().startswith(("license", "notice", "copying")):
                original = distribution.locate_file(file)
                if original.is_file():
                    folder = destination / "python" / name
                    folder.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(original, folder / original.name)
    for workspace in ("web", "desktop"):
        lock = json.loads((ROOT / workspace / "package-lock.json").read_text())
        for path, item in lock["packages"].items():
            if not path:
                continue
            name = path.removeprefix("node_modules/")
            rows.append(
                (workspace, name, item.get("version", ""), item.get("license", "Not declared"))
            )
            source = ROOT / workspace / path
            if source.is_dir():
                for original in source.iterdir():
                    if original.is_file() and original.name.lower().startswith(
                        ("license", "notice", "copying")
                    ):
                        folder = destination / workspace / name
                        folder.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(original, folder / original.name)
    metadata = subprocess.run(
        ["cargo", "metadata", "--format-version", "1", "--locked"],
        cwd=ROOT / "desktop/src-tauri",
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    for package in json.loads(metadata.stdout)["packages"]:
        if package["name"] == "repopilot-desktop":
            continue
        name = package["name"] + "-" + package["version"]
        rows.append(
            ("Rust", package["name"], package["version"], package.get("license") or "Not declared")
        )
        source = Path(package["manifest_path"]).parent
        for original in source.iterdir():
            if original.is_file() and original.name.lower().startswith(
                ("license", "notice", "copying")
            ):
                folder = destination / "rust" / name
                folder.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, folder / original.name)
    lines = [
        "# Third-party dependency inventory",
        "",
        "Generated from installed Python metadata, npm lockfiles and Cargo metadata. License texts included under `docs/licenses/`. This is a metadata inventory, not a completed legal review. Entries marked Not declared require manual review. Model-weight licenses require separate review. No model weights are distributed.",
        "",
        "| Ecosystem | Dependency | Version | Declared license |",
        "|---|---|---|---|",
    ]
    lines += [
        "| " + " | ".join(str(cell).replace("|", "/") for cell in row) + " |"
        for row in sorted(rows)
    ]
    (ROOT / "docs/THIRD_PARTY_NOTICES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Inventoried {len(rows)} dependencies")


if __name__ == "__main__":
    main()
