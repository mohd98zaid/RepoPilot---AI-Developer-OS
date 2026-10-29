"""Windows desktop startup and owned-backend shutdown smoke check."""
from __future__ import annotations

import ctypes
import json
import os
import socket
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    if os.name != "nt":
        raise SystemExit("Windows desktop smoke check only")
    app = subprocess.Popen([str(ROOT / "desktop/src-tauri/target/release/repopilot-desktop.exe")],
                           env={**os.environ, "REPOPILOT_MODEL_PROVIDER": "mock"})
    user32 = ctypes.windll.user32
    windows = []
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    @callback_type
    def collect(window, _):
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(ctypes.c_void_p(window), ctypes.byref(pid))
        title = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(ctypes.c_void_p(window), title, 512)
        if pid.value == app.pid and title.value == "RepoPilot" and user32.IsWindowVisible(ctypes.c_void_p(window)):
            windows.append(window)
        return True

    try:
        for _ in range(120):
            if app.poll() is not None:
                raise RuntimeError("Desktop exited before opening its window")
            user32.EnumWindows(collect, 0)
            if windows:
                break
            time.sleep(.25)
        else:
            raise RuntimeError("Desktop window did not open")
        output = subprocess.run(["powershell", "-NoProfile", "-Command",
            f"Get-CimInstance Win32_Process | Where-Object {{ $_.ParentProcessId -eq {app.pid} -and $_.Name -eq 'repopilot-server.exe' }} | Select-Object ProcessId,CommandLine | ConvertTo-Json"],
            capture_output=True, text=True, check=True)
        backend = json.loads(output.stdout)
        port = int(backend["CommandLine"].split("--port ")[1].split()[0])
        with socket.create_connection(("127.0.0.1", port), timeout=3):
            pass
        user32.PostMessageW(ctypes.c_void_p(windows[0]), 0x0010, 0, 0)
        app.wait(timeout=15)
        try:
            connection = socket.create_connection(("127.0.0.1", port), timeout=1)
        except OSError:
            print("Desktop window opened; bundled backend ready; close stopped backend.")
        else:
            connection.close()
            raise RuntimeError("Desktop left its backend running")
    finally:
        if app.poll() is None:
            app.terminate()
            app.wait(timeout=10)
        # Clean up a backend left by a failed assertion or an earlier smoke attempt.
        subprocess.run(["taskkill", "/PID", str(app.pid), "/T", "/F"], capture_output=True, check=False)


if __name__ == "__main__":
    main()
