"""Entry point for the packaged backend sidecar."""

import argparse
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    options = parser.parse_args()
    if getattr(sys, "frozen", False):
        os.environ["REPOPILOT_WEB_DIR"] = str(Path(sys._MEIPASS) / "web" / "dist")
    import uvicorn
    from repopilot_api.main import app

    uvicorn.run(app, host="127.0.0.1", port=options.port, access_log=False, loop="asyncio")


if __name__ == "__main__":
    main()
