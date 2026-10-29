# Product Requirements Document — RepoPilot

## Product summary
RepoPilot is a local-first AI Developer OS for repository exploration, issue investigation, and sandboxed patch proposals. It uses LangGraph for bounded workflows, LangChain integrations for model/tool interfaces, local LLM inference by default, and hybrid code retrieval.

## Goals
- Reduce time spent understanding repositories and investigating issues.
- Ground answers in commit-aware file and line evidence.
- Safely propose and test code changes in isolation.
- Provide reproducible task history and evaluation.

## Non-goals
- Auto-merge or auto-deploy.
- Unrestricted shell access.
- Guaranteed code correctness.
- Full IDE replacement in MVP.
- Mandatory cloud inference or paid SaaS.

## Personas
1. Developer onboarding to a codebase.
2. Maintainer triaging a bug.
3. Engineer proposing a regression fix.
4. Technical lead reviewing architecture.

## MVP features
1. Repository registration and status.
2. File/symbol indexing with ignore rules.
3. Keyword/exact identifier search.
4. Local LLM chat.
5. LangGraph investigation workflow.
6. Evidence panel with file/line references.
7. Git worktree patch proposal.
8. Sandboxed approved test execution.
9. Diff review and explicit approval.
10. Run history and evaluation suite.

## User stories
- As a developer, I can ask where a function is implemented and inspect the source.
- As a maintainer, I can provide an issue and get a hypothesis list with supporting evidence.
- As an engineer, I can request a patch in an isolated worktree without touching my uncommitted changes.
- As a reviewer, I can inspect the exact diff and test results before approving it.
- As a privacy-conscious user, I can use a local model without a hosted inference account.

## Functional requirements
- All inputs are schema-validated.
- Repository indexing respects ignore/exclusion rules.
- Evidence includes commit hash, path, and line range.
- Model-generated commands are never run directly on the host.
- All write actions use isolated worktrees/sandbox and explicit approval.
- Runs can be cancelled and have bounded budgets.
- Errors are visible and distinguish retryable from permanent.
- Evaluation is repeatable.

## Non-functional requirements
- Local-first privacy.
- Modular provider/runtime adapters.
- Recoverable workflow state.
- Accessibility and keyboard navigation.
- Maintainable, typed code.
- Clear install/setup documentation.

## MVP success metrics
- Retrieval recall@5 on a labeled benchmark.
- Evidence correctness.
- Issue diagnosis quality.
- Patch test pass rate and regression rate.
- Unsafe-action prevention.
- p50/p95 latency and resource use.
- Task completion rate.

## Acceptance criteria
- Can install without paid service credentials.
- Can use a local inference runtime.
- Can index and query a sample repository.
- Can investigate a known issue with evidence.
- Can create a patch in a separate worktree.
- Can run tests in a restricted environment.
- Can reject approval without modifying the original repository.
- Has automated tests and documented limitations.

## Risks
- Weak local models; benchmark and allow swapping.
- Prompt injection; enforce permissions outside prompts.
- Sandbox escape; defense in depth and no secrets.
- Stale index; commit/file hashes and incremental reindexing.
- Scope creep; constrain initial languages and workflows.
