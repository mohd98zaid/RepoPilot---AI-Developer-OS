# RepoPilot — AI Developer OS
## Complete Product, Architecture, Engineering, and Delivery Plan

**Version:** 1.0  
**Status:** Proposed implementation blueprint  
**Principle:** Free/open-source-first; no paid SaaS is required for the local MVP.  
**Primary target:** Windows desktop developer environment, with an architecture that can later support Linux/macOS.

---

## 1. Executive summary

RepoPilot is an AI Developer OS: a developer-focused application that understands a code repository, investigates bugs, explains architecture, proposes changes, runs tests in a controlled environment, verifies outcomes, and presents a reviewable patch. It is an application layer on top of the existing operating system, not a new kernel or replacement OS.

The product must do more than generate code. Its core loop is:

**Understand → Plan → Inspect → Retrieve evidence → Propose change → Execute in isolation → Test → Verify → Present diff for human approval.**

The first release focuses on local repositories and three workflows:
1. Repository onboarding and architecture explanation.
2. Issue investigation with evidence-linked hypotheses.
3. Sandboxed patch proposal with test execution and diff review.

The product should not auto-merge code, access host credentials, or execute arbitrary model-generated commands on the user's machine.

## 2. Free/open-source commitment

### Product constraints
- No paid SaaS dependency is required for the local MVP.
- Prefer OSI-approved/open-source software and self-hosted components.
- NVIDIA hosted inference is **not required** for this all-free/open-source build. Hosted APIs can have quotas, changing terms, and non-open service components. Use local inference by default.
- All third-party dependencies must be checked for current license, maintenance, Windows support, and model license before adoption.
- “Free to use” and “open source” are not interchangeable. A model may have free weights but restrictions; verify its license.

### Practical trade-off
Local LLM inference avoids per-request API fees but is limited by RAM, VRAM, model size, speed, and quality. Start with a model that runs acceptably on the target machine. The architecture must support swapping models without changing workflows.

## 3. Product vision and differentiators

### Vision
A local-first AI engineering environment that can reason over a real repository, use tools with bounded permissions, produce reproducible evidence, and assist developers through the full issue-to-patch workflow.

### Differentiators
- Repository-aware, symbol-aware retrieval rather than only chat over files.
- Agent execution with explicit state, budgets, checkpoints, and stop conditions.
- Test execution in isolated workspaces.
- Verifiable results: file references, diffs, exact commands, exit codes, and test output.
- Human approval for modifications and all remote side effects.
- Repeatable evaluations and transparent limitations.
- Local-first privacy and no mandatory paid model API.

## 4. Target users and use cases

### Primary users
- Developers onboarding to unfamiliar repositories.
- Maintainers triaging bugs and issues.
- Engineers writing tests or fixing regressions.
- Technical leads reviewing architecture and technical debt.
- Students learning codebases and debugging workflows.

### MVP use cases
- “Explain the architecture of this repository.”
- “Where is authentication implemented? Show relevant files and call sites.”
- “Investigate this error log and identify likely causes.”
- “Find the tests related to this function.”
- “Propose a fix for this issue in a separate worktree.”
- “Run the relevant tests and explain the failures.”
- “Summarize the patch and identify untested risks.”

## 5. Non-goals for MVP

- Autonomous merge or deployment.
- Unrestricted shell, network, or browser access.
- Guaranteed fixes for arbitrary repositories.
- Full IDE replacement.
- Support for every programming language/build system.
- Cloud team collaboration or commercial billing.
- Automatic use of proprietary services.
- Model training/fine-tuning as a prerequisite.

## 6. User experience

### Main screens
1. **Home:** recent repositories, active runs, model health, setup checks.
2. **Repository explorer:** file tree, branch/commit, clean/dirty status, indexing progress.
3. **Chat/task panel:** user request, plan, evidence, tool events, final answer.
4. **Plan review:** steps, tools, expected changes, risk labels, budget.
5. **Diff review:** side-by-side diff, changed-file list, patch summary, approve/reject.
6. **Test panel:** commands, exit codes, duration, test summary, logs.
7. **Run history:** prior investigations, patches, failures, model/workflow version.
8. **Settings:** model endpoint, context limit, permissions, sandbox, ignored files, budgets.

