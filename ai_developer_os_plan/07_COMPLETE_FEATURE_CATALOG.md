# RepoPilot — Complete Feature Catalog

**Document purpose:** This file is the standalone, detailed feature inventory for RepoPilot, an AI Developer OS. The other documents define requirements, architecture, stack, security, evaluation, and implementation sequencing. This catalog lists the product capabilities in one place.

## 1. Project and Repository Management
- Create, open, import, and manage multiple software projects.
- Open local Git repositories and clone repositories from Git hosting services.
- Detect languages, frameworks, package managers, build systems, and project entry points.
- Identify frontend, backend, database, infrastructure, test, and documentation layers.
- Recognize monorepos and multi-service projects.
- Generate project summaries and initial architecture overviews.
- Maintain project-specific instructions, settings, context, and chat history.
- Respect `.gitignore` and configurable indexing exclusions.
- Detect file additions, changes, renames, and deletions.
- Re-index changed files incrementally rather than rebuilding the entire index.
- Track index status, errors, and source revision.

## 2. AI Developer Chat
- Answer natural-language questions about the active repository.
- Explain code, architecture, APIs, configuration, dependencies, and business logic.
- Support multi-turn, project-scoped conversations.
- Stream responses to the UI.
- Accept pasted logs, stack traces, code, requirements, and selected files as context.
- Ask clarifying questions when requirements are ambiguous.
- Include file paths, line ranges, and supporting code evidence.
- Show which sources and tools informed an answer.
- Separate verified observations from hypotheses and recommendations.
- Support configurable prompts, context budgets, and model settings.
- Maintain conversation history and allow users to start, rename, and revisit sessions.

## 3. Repository Intelligence and Code Navigation
- Index source code, configuration, tests, and documentation.
- Parse supported languages with Tree-sitter or suitable language parsers.
- Identify functions, classes, methods, imports, exports, and symbols where supported.
- Provide exact-text, keyword, symbol, and semantic search.
- Map relationships between modules and files.
- Trace call sites and dependency paths where static analysis supports it.
- Detect API routes, middleware, data models, and service boundaries where recognizable.
- Summarize files, directories, packages, and repositories.
- Find similar or duplicated code.
- Flag potentially unused symbols, files, or dependencies as candidates for review.
- Filter search by path, language, symbol, and file type.
- Display source locations and retrieval evidence.
- Exclude binaries, generated artifacts, secrets, and irrelevant paths by default.

## 4. RAG and Project Knowledge
- Chunk code by logical units such as functions, classes, and modules where possible.
- Chunk documentation by headings and semantic sections.
- Store metadata such as path, symbol, line range, language, and revision.
- Use SQLite FTS5 for lexical retrieval.
- Support local embeddings and a local vector store such as FAISS where suitable.
- Combine lexical, semantic, and structural retrieval.
- Optionally rerank results using a compatible model.
- Limit retrieved context to a configurable token budget.
- Refresh or invalidate stale chunks when files change or are deleted.
- Keep project indexes isolated from each other.
- Allow exclusions for sensitive or irrelevant content.
- Evaluate retrieval quality using curated queries and expected source locations.

## 5. LangChain and LangGraph Orchestration
- Use LangChain integrations for model, prompt, retriever, and tool adapters.
- Use LangGraph for stateful, multi-step workflows and conditional routing.
- Keep typed workflow state and structured intermediate outputs.
- Support checkpoints and safe resumption where feasible.
- Add bounded retries for transient failures.
- Enforce step limits, timeouts, cancellation, and loop detection.
- Route tasks to specialist workflows based on task type.
- Record workflow events, tool inputs/outputs, errors, and execution timing while redacting secrets.
- Add human approval gates for sensitive or destructive operations.
- Support replayable evaluation fixtures and workflow debugging.
- Prefer deterministic tools for operations that do not require an LLM.

