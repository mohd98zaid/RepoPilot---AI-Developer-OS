# Architecture — RepoPilot AI Developer OS

## 1. Design principles
- Local-first by default.
- Model output is untrusted.
- Typed tools only.
- Explicit state and bounded execution.
- Read-only before write capabilities.
- Evidence is commit-aware.
- Mutations occur in isolated worktrees.
- No paid API dependency in the MVP.

## 2. Component map
- Desktop UI: Tauri + React/TypeScript.
- API: FastAPI + Pydantic.
- Agent runtime: LangGraph.
- Model gateway: Ollama or llama.cpp adapter; LangChain integration.
- Indexer: file enumerator, tree-sitter parsers, symbol extractor.
- Search: SQLite FTS5, optional embeddings/vector store.
- Tool gateway: permissions, path checks, tool schemas, audit.
- Sandbox manager: worktree and container lifecycle.
- Persistence: SQLite.
- Evaluation: Python test harness and labeled task dataset.

## 3. Request flow
1. UI submits task request.
2. API validates request and repository scope.
3. Runtime creates task state and loads repository snapshot.
4. Planner chooses a supported workflow.
5. Retrieval returns evidence under repository/commit filters.
6. Agent may call only registered tools.
7. Tool gateway validates schema and permission.
8. Mutating workflows use an isolated worktree.
9. Test runner runs approved commands inside sandbox.
10. Verifier checks outputs.
11. UI receives final state, evidence, artifacts, and errors.

## 4. LangGraph state
State includes task ID, repository ID, base commit, task type, request, plan, evidence, hypotheses, worktree, diff, test results, approval status, step count, tool count, status, and error.

## 5. Graph
`validate -> snapshot -> classify -> plan -> retrieve -> inspect -> hypotheses -> [clarify] -> [create worktree -> patch -> validate diff -> tests -> bounded repair] -> verify -> approval -> finalize -> cleanup`

The patch branch is only entered after explicit user request. Approval is tied to a specific diff/action hash.

## 6. Retrieval
- Exact identifier and symbol search.
- FTS5 lexical search.
- Optional embedding search.
- Relationship expansion for imports/callers/tests.
- Deduplicate, rerank if beneficial, and return file/line/commit metadata.
- Revalidate references before displaying.

## 7. Data storage
SQLite tables for repositories, snapshots, files, symbols, chunks, tasks, events, evidence, patches, test runs, approvals, and artifacts. Use migrations. Optional pgvector/Qdrant is deferred until needed.

## 8. Local model interface
A single internal interface supports:
- chat completion
- structured output
- tool calling when supported
- streaming
- timeout/error reporting
- model metadata

Runtime adapters should hide Ollama/llama.cpp specifics. Verify model license and capabilities separately.

## 9. Sandbox
Use a separate Git worktree or clone and a restricted container. Do not mount secrets, home directory, SSH keys, or container socket. Disable network by default. Set CPU/memory/time limits and clean up on cancellation. Containers are defense-in-depth, not a perfect security boundary.

## 10. API
- `GET /health`
- `POST /repositories`
- `POST /repositories/{id}/index`
- `GET /repositories/{id}/index-status`
- `POST /tasks`
- `GET /tasks/{id}`
- `GET /tasks/{id}/events`
- `GET /tasks/{id}/evidence`
- `GET /tasks/{id}/diff`
- `POST /tasks/{id}/approval`
- `POST /tasks/{id}/cancel`
- `GET /tasks/{id}/tests`

Bind local API to loopback by default and require local session authorization.

## 11. Security boundaries
- Model cannot grant permissions.
- Tool gateway enforces permissions.
- Repository content is untrusted.
- Path canonicalization and symlink checks are mandatory.
- No arbitrary shell execution on host.
- No network in sandbox unless explicitly configured.
- Secrets are excluded from index and model context.
- All side effects are auditable.

## 12. Failure handling
- Model timeout: stop or retry within budget.
- Invalid structured output: one bounded repair/parse attempt, then fail safely.
- Index mismatch: re-index changed files.
- Test timeout: terminate sandbox process tree.
- Approval rejected: do not apply patch.
- Cancellation: stop scheduling tools and clean up workers.
