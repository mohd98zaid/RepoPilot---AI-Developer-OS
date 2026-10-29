# RepoPilot

RepoPilot is a local-first AI developer environment for understanding repositories, investigating issues, proposing reviewable changes, and verifying patches in isolation.

It is Windows-first and combines React/Vite, FastAPI, SQLite/FTS5, Tree-sitter, LangGraph, Git worktrees, Docker, and an optional Tauri desktop shell.

RepoPilot does not auto-merge, auto-deploy, or treat model output as executable authority.

## Contents

- [Features](#features)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Using RepoPilot](#using-repopilot)
- [Architecture](#architecture)
- [Workflows](#workflows)
- [API](#api)
- [Security](#security)
- [Development](#development)
- [Testing and evaluation](#testing-and-evaluation)
- [Desktop packaging](#desktop-packaging)
- [Structure](#structure)
- [Limitations](#limitations)
- [License](#license)

## Features

### Repository intelligence

- Register local Git repositories.
- Detect branch, commit, dirty state, status, and recent commits.
- Respect `.gitignore` and `.repopilotignore`.
- Index Python, JavaScript, JSX, TypeScript, TSX, Markdown, JSON, YAML, and TOML.
- Extract Tree-sitter symbols, imports, and syntactic call candidates.
- Store file hashes, commit hashes, line ranges, and evidence hashes.
- Incrementally update changed files and remove stale files.
- Exclude secrets, generated files, dependencies, binaries, symlinks, junctions, hard links, and oversized files.

### Search and navigation

- Exact identifier and symbol search.
- SQLite FTS5 lexical search.
- Lexical reference candidates.
- Repository structure and language summaries.
- Optional local embedding search with hybrid reciprocal-rank fusion.
- Safe file listing and bounded line-range source reads.

### AI workflows

- Explain repository concepts.
- Investigate errors and issue descriptions.
- Generate bounded plans and hypotheses.
- Require evidence IDs in structured model responses.
- Verify evidence freshness before completion.
- Pause for clarification and resume after restart.
- Track task state, events, progress, evidence, and verification.
- Cancel long-running tasks.

### Patch and testing workflows

- Generate patches with a configured model or provide manual file contents.
- Work only in detached Git worktrees until approval.
- Calculate immutable diff hashes.
- Reject stale approvals and modified worktrees.
- Run baseline and patch tests in Docker.
- Disable sandbox networking and host credential access.
- Compare baseline and patch results.
- Attempt bounded repair for verified regressions.
- Export Markdown reports.

### Packaging

- Browser development mode.
- Single-process local launcher.
- Tauri 2 desktop shell.
- Bundled Python backend.
- Windows NSIS installer.
- SHA-256 checksum generation.

## Quick start

### Prerequisites

Install:

- Python 3.11+;
- Node.js 22.12+;
- Git;
- Rust and Microsoft C++ tools for desktop packaging;
- Docker Desktop for sandbox tests; and
- Ollama or an OpenAI-compatible provider for real model responses.

The mock provider works without a model runtime or account.

### Start the application

From the repository root, double-click:

```text
launch.bat
```

Or run:

```powershell
.\launch.bat
```

The launcher creates `.venv`, installs pinned Python dependencies, installs frontend dependencies, builds the React UI, starts the loopback API on an available port, waits for readiness, generates a session token, and opens the authenticated browser UI.

The actual URL and port are printed at startup. The UI and API use the same server at runtime; Vite is not required after the build.

### Startup smoke check

```powershell
.\.venv\Scripts\python.exe scripts\launch.py --smoke
```

This starts the API, verifies health and authenticated repository access, and exits without opening a browser.

## Configuration

Copy the example once:

```powershell
Copy-Item .env.example .env
```

Never commit `.env` or real credentials.

### Core settings

```dotenv
REPOPILOT_DATABASE_PATH=data/repopilot.sqlite3
REPOPILOT_MAX_FILE_BYTES=2000000
REPOPILOT_TASK_TIMEOUT_SECONDS=120
REPOPILOT_MAX_OUTPUT_BYTES=200000
```

### Model settings

```dotenv
REPOPILOT_MODEL_PROVIDER=mock
REPOPILOT_MODEL_BASE_URL=http://127.0.0.1:11434
REPOPILOT_MODEL_API_KEY=
REPOPILOT_PRIMARY_MODEL=
REPOPILOT_FALLBACK_MODEL=
```

Supported providers:

| Provider | Configuration | Network |
|---|---|---|
| `mock` | None | No external call |
| `ollama` | Loopback URL and installed model | Local only |
| `openai_compatible` | HTTPS URL, key, and model | Explicit UI consent |

### Ollama example

```dotenv
REPOPILOT_MODEL_PROVIDER=ollama
REPOPILOT_MODEL_BASE_URL=http://127.0.0.1:11434
REPOPILOT_PRIMARY_MODEL=<installed-model-name>
```

### NVIDIA NIM/OpenAI-compatible example

```dotenv
REPOPILOT_MODEL_PROVIDER=openai_compatible
REPOPILOT_MODEL_BASE_URL=https://integrate.api.nvidia.com/v1
REPOPILOT_MODEL_API_KEY=<set privately>
REPOPILOT_PRIMARY_MODEL=openai/gpt-oss-20b
REPOPILOT_FALLBACK_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b
```

NVIDIA aliases are also accepted:

```dotenv
NVIDIA_API_KEY=<set privately>
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_PRIMARY_MODEL=openai/gpt-oss-20b
NVIDIA_FALLBACK_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b
```

No key is embedded in the application or web bundle. Rotate any credential exposed in chat or logs.

### Sandbox settings

```dotenv
REPOPILOT_SANDBOX_MODE=docker
REPOPILOT_SANDBOX_PYTHON_IMAGE=repopilot-python-tests
REPOPILOT_SANDBOX_NODE_IMAGE=node:22-bookworm-slim
```

Only Docker mode is supported. RepoPilot never silently falls back to host execution.

### Optional embeddings

```dotenv
REPOPILOT_EMBEDDING_MODEL=
REPOPILOT_EMBEDDING_ENDPOINT=http://127.0.0.1:11434
```

Embeddings are disabled unless explicitly configured. The endpoint must be loopback and the model/license must be selected manually.

## Using RepoPilot

### Register and index

1. Start RepoPilot.
2. Enter the absolute path to the root of a Git repository.
3. Select **Register**.
4. Select **Index**.
5. Wait for `ready`.

The target repository must have at least one commit. The original working tree is not modified by indexing.

### Search

Search for:

- function or class names;
- error messages;
- configuration keys;
- imports;
- file names; or
- natural-language terms.

Results show paths, line ranges, excerpts, hashes, commit metadata, and retrieval method. Changed files are rejected as stale until reindexed.

### Investigate

1. Select an indexed repository.
2. Choose **Investigate issue** or **Explain architecture**.
3. Enter a specific request.
4. Select **Run task**.
5. Review the plan, evidence, hypotheses, and response.

Example:

```text
Where is authentication implemented, and which tests exercise it?
```

The mock provider returns deterministic evidence summaries. A real model is required for substantive diagnosis or architecture explanations.

### Clarification

If no matching evidence is found, the workflow pauses. Provide a function name, file path, exact error, or more reproduction detail and select **Resume investigation**. Checkpoint state is stored locally so a restart does not silently discard the task.

### Repository explorer

The explorer displays indexed files, source content, languages, file counts, imports, and syntactic call candidates. Dynamic dispatch, reflection, generated code, and runtime dependency resolution are not fully modeled.

## Architecture

```text
React/Vite or Tauri UI
          │ loopback API + session token
          ▼
FastAPI application ───── Model gateway
          │              mock · Ollama · NIM
          ▼
SQLite / FTS5 / checkpoints
          │
Indexer · Tree-sitter · retrieval · read-only tools
          │
LangGraph: validate → plan → retrieve → analyze → verify
          │
Detached Git worktree → diff hash → approval
          │
Docker sandbox: no network · no secrets · bounded resources
```

Design rules:

- Repository content is untrusted input.
- Model output is data, not permission.
- The UI cannot directly execute model-generated commands.
- Mutations occur only in isolated worktrees until approval.
- Evidence is hash-checked before completion.
- Tasks have concurrency, step, tool-call, output, and time budgets.
- Remote inference requires explicit consent.

## Workflows

### Indexing

The indexer uses Git’s tracked/unignored file list, `.gitignore`, `.repopilotignore`, and RepoPilot policy checks.

Excluded by default:

- `.env` variants, credentials, private keys, and certificates;
- `.git`, virtual environments, `node_modules`, build output, caches, and coverage;
- databases, SQLite files, binary files, symlinks, junctions, hard links; and
- files above `REPOPILOT_MAX_FILE_BYTES`.

Secret-like content is also rejected. This is defense in depth, not a guarantee that every secret format is detected.

The database stores repository metadata, file hashes, FTS5 content, symbols, relationships, task state, events, evidence hashes, patches, tests, and approvals. It uses WAL mode, additive migrations, and a single-instance lock.

### Investigation

The bounded LangGraph workflow:

1. Validates the request.
2. Creates a deterministic read-only plan.
3. Retrieves lexical, symbol, and optional semantic evidence.
4. Pauses for clarification when evidence is absent.
5. Produces observations and hypotheses.
6. Verifies evidence freshness and file hashes.
7. Persists the answer, evidence, hypotheses, events, and verification state.

The mock provider returns deterministic evidence summaries. A real model is needed for substantive diagnosis.

### Patch approval

1. Record the source commit.
2. Create a detached worktree outside the source repository.
3. Apply changes only in that worktree.
4. Calculate the diff hash.
5. Optionally run baseline and patch tests.
6. Display the diff.
7. Require the matching action hash.
8. Recheck the source and worktree.
9. Run `git apply --check` and apply the exact diff.
10. Record approval and remove the temporary worktree.

Approval is rejected if the source, worktree, or diff changed, or if the action was replayed.

### Sandboxed tests

Docker Desktop must be running. Prepare the Python image:

```powershell
docker build -f sandbox/Dockerfile.python -t repopilot-python-tests .
```

Then set `REPOPILOT_SANDBOX_PYTHON_IMAGE=repopilot-python-tests`.

For real repositories, prepare an image containing their pinned dependencies and test tools. RepoPilot does not install dependencies with network access.

The sandbox uses a sanitized source copy, no `.git`, no host secrets, no Docker socket, no network, a non-root UID, dropped capabilities, read-only root filesystem, writable tmpfs, CPU/memory/process limits, bounded output, and timeouts.

Baseline and patch results are compared. A regression means the baseline passes and the patch fails. Passing tests are evidence, not proof. A repair is limited to two attempts.

## API

Protected endpoints require `X-RepoPilot-Token` on the initial browser requests. The launcher creates a new token for each session; after the first valid request, the API also stores it in an HttpOnly same-origin cookie so a normal tab reload does not lose authentication.

### Health and settings

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Application and provider health |
| `GET` | `/settings` | Non-secret runtime settings |
| `GET` | `/model/health` | Probe configured model runtime |

### Repositories

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/repositories` | List repositories |
| `POST` | `/repositories` | Register or refresh a repository |
| `GET` | `/repositories/{id}` | Metadata |
| `POST` | `/repositories/{id}/index` | Synchronous index |
| `POST` | `/repositories/{id}/index?background=true` | Background index |
| `POST` | `/repositories/{id}/index/cancel` | Cancel indexing |
| `GET` | `/repositories/{id}/index-status` | Index status |
| `POST` | `/repositories/{id}/search` | Evidence search |
| `GET` | `/repositories/{id}/files` | Safe file list |
| `GET` | `/repositories/{id}/file` | Bounded file read |
| `GET` | `/repositories/{id}/symbols` | Symbol definitions |
| `GET` | `/repositories/{id}/references` | Reference candidates |
| `GET` | `/repositories/{id}/structure` | Languages and relationships |
| `GET` | `/repositories/{id}/git-status` | Git status |
| `GET` | `/repositories/{id}/commits` | Recent commits |
| `GET` | `/repositories/{id}/tests` | Test-like files |
| `POST` | `/repositories/{id}/embeddings` | Local embedding cache |

### Tasks

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/tasks` | Task history |
| `POST` | `/tasks` | Explain, investigate, or patch |
| `GET` | `/tasks/{id}` | Task state |
| `GET` | `/tasks/{id}/events` | Workflow events |
| `GET` | `/tasks/{id}/evidence` | Task evidence |
| `GET` | `/tasks/{id}/diff` | Diff and approval state |
| `POST` | `/tasks/{id}/resume` | Resume clarification |
| `POST` | `/tasks/{id}/cancel` | Cancel task |
| `POST` | `/tasks/{id}/tests` | Run allowlisted test |
| `GET` | `/tasks/{id}/tests` | Test results |
| `POST` | `/tasks/{id}/repair` | Repair verified regression |
| `POST` | `/tasks/{id}/approval` | Reject/apply matching diff |
| `GET` | `/tasks/{id}/report` | Markdown report |

Example:

```powershell
$headers = @{ "X-RepoPilot-Token" = "session-token" }
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:54126/repositories" -Headers $headers
```

## Security

Controls include loopback binding, per-launch authentication, localhost origin checks, request-size limits, Pydantic validation, canonical path checks, traversal/symlink/junction/hard-link blocking, secret redaction, no arbitrary host shell, Git hook/filter suppression, isolated worktrees, immutable approval hashes, Docker network isolation, and bounded budgets.

Residual risks remain: repositories can contain hostile scripts or dependencies; Docker is defense in depth; secret detection is heuristic; and model answers can be wrong. Do not run untrusted repositories on sensitive machines without appropriate isolation.

## Development

```powershell
py -3.14 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
python -m pip install -e ".[dev]"
cd web
npm ci
npm run build
```

Run the API directly from the repository root:

```powershell
.venv\Scripts\python.exe -m uvicorn repopilot_api.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

Run Vite hot reload:

```powershell
cd web
npm run dev -- --host 127.0.0.1
```

Lint and format:

```powershell
.venv\Scripts\python.exe -m ruff check apps tests scripts
.venv\Scripts\python.exe -m ruff format --check apps tests scripts
```

Optional pre-commit:

```powershell
python -m pip install pre-commit
pre-commit install
```

## Testing and evaluation

Backend and security tests:

```powershell
.venv\Scripts\python.exe -m pytest -q -m "not browser"
```

These cover registration, indexing, retrieval, Tree-sitter relationships, checkpoints, path policy, redaction, stale evidence, cancellation, approval replay, model protocols, semantic cache behavior, and evaluation metrics.

Browser test:

```powershell
.venv\Scripts\python.exe -m playwright install chromium
.venv\Scripts\python.exe -m pytest -q -m browser
```

The browser flow covers registration, indexing, search, investigation, manual patch creation, and rejection without modifying the original source.

Docker test:

```powershell
docker build -f sandbox/Dockerfile.python -t repopilot-python-tests .
.venv\Scripts\python.exe -m pytest -q -m docker
```

If Docker Desktop or the prepared image is unavailable, the live Docker test is skipped and must not be interpreted as passing sandbox evidence.

Retrieval evaluation:

```powershell
.venv\Scripts\python.exe scripts\run_evaluation.py
```

The synthetic benchmark contains 25 queries over 10 permissively licensed fixture modules. It reports Recall@5, MRR, p50 latency, and p95 latency to `evals/reports/retrieval.json` and `evals/reports/retrieval.md`. It does not claim diagnosis accuracy, patch correctness, or arbitrary production-repository performance.

Packaged backend smoke:

```powershell
.venv\Scripts\python.exe scripts\smoke_packaged.py
```

Desktop lifecycle smoke:

```powershell
.venv\Scripts\python.exe scripts\smoke_desktop.py
```

The packaged checks verify bundled UI assets, backend startup, repository registration, indexing, investigation, the Tauri window, and child-process shutdown.

## Desktop packaging

Build the installer:

```powershell
.\build-desktop.bat
```

The build installs frontend dependencies, builds web assets, packages the backend with PyInstaller, includes license notices, builds Tauri, creates an NSIS installer, and writes checksums.

Output: `desktop/src-tauri/target/release/bundle/nsis/RepoPilot_0.1.0_x64-setup.exe` and `desktop/checksums.json`.

The installer is unsigned. Signing requires a publisher certificate. Git, Docker, model runtimes, model weights, and provider credentials are not bundled. Packaged local data is stored under the Tauri identifier `dev.repopilot.desktop` in the Windows local-application-data directory.

Generate the dependency/license inventory:

```powershell
.venv\Scripts\python.exe scripts\license_inventory.py
```

This updates `docs/THIRD_PARTY_NOTICES.md` and copies dependency license texts under `docs/licenses/`. It is an inventory, not legal approval; model licenses require separate review.

## Structure

```text
RepoPilot - AI Developer OS/
├── apps/api/repopilot_api/     # FastAPI, indexing, models, tasks, workflows
├── desktop/                    # Tauri 2 shell and packaging
├── docs/                       # ADRs, status, notices, licenses
├── evals/                      # Fixtures, datasets, reports
├── scripts/                    # Launch, build, evaluation, smoke checks
├── sandbox/                    # Docker image guidance
├── tests/                      # Unit, integration, security, browser, Docker
├── web/                        # React/Vite UI
├── ai_developer_os_plan/       # Original product and implementation plan
├── build-desktop.bat
├── launch.bat
├── LICENSE
├── pyproject.toml
└── requirements.lock
```

## Limitations

RepoPilot does not promise guaranteed fixes for arbitrary repositories, complete language support, a complete dynamic call graph, perfect secret detection, perfect prompt-injection resistance, perfect Docker isolation, automatic dependency installation in sandboxes, automatic merging into dirty trees, hunk-level diff approval, automatic deployment, remote Git operations, cloud collaboration, billing, mandatory paid model access, or signed installers without publisher credentials.

The current benchmark is synthetic and small. Its results must not be presented as production diagnosis or patch-quality results.

## Roadmap extensions

Possible future work includes side-by-side/hunk-level diff review, richer language-specific reference resolution, larger licensed evaluation corpora, model resource dashboards, additional sandbox images, installer signing/release CI, and optional remote Git integrations behind explicit approval.

## License

RepoPilot is released under the MIT License. See [`LICENSE`](LICENSE).

Third-party components and model weights have separate licenses. See [`docs/THIRD_PARTY_NOTICES.md`](docs/THIRD_PARTY_NOTICES.md) and review model terms independently before redistribution or commercial use.
