# Sandboxed tests

Start Docker Desktop before running tests through RepoPilot. The application never falls back to running project scripts on the host.

Prepare a Python image (network is needed only while explicitly building the image):

```powershell
docker build -f sandbox/Dockerfile.python -t repopilot-python-tests .
```

Set `REPOPILOT_SANDBOX_PYTHON_IMAGE=repopilot-python-tests` in `.env`, then restart the app. For another repository, build a dedicated image containing its pinned dependencies and test tools. Base `python:3.12-slim` does not contain pytest. The same rule applies to Node images and npm project dependencies: use a prebuilt project image with tools available on PATH/NODE_PATH. RepoPilot does not automatically run networked dependency installs.

Execution copies scoped source into a size-limited container tmpfs. It does not mount `.git`, dependency folders, credential files, host home directories, or the Docker socket. The source bind mount is read-only. Network is disabled, UID is 1000, capabilities are dropped, and memory/CPU/process/time limits are applied. Docker images must already be local (`--pull=never`). Tests cannot change the reviewed worktree.

The UI runs the baseline and patch with the same configured image/command. A regression is reported only when baseline passes and the patch fails. The repair action allows two explicit attempts and reruns baseline plus patch after each attempt. Passing tests are evidence, not proof of correctness.
