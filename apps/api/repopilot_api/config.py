from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv(Path.cwd() / ".env")
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return parsed


@dataclass(frozen=True)
class Settings:
    database_path: Path
    max_file_bytes: int
    model_provider: str
    model_base_url: str
    model_api_key: str | None
    primary_model: str | None
    fallback_model: str | None
    session_token: str | None = None
    task_timeout_seconds: int = 120
    max_output_bytes: int = 200_000
    sandbox_mode: str = "docker"
    sandbox_python_image: str = "python:3.12-slim"
    sandbox_node_image: str = "node:22-bookworm-slim"
    embedding_model: str | None = None
    embedding_endpoint: str = "http://127.0.0.1:11434"

    def __post_init__(self):
        if self.model_provider not in {"mock", "ollama", "openai_compatible"}:
            raise ValueError("unsupported model provider")
        endpoint = urlparse(self.model_base_url)
        if (
            endpoint.scheme not in {"http", "https"}
            or not endpoint.hostname
            or endpoint.username
            or endpoint.password
            or endpoint.query
        ):
            raise ValueError("model URL must be HTTP(S) without credentials or query parameters")
        local = endpoint.hostname in {"localhost", "127.0.0.1", "::1"}
        if self.model_provider == "ollama" and not local:
            raise ValueError("Ollama provider must use loopback")
        if not local and endpoint.scheme != "https":
            raise ValueError("remote providers require HTTPS")
        if self.sandbox_mode != "docker":
            raise ValueError("sandbox mode must be docker")

    @classmethod
    def from_env(cls) -> Settings:
        configured_provider = os.getenv("REPOPILOT_MODEL_PROVIDER")
        provider = configured_provider or (
            "openai_compatible" if os.getenv("NVIDIA_API_KEY") else "mock"
        )
        return cls(
            database_path=Path(os.getenv("REPOPILOT_DATABASE_PATH", "data/repopilot.sqlite3")),
            max_file_bytes=_int_env("REPOPILOT_MAX_FILE_BYTES", 2_000_000),
            model_provider=provider.strip().lower(),
            model_base_url=os.getenv("REPOPILOT_MODEL_BASE_URL")
            or os.getenv("NVIDIA_BASE_URL", "http://localhost:11434"),
            model_api_key=os.getenv("REPOPILOT_MODEL_API_KEY")
            or os.getenv("NVIDIA_API_KEY")
            or None,
            primary_model=os.getenv("REPOPILOT_PRIMARY_MODEL")
            or os.getenv("NVIDIA_PRIMARY_MODEL")
            or None,
            fallback_model=os.getenv("REPOPILOT_FALLBACK_MODEL")
            or os.getenv("NVIDIA_FALLBACK_MODEL")
            or None,
            session_token=os.getenv("REPOPILOT_SESSION_TOKEN") or None,
            task_timeout_seconds=_int_env("REPOPILOT_TASK_TIMEOUT_SECONDS", 120),
            max_output_bytes=_int_env("REPOPILOT_MAX_OUTPUT_BYTES", 200_000),
            sandbox_mode=os.getenv("REPOPILOT_SANDBOX_MODE", "docker").strip().lower(),
            sandbox_python_image=os.getenv("REPOPILOT_SANDBOX_PYTHON_IMAGE", "python:3.12-slim"),
            sandbox_node_image=os.getenv("REPOPILOT_SANDBOX_NODE_IMAGE", "node:22-bookworm-slim"),
            embedding_model=os.getenv("REPOPILOT_EMBEDDING_MODEL") or None,
            embedding_endpoint=os.getenv("REPOPILOT_EMBEDDING_ENDPOINT", "http://127.0.0.1:11434"),
        )
