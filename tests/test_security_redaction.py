from repopilot_api.security import redact


def test_redact_removes_common_credentials() -> None:
    output = redact("NVIDIA_API_KEY=nvapi-123456789012345678 and password=hunter2")
    assert "nvapi-123456789012345678" not in output
    assert "hunter2" not in output
    assert "[REDACTED]" in output