## 6. Specialist Agents
- **Repository Analyst:** explains structure, modules, dependencies, and execution paths.
- **Debugging Agent:** investigates logs, exceptions, stack traces, and likely root causes.
- **Coding Agent:** proposes and applies approved code changes as reviewable patches.
- **Testing Agent:** discovers, runs, and generates relevant tests.
- **Code Review Agent:** checks diffs for bugs, regressions, security, and maintainability concerns.
- **Documentation Agent:** drafts and updates README, setup, API, and architecture documentation.
- **Dependency Agent:** analyzes package manifests, dependency changes, and compatibility concerns.
- **Refactoring Agent:** proposes behavior-preserving structural improvements.
- **Performance Agent:** investigates likely bottlenecks using evidence and available profiling tools.
- **Security Agent:** flags suspicious patterns and integrates available security scanners.
- **Database Agent:** assists with schemas, queries, and migrations.
- **DevOps Agent:** assists with build, container, CI, and deployment configuration.
- **Workflow Coordinator:** routes tasks and reconciles structured agent outputs.
- Prevent agents from applying conflicting changes independently; consolidate and review patches.

## 7. Code Generation and Editing
- Generate code snippets and new files.
- Edit existing files with targeted patches.
- Preview before-and-after changes.
- Review and accept or reject individual diff hunks.
- Support coordinated multi-file changes.
- Follow repository conventions and local instructions.
- Generate type annotations, docstrings, validation, logging, and error handling.
- Refactor functions, classes, and modules.
- Update imports and references when required.
- Generate tests for new or modified behavior.
- Detect patch conflicts and preserve unrelated user changes.
- Show every modified file and the final diff.
- Support undo and recovery through Git or saved patch history.
- Require approval for high-impact or destructive changes.

## 8. Autonomous Development Workflows
- Turn a feature request or bug report into a structured implementation plan.
- Inspect relevant repository context before proposing changes.
- Identify likely affected modules, dependencies, risks, and tests.
- Break work into small, reviewable steps.
- Create an isolated Git worktree for a task.
- Implement approved changes in bounded iterations.
- Run configured formatting, linting, type checks, builds, and tests.
- Analyze failures and attempt a limited number of repairs.
- Re-run relevant checks after repairs.
- Review the final diff for unintended changes.
- Produce a summary of changes, evidence, test outcomes, and unresolved risks.
- Create commits or pull requests only when authorized.
- Stop and ask for help when requirements are unclear or verification is insufficient.

## 9. Debugging and Error Analysis
- Accept pasted errors, stack traces, logs, and failing test output.
- Correlate error locations with repository symbols and code paths.
- Develop and rank root-cause hypotheses using evidence.
- Identify relevant configuration, dependency, and environment issues.
- Suggest reproducible debugging steps and commands.
- Generate minimal reproduction cases where appropriate.
- Inspect expected versus actual test behavior.
- Propose a minimal fix and explain trade-offs.
- Reproduce issues in a controlled environment when feasible.
- Verify fixes with relevant checks where possible.
- Keep a history of attempts and outcomes.
- Never report a fix as verified if the relevant checks did not run or failed.

## 10. Terminal and Command Execution
- Provide an integrated terminal or task-output panel.
- Run approved commands in the selected project.
- Detect configured toolchains and project environments.
- Run build, test, lint, format, and type-check commands.
- Capture stdout, stderr, exit status, and duration.
- Stream command output and allow cancellation.
- Enforce timeouts and, where supported, CPU, memory, process, and disk limits.
- Restrict working directories and environment access.
- Support Docker or Podman isolation where available.
- Use command policies and approval prompts for risky operations.
- Warn or block on destructive commands and unapproved network access.
- Redact secret-like values from logs.
- Keep an audit trail for agent-initiated commands.

## 11. Testing and Quality Assurance
- Detect existing test frameworks and test commands.
- Discover relevant tests based on changed files and dependencies.
- Run selected tests or the full suite.
- Generate unit and integration tests where supported.
- Support pytest and project-native test frameworks.
- Support browser end-to-end tests with Playwright.
- Integrate configured linters, formatters, and static type checkers.
- Parse results into passed, failed, skipped, and errored categories.
- Associate failures with relevant files and recent changes.
- Re-run regression tests after patches.
- Report coverage when supported by the project's tooling.
- Identify likely flaky tests without assuming every failure is flaky.
- Preserve test logs as task evidence.
- Treat test success as evidence, not proof of total correctness.

