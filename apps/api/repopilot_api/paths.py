"""Shared path policy for reads, indexing and patch writes."""

from pathlib import Path, PureWindowsPath

IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "coverage",
    ".repopilot-worktrees",
}
SECRET_FILE_NAMES = {
    ".env",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "credentials",
    ".npmrc",
    ".pypirc",
}
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".crt", ".sqlite3", ".db")


def allowed_path(name: str) -> bool:
    parts = name.replace("\\", "/").split("/")
    return bool(parts) and not (
        any(part.lower() in IGNORED_DIRECTORY_NAMES for part in parts)
        or parts[-1].lower() in SECRET_FILE_NAMES
        or parts[-1].lower().startswith(".env.")
        or parts[-1].lower().endswith(SECRET_SUFFIXES)
    )


def scoped_path(root: Path, name: str) -> Path:
    if (
        not name
        or PureWindowsPath(name).drive
        or name.startswith(("/", "\\"))
        or ":" in name
        or any(part in {"..", "", "."} for part in name.replace("\\", "/").split("/"))
    ):
        raise ValueError("path must be a normalized repository-relative path")
    if not allowed_path(name):
        raise ValueError("path is excluded by repository policy")
    root = root.resolve()
    candidate = root
    for part in name.replace("\\", "/").split("/"):
        if part.endswith((".", " ")):
            raise ValueError("ambiguous Windows path")
        candidate = candidate / part
        if candidate.is_symlink() or (
            hasattr(candidate, "is_junction") and candidate.is_junction()
        ):
            raise ValueError("symlink and junction access is not permitted")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("path escapes repository")
    if resolved.exists() and resolved.is_file() and resolved.stat().st_nlink > 1:
        raise ValueError("hard-linked files are not permitted")
    return resolved
