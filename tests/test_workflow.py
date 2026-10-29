from __future__ import annotations

from repopilot_api.model import ModelGateway
from repopilot_api.workflow import run_investigation


def test_langgraph_investigation_has_bounded_steps() -> None:
    result = run_investigation(
        lambda query: [
            {"path": "src/example.py", "line_start": 1, "line_end": 2, "excerpt": query}
        ],
        ModelGateway("mock", "", None, None, None),
        "where is the example?",
    )

    assert result["status"] == "completed"
    assert result["step_count"] == 5
    assert result["tool_call_count"] == 1
    assert result["plan"]
    assert result["verification"]["evidence_fresh"] is True
    assert result["verification"]["claims_verified"] is False
