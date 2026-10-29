from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import expect, sync_playwright


@pytest.mark.browser
def test_browser_register_index_investigate_patch_and_reject(tmp_path, git_repository):
    root = Path(__file__).resolve().parents[2]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {
        **os.environ,
        "REPOPILOT_DATABASE_PATH": str(tmp_path / "browser.sqlite3"),
        "REPOPILOT_MODEL_PROVIDER": "mock",
        "REPOPILOT_SESSION_TOKEN": "browser-session",
    }
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "repopilot_api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
        ],
        env=env,
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(80):
            try:
                if httpx.get(url + "/health").status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.1)
        else:
            pytest.fail("Server startup failed")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url + "/#token=browser-session")
            page.get_by_label("Local repository path").fill(str(git_repository))
            page.get_by_role("button", name="Register", exact=True).click()
            page.get_by_role("button", name="Index sample-repository").click()
            expect(page.get_by_role("status")).to_contain_text("Indexed", timeout=15000)
            page.get_by_label("Search repository").fill("authenticate")
            page.get_by_role("button", name="Search", exact=True).click()
            expect(page.locator(".evidence-meta").first).to_contain_text("src/auth.py")
            page.get_by_label("Task request").fill("Where is authenticate implemented?")
            page.get_by_role("button", name="Run task").click()
            expect(page.locator(".answer")).to_contain_text("src/auth.py", timeout=15000)
            page.get_by_label("Task type").select_option("patch")
            page.get_by_label("Task request").fill("Manual patch review")
            page.get_by_text("Optional manual change", exact=False).click()
            page.get_by_label("Patch path").fill("src/auth.py")
            page.get_by_label("Patch content").fill(
                "def authenticate(token):\n    return bool(token)\n"
            )
            page.get_by_role("button", name="Run task").click()
            expect(page.locator(".patch-review")).to_contain_text("bool(token)", timeout=15000)
            original = (git_repository / "src/auth.py").read_bytes()
            page.get_by_role("button", name="Reject", exact=True).click()
            expect(page.get_by_role("status")).to_contain_text("rejected", timeout=10000)
            assert (git_repository / "src/auth.py").read_bytes() == original
            assert errors == []
            browser.close()
    finally:
        process.terminate()
        process.wait(timeout=10)
