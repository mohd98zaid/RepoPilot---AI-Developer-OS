from __future__ import annotations

from pathlib import Path

import pytest
from repopilot_api.runner import run_approved_test
from repopilot_api.tools import ToolError, read_file_range


def test_file_tool_blocks_path_escape(git_repository: Path) -> None:
    with pytest.raises(ToolError):
        read_file_range(git_repository, "../outside.txt")


def test_file_tool_blocks_secret_like_file(git_repository: Path) -> None:
    with pytest.raises(ToolError):
        read_file_range(git_repository, ".env")


def test_runner_blocks_unapproved_commands(git_repository: Path) -> None:
    with pytest.raises(ValueError, match="approved"):
        run_approved_test(git_repository, "python -c 'print(1)'", 2, 1000)
