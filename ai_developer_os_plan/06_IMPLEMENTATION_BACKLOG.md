# Implementation Backlog — RepoPilot

## How to use this backlog
Complete epics in order. Do not begin patch execution until repository indexing, tool permissions, and read-only investigation are tested. Each task should have tests and acceptance criteria before it is marked done.

## Epic 0 — Project governance and scaffold
- [ ] Create repository and choose project license.
- [ ] Add README, PRD, architecture, threat model, ADR directory.
- [ ] Define supported OS and initial languages.
- [ ] Create Python package structure and frontend workspace.
- [ ] Add formatter, linter, type checks, and pre-commit hooks.
- [ ] Add dependency lockfiles and license audit process.
- [ ] Add `.env.example` containing placeholders only.
- [ ] Add CI workflow or reproducible local test script.

**Acceptance:** clean install and basic tests run without paid accounts.

## Epic 1 — Local model gateway
- [ ] Define provider-neutral model interface.
- [ ] Add Ollama adapter.
- [ ] Add timeout and cancellation behavior.
- [ ] Add structured output validation.
- [ ] Add model health check.
- [ ] Add configuration UI/API.
- [ ] Add model outage and malformed output tests.
- [ ] Document supported local model setup and license checks.

**Acceptance:** application can query a local model and fails safely when unavailable.

## Epic 2 — Repository registration
- [ ] Add repository registration endpoint/UI.
- [ ] Validate selected directory.
- [ ] Detect Git repository, branch, commit, and dirty state.
- [ ] Respect `.gitignore` and product ignore rules.
- [ ] Exclude secrets, binaries, build output, dependencies, and oversized files.
- [ ] Add path canonicalization tests.
- [ ] Add indexing status and cancellation.

**Acceptance:** repository metadata is visible and no files are modified.

## Epic 3 — Indexing and lexical search
- [ ] Create SQLite schema and migrations.
- [ ] Enumerate supported source files.
- [ ] Parse language and file metadata.
- [ ] Integrate tree-sitter for selected languages.
- [ ] Extract symbols and line ranges.
- [ ] Add SQLite FTS5 search.
- [ ] Add exact identifier search.
- [ ] Store file hashes and commit hashes.
- [ ] Incrementally update changed files.
- [ ] Remove stale chunks for deleted files.
- [ ] Add index consistency tests.

**Acceptance:** search returns correct file/line evidence on fixture repositories.

## Epic 4 — Optional semantic retrieval
- [ ] Select a license-compatible local embedding model.
- [ ] Define embedding interface and version.
- [ ] Add local embedding generation.
- [ ] Add vector index adapter (SQLite extension, FAISS, pgvector, or Qdrant after evaluation).
- [ ] Implement hybrid result merge and deduplication.
- [ ] Compare lexical vs vector vs hybrid retrieval.
- [ ] Add re-indexing behavior when embedding model changes.

**Acceptance:** semantic retrieval is enabled only if evaluation demonstrates useful improvement.

## Epic 5 — Read-only tools
- [ ] `list_repository_files`
- [ ] `search_code`
- [ ] `read_file_range`
- [ ] `get_symbol_definition`
- [ ] `find_references` where parser supports it
- [ ] `get_git_status`
- [ ] `get_recent_commits`
- [ ] `list_tests`
- [ ] Add schema validation and permission checks.
- [ ] Add tool-call audit events.
- [ ] Add malicious argument tests.

**Acceptance:** no tool can read outside the registered repository scope.

## Epic 6 — LangGraph investigation workflow
- [ ] Define typed state schema.
- [ ] Add request validation and task classification.
- [ ] Add bounded planner node.
- [ ] Add retrieval and inspection nodes.
- [ ] Add hypothesis-generation node.
- [ ] Add evidence verification.
- [ ] Add user clarification interrupt.
- [ ] Add checkpoint persistence.
- [ ] Add step/tool/time budgets.
- [ ] Add cancellation and terminal failure states.
- [ ] Add end-to-end investigation tests.

**Acceptance:** known questions produce evidence-backed reports without modifying files.