### UX rules
- Always show whether the model is generating, a tool is running, approval is required, or a task has failed.
- Separate “proposed” from “executed” actions.
- Show evidence links to file paths and line ranges.
- Do not show a green “success” state unless the expected result was checked.
- Preserve user edits and existing uncommitted changes.
- Make cancellation visible and effective.

## 7. Recommended free/open-source technology stack

| Layer | Recommendation | Role | License note |
|---|---|---|---|
| Desktop shell | Tauri 2 + React + TypeScript | Cross-platform UI shell | Tauri/MIT or Apache-2.0 ecosystem; verify dependency licenses |
| UI components | shadcn/ui + Tailwind CSS | Accessible reusable UI | Mostly MIT; audit installed packages |
| Backend | Python + FastAPI + Pydantic | Local API and typed schemas | Open source |
| Agent orchestration | LangGraph | Stateful workflow graph | Open source; verify current package license |
| Model/tool integrations | LangChain core and selected integrations | Chat models, prompts, tool schemas | Open source; audit optional integrations |
| Local model runtime | Ollama or llama.cpp | Run models locally | Open source; model weights have separate licenses |
| Code parsing | tree-sitter and language-specific parsers | Syntax/symbol indexing | Open source; audit grammar licenses |
| Local metadata DB | SQLite | Runs, repository metadata, approvals | Public domain |
| Vector retrieval | PostgreSQL + pgvector or Qdrant local | Embedding search | Open source; evaluate operational footprint |
| Lexical search | SQLite FTS5 initially | Exact identifiers and keyword search | Included with SQLite; build configuration can vary |
| Embeddings | Local embedding model via sentence-transformers or a compatible runtime | Vector representation | Library/model licenses vary |
| Git operations | Git CLI via a strict wrapper | Branches, worktrees, diffs | Open source |
| Test runner | Existing repo test tools in sandbox | Verification | Depends on project |
| Container isolation | Docker Engine where licensing/setup fits, or Podman | Sandboxed execution | Check current Windows and distribution requirements |
| Observability | OpenTelemetry + local JSONL logs; optional Langfuse self-hosting | Traces and metrics | Open source components; self-hosting costs hardware/time |
| API/UI tests | pytest, httpx, Playwright | Automated testing | Open source |
| Packaging | Tauri bundler; GitHub Actions optional | Desktop builds and CI | Local builds need no hosted CI |

### Keep the initial stack smaller
For the first working vertical slice use:
- Tauri + React UI
- FastAPI
- LangGraph
- Ollama or llama.cpp
- SQLite + FTS5
- Git CLI
- pytest
- Docker/Podman sandbox when available

Add pgvector/Qdrant, a dedicated embedding service, and advanced tracing only when the baseline shows a need. Do not deploy every component on day one.

## 8. System architecture

### High-level components

```text
┌─────────────────────────────────────────────────────┐
│ Tauri Desktop UI                                     │
│ Repository / Task Plan / Evidence / Diff / Test Logs│
└──────────────────────┬──────────────────────────────┘
                       │ local authenticated API
┌──────────────────────▼──────────────────────────────┐
│ FastAPI Application                                  │
│ Auth/session · Task API · Permissions · Run history  │
└──────────────┬──────────────────────────┬────────────┘
               │                          │
┌──────────────▼────────────┐  ┌──────────▼────────────┐
│ LangGraph Runtime         │  │ Repository Indexer    │
│ Plan/Inspect/Patch/Test   │  │ Parse/Symbols/FTS     │
└──────────────┬────────────┘  └──────────┬────────────┘
               │                          │
┌──────────────▼──────────────────────────▼────────────┐
│ Tool Gateway + Policy Engine                         │
│ File read/search · Git · tests · patch · approval    │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│ Isolated Worktree / Sandbox                          │
│ Limited FS · Resource limits · No secrets · Network  │
│ disabled by default                                  │
└──────────────────────────────────────────────────────┘

Shared services: local model runtime, SQLite/FTS, vector index (optional),
structured logs, evaluation harness, artifact store.
```