## 12. Code Review and Security Analysis
- Review staged, unstaged, and AI-generated diffs.
- Flag likely bugs, edge cases, error-handling gaps, and regressions.
- Check for hardcoded credentials and accidental secret exposure.
- Flag potential injection, unsafe deserialization, path traversal, and authorization issues.
- Integrate available dependency and static-analysis scanners.
- Review API validation, authentication, and permission checks.
- Flag risky configuration and permissions.
- Report findings with file paths, line ranges, severity, evidence, and suggested remediation.
- Distinguish confirmed scanner results from heuristic concerns.
- Allow configurable review rules.
- Require human approval before security-sensitive fixes.

## 13. Git and Version Control
- Display repository status, diffs, branches, and commit history.
- Create and switch branches when authorized.
- Create isolated worktrees for concurrent tasks.
- Stage and unstage files or hunks.
- Review staged and unstaged changes separately.
- Draft commit messages and pull request descriptions.
- Create commits only with explicit permission.
- Detect merge conflicts and explain conflict regions.
- Propose conflict resolutions for review.
- Preserve uncommitted user work.
- Support rollback and recovery for AI-generated changes.
- Avoid force-pushing or rewriting shared history without explicit approval.
- Integrate optional GitHub issue and pull-request workflows.

## 14. Documentation and Project Knowledge
- Generate and update README files.
- Draft installation, setup, and troubleshooting guides.
- Generate architecture documentation and Mermaid diagrams.
- Document API routes, request schemas, and response formats.
- Document modules and important implementation decisions.
- Explain required environment variable names without revealing secret values.
- Generate contribution guidelines and onboarding guides.
- Draft changelogs from code and Git history.
- Maintain a project glossary and domain terms.
- Link requirements, implementation changes, and tests where feasible.
- Flag documentation that may have become stale after code changes.

## 15. Model Management and Local Inference
- Integrate Ollama and/or llama.cpp-compatible local inference.
- Support compatible OpenAI-style endpoints when configured.
- Discover available models through the configured backend.
- Let users select models for coding, reasoning, embeddings, and reranking tasks.
- Configure context size and generation parameters where supported.
- Allow explicitly configured fallback models.
- Benchmark models on representative project tasks.
- Track latency and resource consumption.
- Cache safe, reusable results where appropriate.
- Avoid sending the entire repository when targeted retrieval is sufficient.
- Clearly indicate local versus remote inference.
- Do not require paid hosted APIs for core workflows.
- Verify model and dependency licenses before distribution or commercial use.

## 16. Desktop User Experience
- Use Tauri with React and TypeScript for the desktop shell and UI.
- Provide project dashboard and project switching.
- Include file explorer, code viewer, AI chat, diff review, and terminal panels.
- Display citations, task progress, workflow traces, and approval requests.
- Show test, lint, type-check, and build results.
- Provide keyboard shortcuts and a command palette.
- Support light and dark themes.
- Allow configurable panels and layouts where practical.
- Show model connectivity and indexing status.
- Provide clear errors and recovery actions.
- Support accessible keyboard navigation and focus behavior.

## 17. Workflow Automation
- Save reusable workflows for debugging, feature implementation, test generation, refactoring, and documentation.
- Start workflows manually or against selected files and folders.
- Support conditional branches and structured data between stages.
- Add dry-run mode before applying changes.
- Configure retries, timeouts, step limits, and approval checkpoints.
- Store task history and outputs.
- Resume interrupted workflows only when safe.
- Validate workflow definitions and tool permissions.
- Keep local workflows usable without mandatory cloud services.