## Epic 7 — UI and run history
- [ ] Build home/repository list.
- [ ] Build task/chat panel.
- [ ] Show plan and node progress.
- [ ] Show evidence with path/line references.
- [ ] Show tool errors and retry status.
- [ ] Add run history.
- [ ] Add cancel button.
- [ ] Add accessibility and keyboard navigation tests.

**Acceptance:** user can inspect and cancel a run.

## Epic 8 — Git worktree management
- [ ] Detect uncommitted user changes.
- [ ] Create isolated worktree from recorded base commit.
- [ ] Ensure branch/worktree naming is collision-safe.
- [ ] Record cleanup metadata.
- [ ] Prevent writes to original worktree.
- [ ] Clean up on cancellation/failure.
- [ ] Test dirty-tree preservation and worktree cleanup.

**Acceptance:** patch workflow never overwrites user's original changes.

## Epic 9 — Patch proposal and diff validation
- [ ] Add patch-mode request confirmation.
- [ ] Generate patch only in isolated worktree.
- [ ] Validate all changed paths.
- [ ] Reject path traversal and out-of-scope changes.
- [ ] Add diff viewer.
- [ ] Summarize changed files and rationale.
- [ ] Tie approval to immutable diff hash.
- [ ] Add reject/approve tests.

**Acceptance:** user can inspect and reject a proposed patch safely.

## Epic 10 — Sandboxed test runner
- [ ] Detect supported test commands.
- [ ] Require approval for unknown commands.
- [ ] Add container/isolated runner.
- [ ] Disable network by default.
- [ ] Do not mount host secrets.
- [ ] Apply CPU/memory/disk/time limits.
- [ ] Capture exit code and bounded output.
- [ ] Terminate process tree on timeout/cancel.
- [ ] Add malicious test script fixtures.
- [ ] Record test environment/image version.

**Acceptance:** approved tests run in isolation and unsafe tests are blocked.

## Epic 11 — Verification and bounded repair
- [ ] Compare test outcomes with baseline where possible.
- [ ] Detect pre-existing failures.
- [ ] Add bounded patch repair loop.
- [ ] Re-run relevant tests after each repair.
- [ ] Verify diff scope after repair.
- [ ] Stop on budget exhaustion.
- [ ] Produce final evidence/test summary.

**Acceptance:** the system never claims tests passed when they did not run or failed.

## Epic 12 — Security hardening
- [ ] Local API session authentication.
- [ ] CORS/origin protections for local UI.
- [ ] Secret scanning/exclusion.
- [ ] Redaction of logs.
- [ ] Prompt injection fixtures.
- [ ] Path/symlink escape tests.
- [ ] Approval replay tests.
- [ ] Resource exhaustion tests.
- [ ] Dependency/license audit.
- [ ] Security documentation.

**Acceptance:** all critical threat-model tests pass or documented blockers prevent release.

## Epic 13 — Evaluation
- [ ] Create labeled repository question set.
- [ ] Create issue investigation benchmark.
- [ ] Create patch benchmark with expected tests.
- [ ] Add retrieval metrics.
- [ ] Add task outcome metrics.
- [ ] Add safety metrics.
- [ ] Record hardware/model configuration.
- [ ] Generate Markdown evaluation report.
- [ ] Add regression gate to release process.

**Acceptance:** benchmark can be run repeatedly with the same dataset/version.

## Epic 14 — Packaging and documentation
- [ ] Package desktop app.
- [ ] Provide local model setup guide.
- [ ] Provide sandbox setup guide.
- [ ] Document supported languages and limitations.
- [ ] Add architecture diagrams.
- [ ] Record a demo workflow.
- [ ] Publish evaluation results.
- [ ] Add third-party notices and license information.
- [ ] Tag a reproducible release.

**Acceptance:** another developer can install and reproduce the documented demo without a paid SaaS account.

## Suggested milestone order
1. Governance/scaffold.
2. Local model gateway.
3. Repository registration and lexical index.
4. Read-only tools.
5. LangGraph investigation.
6. UI/run history.
7. Worktree and diff.
8. Sandbox tests.
9. Verification and security.
10. Evaluation and release.

## Do not build yet
- Multi-agent swarm.
- Cloud multi-tenancy.
- Billing.
- Auto-merge/deploy.
- Dozens of connectors.
- Custom model training.
- Complex knowledge graph before retrieval benchmarks.