### Architecture rules
- The UI never calls the model directly with secrets.
- All tools are registered through one policy-enforcing gateway.
- Model output is untrusted data, not executable authority.
- Repository reads and writes use canonical path checks.
- Model-generated shell commands are not executed as-is.
- All mutating work occurs in a separate worktree or sandbox.
- Every task has a maximum step count, tool-call count, runtime, and token/cost budget.
- A run is complete only after verification or an explicit unresolved state.

## 9. Main workflows

### Workflow A — Repository onboarding
1. Register local repository.
2. Detect Git status and current commit.
3. Respect `.gitignore` and a product-level ignore list.
4. Exclude secrets, binaries, generated folders, vendored dependencies, and oversized files.
5. Parse manifests, entry points, modules, tests, and configuration.
6. Build lexical and symbol indexes.
7. Optionally embed code/document chunks.
8. Generate architecture map with file evidence.
9. Verify every cited path/line exists at the indexed commit.
10. Save index version and report.

### Workflow B — Issue investigation
1. Validate request and repository scope.
2. Planner converts request into bounded investigation questions.
3. Retrieve matching files, symbols, tests, docs, and Git metadata.
4. Inspect relevant source snippets and call sites.
5. Optionally inspect user-provided logs.
6. Produce a list of hypotheses, each with evidence and a test to distinguish it.
7. Ask the user for missing reproduction details when necessary.
8. Stop without changing code unless patch mode is explicitly requested.

### Workflow C — Patch proposal
1. Confirm the repository snapshot and current working tree.
2. Create a separate Git worktree or isolated clone from a recorded base commit.
3. Generate a minimal patch in that isolated location.
4. Validate diff scope and reject paths outside repository root.
5. Select only approved test commands from detected project configuration or user approval.
6. Run tests in a sandbox with resource limits.
7. If failure is attributable to the proposed change, allow a small bounded repair loop.
8. Run relevant tests again.
9. Verify diff, test results, and expected behavior.
10. Show diff and require user approval before applying/exporting.
11. Never auto-merge or deploy in MVP.

## 10. LangGraph design

### Suggested graph nodes
- `validate_request`
- `load_repository_snapshot`
- `classify_task`
- `plan_investigation`
- `retrieve_code_context`
- `inspect_symbols_and_tests`
- `form_hypotheses`
- `request_user_input` (interrupt/checkpoint)
- `create_isolated_worktree`
- `propose_patch`
- `validate_patch_scope`
- `select_tests`
- `run_tests`
- `analyze_test_results`
- `repair_patch` (bounded)
- `verify_result`
- `await_human_approval`
- `finalize_report`
- `cleanup`

### State schema
```python
class DeveloperTaskState(TypedDict):
    task_id: str
    repository_id: str
    base_commit: str
    task_type: Literal["explain", "investigate", "test", "patch"]
    user_request: str
    plan: list[dict]
    evidence: list[dict]
    hypotheses: list[dict]
    worktree_path: str | None
    diff_ref: str | None
    test_results: list[dict]
    approval_status: Literal["not_required", "pending", "approved", "rejected"]
    step_count: int
    tool_call_count: int
    status: str
    error: dict | None
```

### Graph controls
- Maximum planner revisions: 2.
- Maximum patch-repair iterations: configurable, default 2.
- Maximum tool calls per run: configurable.
- Maximum wall-clock runtime: configurable.
- Every node has timeout and typed error output.
- Retry only transient errors; do not retry permission failures as if they were transient.
- Persist state using a local checkpointer; keep repository data and run state versioned.
- Human approval must be an external UI event associated with the exact diff/action hash.

## 11. Repository intelligence and RAG