## 18. Performance and Resource Management
- Perform indexing and analysis in background workers.
- Use incremental indexing and cache embeddings where appropriate.
- Stream responses and task logs.
- Retrieve only relevant code and documentation.
- Cancel obsolete work and limit concurrent tasks.
- Provide configurable context and indexing limits.
- Support lower-memory configurations and smaller models.
- Expose useful disk, memory, and latency diagnostics.
- Benchmark on representative repositories and supported hardware.
- Do not promise unrealistic response times for model inference.

## 19. Privacy, Safety, and Reliability
- Keep repository content local by default.
- Clearly disclose data sent to remote model endpoints.
- Redact likely secrets before model submission and logging.
- Use the operating system's secure credential storage where available.
- Treat code, comments, repository instructions, issues, and retrieved documents as untrusted input.
- Defend against prompt injection and malicious tool instructions.
- Restrict file access to the selected workspace and explicitly authorized locations.
- Require permission for network access and destructive actions.
- Run untrusted code in isolation where supported.
- Use atomic patching, diff review, cancellation, and recovery mechanisms.
- Maintain audit logs without collecting sensitive source by default.
- Keep telemetry opt-in and minimize collected data.
- Provide dependency scanning and a secure update process.

## 20. Observability and Evaluation
- Record workflow events, tool invocations, errors, retries, and durations.
- Trace LangGraph execution paths.
- Track model latency and token usage when available.
- Use structured logs and optional OpenTelemetry instrumentation.
- Maintain repeatable evaluation tasks and expected outcomes.
- Measure retrieval relevance, citation correctness, and answer grounding.
- Measure patch acceptance, task completion, test pass rate, and regressions.
- Compare model and prompt versions on the same evaluation set.
- Provide diagnostics reports for support and troubleshooting.
- Avoid recording repository source or secrets in telemetry by default.

## 21. Dashboard and Activity Analytics
- Show repository indexing status and counts of files and symbols.
- Display current Git branch and repository status.
- List active, completed, failed, and cancelled tasks.
- Show pending approval requests.
- Summarize changed files and patch status.
- Display test, lint, build, and type-check outcomes.
- Show recent debugging sessions and task history.
- Display model latency and available resource diagnostics.
- Track task retries and workflow outcomes.
- Export task summaries and verification reports.
- Warn about stale indexes or failed background jobs.

## 22. Integrations and Extensibility
- Integrate with Git and local development toolchains.
- Support GitHub as an optional integration.
- Support Docker or Podman for isolation.
- Support MCP-compatible tools only behind explicit permission boundaries.
- Define an interface for custom tools and language adapters.
- Add optional test, lint, formatting, and security scanner integrations.
- Support configurable local model providers.
- Version tool schemas and workflow definitions.
- Validate plugin permissions and require opt-in before enabling capabilities.
- Keep core repository chat, search, patch review, and testing workflows independent of external SaaS.

## 23. Suggested MVP Acceptance Checklist
- [ ] Open and manage a local Git repository.
- [ ] Detect repository structure and common project metadata.
- [ ] Index source files and documentation incrementally.
- [ ] Support keyword search and semantic retrieval.
- [ ] Answer repository questions with file and line references.
- [ ] Explain stack traces using repository evidence.
- [ ] Generate a structured implementation plan.
- [ ] Generate a targeted patch and preview the diff.
- [ ] Apply changes only after user approval.
- [ ] Preserve unrelated and uncommitted user changes.
- [ ] Run selected tests and capture their results.
- [ ] Use an isolated worktree for AI modifications.
- [ ] Support a local inference backend.
- [ ] Enforce timeouts, cancellation, and bounded agent steps.
- [ ] Show final changes, test outcomes, and unresolved issues.
- [ ] Work without a paid API for the core MVP.

## 24. Non-Goals for the Initial MVP
- Unrestricted autonomous access to the user's whole machine.
- Automatic execution of arbitrary shell commands without permission controls.
- Guaranteed correctness of AI-generated code.
- Mandatory cloud accounts or paid model APIs.
- Automatically pushing commits or merging pull requests without explicit approval.
- Claiming full language support where parser and static-analysis coverage is incomplete.
- Replacing a developer's code review or security judgment.
