import os
import shutil
import subprocess

import pytest
from repopilot_api.runner import run_approved_test


@pytest.mark.docker
def test_real_container_blocks_network_and_credentials(tmp_path):
    docker = shutil.which("docker")
    if (
        not docker
        or subprocess.run([docker, "info"], capture_output=True, timeout=15, check=False).returncode
    ):
        pytest.skip("Docker engine is not running")
    image = os.getenv("REPOPILOT_TEST_IMAGE", "repopilot-python-tests")
    if subprocess.run(
        [docker, "image", "inspect", image], capture_output=True, timeout=15, check=False
    ).returncode:
        pytest.skip("Build sandbox/Dockerfile.python as repopilot-python-tests first")
    (tmp_path / ".env").write_text("private data")
    (tmp_path / ".git").write_text("gitdir: /private/host/repository")
    (tmp_path / "test_isolation.py").write_text("""import os
import socket
from pathlib import Path
def test_boundaries():
    assert not Path('/source/.env').exists()
    assert not Path('/source/.git').exists()
    assert 'NVIDIA_API_KEY' not in os.environ
    try:
        socket.create_connection(('1.1.1.1', 443), timeout=1)
    except OSError:
        return
    raise AssertionError('network was not isolated')
""")
    result = run_approved_test(tmp_path, "python -m pytest", 30, 20000, python_image=image)
    assert result.status == "passed", result.output