### Why plain vector RAG is insufficient
Codebases rely heavily on exact identifiers, imports, call sites, inheritance, and test relationships. Embeddings may miss exact symbol matches. Use hybrid retrieval.

### Indexing pipeline
1. Enumerate files using ignore rules.
2. Detect language and parser.
3. Extract symbols and line ranges using tree-sitter or language-specific tooling.
4. Extract imports, call sites where feasible, manifests, and test mappings.
5. Store whole-file metadata and symbol-level chunks.
6. Index identifiers and text in SQLite FTS5.
7. Optionally generate embeddings for semantic retrieval.
8. Keep commit hash and file hash on every record.
9. Incrementally re-index changed files.
10. Delete stale chunks when files are removed or renamed.

### Retrieval pipeline
- Exact identifier search first for named symbols.
- Lexical search for error strings, imports, and configuration keys.
- Vector search for conceptual similarity.
- Graph/relationship expansion for imports, callers, and tests where available.
- Merge/deduplicate candidates.
- Optional reranking.
- Apply repository and commit filters.
- Return file path, line range, symbol, commit hash, and excerpt.

### Citation contract
Every code evidence item should have:
`repository_id, commit_hash, path, line_start, line_end, symbol_name, excerpt_hash, retrieval_method`.

Before showing a citation, verify the file and line range still match the indexed commit. If the working tree has changed, indicate that the evidence may be stale.

## 12. Model strategy — local and free-first

### Default approach
Use a local inference runtime:
- **Ollama:** simpler developer experience and local HTTP API.
- **llama.cpp:** more control over GGUF quantized models and CPU/GPU offload.

These runtimes are open source, but model licenses differ. Choose a code-capable model that fits the user's hardware, context window, and license requirements. Do not hardcode a model name into the graph.

### Model roles
- Fast model: intent classification, query rewriting, simple summaries.
- Stronger code model: issue analysis and patch generation.
- Embedding model: local vector embeddings.
- Optional reranker: local reranking only if evaluation improves enough to justify latency.

A single model can serve all roles initially. Avoid multi-model routing until benchmarks show value.

### NVIDIA note
This plan uses local inference to satisfy the free/open-source requirement. NVIDIA-hosted API endpoints may be convenient but are not a necessary dependency and may have quotas or licensing conditions. NVIDIA hardware acceleration can be used if compatible drivers/runtime and hardware are available, but it is not assumed.

### Hardware reality
On a laptop with limited VRAM, use a quantized model and a smaller context window; CPU offload may work but can be slow. Benchmark first. A model that runs locally is not automatically good at code editing. Keep a test set of real tasks and compare models empirically.

## 13. Security and sandboxing

### Threat model
Assume:
- Repository code and documentation may contain prompt injection.
- Issues/logs may contain malicious instructions.
- Generated code may be destructive or exfiltrate data.
- Test scripts may execute arbitrary commands.
- Dependencies may run install hooks.
- A malicious repository may attempt to access host files or network.
- Model output may contain invalid paths or unsafe commands.

### Required controls
- Do not mount user home, SSH keys, cloud credentials, browser profiles, or container sockets into sandbox.
- Disable network by default in test containers; allow only explicit destinations when needed.
- Use non-root execution, read-only base image, ephemeral writable worktree, resource quotas, and process/time limits.
- Use command allowlists; never execute arbitrary model-generated shell strings on the host.
- Inspect test/build scripts and dependency install steps before execution.
- Restrict file writes to a dedicated worktree.
- Canonicalize paths and prevent path traversal and symlink escape.
- Enforce permissions in Python/application code, not in prompts.
- Require approval for remote Git operations and all writes outside sandbox.
- Store only redacted tool output in logs.
- Clean up sandboxes on completion/cancellation.
- Keep sandboxing as a defense-in-depth layer; containers are not a perfect security boundary.

## 14. Data model

Use SQLite for local MVP, with migrations. Suggested tables:

- `repositories(id, display_name, local_path, default_branch, current_commit, created_at)`
- `repository_snapshots(id, repository_id, commit_hash, index_version, indexed_at)`
- `files(id, snapshot_id, path, file_hash, language, size_bytes, status)`
- `symbols(id, snapshot_id, file_id, name, kind, start_line, end_line, signature)`
- `chunks(id, snapshot_id, file_id, start_line, end_line, text, embedding_ref)`
- `tasks(id, repository_id, task_type, request, status, workflow_version, model_id, created_at, finished_at)`
- `task_events(id, task_id, seq, event_type, timestamp, redacted_payload)`
- `evidence(id, task_id, file_id, commit_hash, start_line, end_line, excerpt_hash)`
- `patches(id, task_id, base_commit, diff_hash, artifact_path, status)`
- `test_runs(id, task_id, command_id, exit_code, duration_ms, output_path)`
- `approvals(id, task_id, action_hash, status, decided_at)`
- `artifacts(id, task_id, path, content_hash, media_type, created_at)`

Never store raw secrets. Add schema versioning and data migrations from the beginning.

## 15. API contract (local service)

- `GET /health` — application and model-runtime health (no secrets).
- `POST /repositories` — register a repository path after user selection.
- `GET /repositories/{id}` — repository status.
- `POST /repositories/{id}/index` — start indexing.
- `GET /repositories/{id}/index-status` — indexing status.
- `POST /tasks` — create an explain/investigate/test/patch task.
- `GET /tasks/{id}` — task status and summary.
- `GET /tasks/{id}/events` — stream safe progress events.
- `GET /tasks/{id}/evidence` — retrieve evidence references.
- `GET /tasks/{id}/diff` — retrieve a patch diff.
- `POST /tasks/{id}/approval` — approve/reject an exact pending action.
- `POST /tasks/{id}/cancel` — cancel a run.
- `GET /tasks/{id}/tests` — list test outcomes.
- `GET /artifacts/{id}` — retrieve an authorized artifact.

API rules:
- Pydantic validation on every input.
- No arbitrary local path from unauthenticated remote requests.
- Bind local API to loopback by default and use a per-session token or equivalent local authentication.
- Use size limits, request timeouts, and consistent error codes.
- Approval references a specific immutable action/diff hash.

## 16. Repository and file handling

- Respect `.gitignore`, product ignore file, and user-configured excludes.
- Exclude `.env`, private keys, tokens, credentials, database dumps, large binary files, build outputs, and dependency folders by default.
- Detect likely secrets with an open-source scanner before indexing or sending context to a model.
- Never silently upload source code to an external endpoint.
- For hosted inference, show a clear disclosure and require opt-in.
- Track file hashes to prevent stale index results.
- Do not alter the original working tree during patch generation.

## 17. Testing strategy

### Unit tests
- Path validation and canonicalization.
- Ignore/exclude logic.
- Parser output and line mappings.
- Tool argument schemas.
- Permission decisions.
- State transitions and retry classification.
- Patch scope validation.
- Secret redaction.

### Integration tests
- FastAPI task lifecycle.
- SQLite migrations and transaction behavior.
- Git worktree creation/cleanup.
- Local model unavailable/timeout behavior.
- Index update after file change.
- Test runner in a sandbox.
- Approval pause/resume.

### Adversarial/security tests
- Prompt injection in README/source comments.
- Malicious test command attempts.
- Path traversal and symlink escapes.
- Repository attempting to read host credentials.
- Cross-repository evidence leakage.
- Cancellation during a long-running process.
- Duplicate approval submissions.
- Malformed model JSON and oversized output.

### End-to-end tests
- Repository onboarding.
- Architecture explanation.
- Issue investigation.
- Patch proposal and test execution.
- Rejected approval leaves original repository unchanged.
- Model outage yields a clear error and does not perform actions.

## 18. Evaluation plan

Create a small benchmark before tuning. Start with 25–50 tasks from permissively licensed repositories or synthetic sample repos. Expand after the workflow is stable.

### Dataset fields
- Task ID and repository commit.
- User issue/question.
- Expected relevant files/symbols.
- Expected behavior or accepted answer.
- Tests to run.
- Allowed tools.
- Unsafe actions that must not occur.
- Human-reviewed rubric.

### Metrics
- Relevant-file recall@5 and MRR.
- Diagnosis accuracy and evidence support.
- Patch test pass rate.
- Regression rate on existing tests.
- Patch size and unrelated changes.
- Correct tool-call rate.
- Permission policy violations.
- Task completion rate.
- p50/p95 latency.
- Memory/VRAM use and local inference throughput.

Never claim that a patch is correct solely because tests pass. Report benchmark scope and failure categories.

## 19. Performance and cost controls

- Use local inference by default to avoid per-token hosted API fees.
- Cache repository summaries by commit hash.
- Cache embeddings for unchanged content.
- Retrieve bounded context rather than entire repositories.
- Use smaller models for classification and larger ones only for complex tasks when multiple models are configured.
- Cap output tokens and graph iterations.
- Stop work when user cancels or budget is exhausted.
- Make indexing incremental.
- Measure CPU/RAM/VRAM and latency on the target laptop.
- Note that hardware, electricity, disk, and development time are still costs.

## 20. Implementation roadmap

### Milestone 0 — scope and engineering setup (Days 1–2)
- Create repository and license policy.
- Write PRD, architecture, threat model, and decision log.
- Define supported OS, languages, and initial workflows.
- Establish code formatting, linting, tests, and CI.
- Add `.env.example` with no real secrets.

**Exit:** clean project scaffold and decisions recorded.

### Milestone 1 — vertical slice (Days 3–5)
- Build FastAPI app and health endpoint.
- Connect local model runtime.
- Create simple UI chat/task panel.
- Implement one read-only repository tool.
- Add structured response and visible tool events.

**Exit:** user can ask a repository question and see a grounded file reference.

### Milestone 2 — repository indexing (Days 6–10)
- Git status and file enumeration.
- Ignore and secret exclusion.
- Tree-sitter parsing for selected languages.
- SQLite metadata + FTS5 search.
- Evidence references with line numbers.
- Incremental index update.

**Exit:** exact identifier and keyword search works on a sample repo.

### Milestone 3 — LangGraph investigation workflow (Days 11–15)
- Define typed graph state.
- Add classification, planning, retrieval, hypothesis, and final report nodes.
- Add time/step/tool budgets.
- Add checkpointing and cancellation.
- Build golden questions.

**Exit:** repeatable read-only investigation tasks with evidence.

### Milestone 4 — isolated patch workflow (Days 16–22)
- Create separate worktree.
- Add patch generation in worktree.
- Validate diff paths and scope.
- Add sandboxed test execution.
- Display diff and test results.
- Add approval/rejection UI.

**Exit:** no changes are applied to original worktree; tests and approval state are traceable.

### Milestone 5 — reliability and security (Days 23–27)
- Threat-model test cases.
- Permission checks and local API authentication.
- Timeouts/retries/cancellation.
- Secret redaction.
- Sandbox failure injection.
- Evaluation dashboard/report.

**Exit:** documented test results and no known critical issue in the MVP threat-test suite.

### Milestone 6 — packaging and portfolio release (Days 28–30)
- Build desktop installer.
- Write setup instructions and supported model list.
- Add architecture diagrams and demo video.
- Publish evaluation results and limitations.
- Tag release and attach checksums.

**Exit:** reproducible install and demo.

This is a planning estimate for a focused MVP, not a guarantee; adjust based on model performance and sandbox complexity.

## 21. Repository structure

```text
repopilot/
├── apps/
│   ├── desktop/                 # Tauri + React UI
│   └── api/                     # FastAPI application
├── packages/
│   ├── contracts/               # Pydantic/API schemas
│   ├── model_gateway/            # Local model adapters
│   ├── repo_indexer/             # Files, symbols, FTS, optional embeddings
│   ├── retrieval/                # Hybrid retrieval and ranking
│   ├── agent_runtime/            # LangGraph workflows and state
│   ├── tool_gateway/             # Permissions and typed tools
│   ├── sandbox/                  # Worktree/container/test runner
│   └── evaluation/               # Dataset runner and metrics
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   └── e2e/
├── evals/
│   ├── datasets/
│   ├── rubrics/
│   └── reports/
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── THREAT_MODEL.md
│   ├── ADRs/
│   └── USER_GUIDE.md
├── scripts/
├── .github/workflows/
├── .env.example
├── LICENSE
└── README.md
```

## 22. Definition of done

A feature is done only when:
- Its requirements and permissions are documented.
- Input/output schemas are typed and validated.
- Unit and integration tests exist.
- Errors and cancellation are handled.
- Logs do not expose secrets.
- Relevant evaluation cases pass.
- User-facing status and limitations are clear.
- Documentation and migration notes are updated.
- It has been tested on the supported Windows environment.

## 23. Open-source and license checklist

- Choose a project license, such as MIT or Apache-2.0, after considering patent and contribution needs.
- Check every dependency's license and attribution obligations.
- Check model weight licenses separately from runtime licenses.
- Do not redistribute model weights unless permitted.
- Use permissively licensed sample repositories and datasets.
- Include third-party notices.
- Keep optional dependencies isolated.
- Pin versions and review security advisories.
- Do not claim all components are open source without verifying their licenses.

## 24. Release acceptance criteria

- Installs and runs locally without a paid SaaS account.
- Can use a locally hosted model.
- Can index a supported repository and answer with verified file references.
- Can investigate a benchmark issue without modifying the source repository.
- Can propose a patch in a separate worktree.
- Can run approved tests in a restricted environment.
- Can pause for approval and reject safely.
- Can cancel a run and clean up workers.
- Has unit/integration/security tests and published evaluation methodology.
- Has documented limitations and reproducible setup instructions.

## 25. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Local model is weak or slow | Benchmark multiple license-compatible models; allow provider/runtime adapters |
| Context is incomplete | Hybrid retrieval, symbol graph, tests/call-site retrieval |
| Model creates unsafe patch | Isolated worktree, test sandbox, diff review, no auto-merge |
| Tests execute malicious code | Sandbox, no secrets, no network by default, resource limits |
| Index becomes stale | Commit/file hashes and incremental re-indexing |
| Free dependencies change | Pin versions, license review, replaceable interfaces |
| Scope expands too much | Three MVP workflows; defer IDE replacement and remote collaboration |
| Costs emerge despite free software | Document hardware, storage, electricity, and maintenance costs |

## 26. CV and portfolio presentation

After implementation, present measurable results only:
- Number of repositories/files indexed.
- Relevant-file recall@5 on a defined benchmark.
- Patch test pass rate and regression rate.
- Median/p95 task time on specified hardware.
- Percentage of unsafe actions correctly blocked in test cases.
- Memory/VRAM footprint and model configuration.

Example CV description to adapt only after the work exists:

**RepoPilot — Local-First AI Developer OS**  
*Python, FastAPI, LangGraph, LangChain, tree-sitter, SQLite FTS5, local LLM inference, Git worktrees, Docker/Podman, React/Tauri*

- Built a repository-aware AI engineering environment for codebase exploration, issue investigation, and sandboxed patch proposals.
- Implemented hybrid code retrieval using symbol/identifier search and semantic retrieval, with commit-aware file/line evidence.
- Orchestrated bounded LangGraph workflows with checkpointing, approval gates, tool permissions, and test verification.
- Developed isolated patch/test execution with audit trails and automated safety checks.
- Evaluated retrieval, patch outcomes, latency, and unsafe-action prevention on a versioned benchmark.

Do not use these bullets as claims until the relevant features and measurements have been completed.

## 27. Final recommendation

Build the local-only vertical slice first: **repository indexing + evidence-backed investigation + local LLM + safe read-only tools**. Add patch generation only after evidence quality and repository isolation are dependable. Then add sandboxed tests and approval-gated changes. This sequence keeps the project free/open-source-first while giving it a credible path toward a production-grade AI developer environment.
