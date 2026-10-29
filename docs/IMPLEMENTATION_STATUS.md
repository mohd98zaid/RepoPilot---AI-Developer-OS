# Implementation and verification status

Updated 2026-10-26. This replaces the earlier broad “complete MVP” claims: implementation, deterministic verification, and live release sign-off are different states.

| Area | Implemented now | Remaining acceptance work |
|---|---|---|
| Setup | MIT, Python/React packages, pinned runtime dependencies, npm/Cargo locks, CI, pre-commit configuration, ADR | User-owned Git repository/remote setup; pre-commit installation |
| Model gateway | Mock/Ollama/OpenAI-compatible, SSE/NDJSON parsing, cancellation, response limits, total request deadline, fallback, JSON parse retry, connection probe | Live NVIDIA/Ollama generation with a configured valid provider; model-quality evaluation |
| Registration/index | Git root validation, commit/dirty metadata, lexical index, file hashes, incremental updates/deletes, background indexing/cancel, product ignores | Large-repository performance measurements |
| Code intelligence | Tree-sitter Python/JS/TS/TSX declarations, imports, syntactic call candidates, source viewer | Cross-module dynamic dispatch and fully resolved call graphs are not implemented |
| Semantic retrieval | Opt-in loopback embeddings, SQLite vector cache, dimension/version checks, cosine search and reciprocal-rank fusion | Select/license a local embedding model and compare real retrieval quality against baseline |
| Investigation | LangGraph validation/plan/retrieval/analysis/verification, typed evidence IDs, durable clarification interrupts/resume, two workers, step/tool/time budgets | Broader diagnosis benchmark and adversarial model testing |
| UI/history | Repository/search/source/structure panels, asynchronous task progress, cancellation, clarification, diff approval, baseline/patch results, settings status, report export | Full accessibility audit; side-by-side and individual-hunk diff review not implemented |
| Patches | Model-generated or manual changes, isolated worktree, safe path policy, immutable diff approval, transactional replay protection, reject/apply/cleanup | Crash recovery around the narrow Git-apply/database-commit boundary needs further hardening; deletions/renames are not generated |
| Tests/repair | Docker-only source-copy execution, no network/secrets, tmpfs/resource limits, bounded logs, timeout/cancel cleanup, baseline comparison, two explicit repair attempts | Live container validation blocked until Docker Desktop and test image are available; live AI repair quality unmeasured |
| Security | Mandatory session token, origin restrictions, path/symlink/junction/hard-link checks, secret-pattern exclusion/redaction, Git hook/filter/fsmonitor suppression | Exhaustive secret scanning and full threat-model sign-off are not complete |
| Evaluation | 25 synthetic queries over 10 MIT modules, file recall@5, MRR, p50/p95, regression gate, JSON/Markdown reports | Real diagnosis/patch benchmarks and hardware/model throughput reports |
| Packaging | Windows Tauri application, bundled backend and web assets, NSIS build, launcher readiness checks, owned-process cleanup, checksum generation, license inventory/texts | Clean-machine installation verification, publisher signing, complete license review, public release |

## Automated evidence

- Backend/security/workflow tests exercise authentication, traversal, immutable evidence, replay, modified-worktree rejection, model protocol parsing, cancellation and checkpoint resumption.
- Chromium browser test exercises registration → indexing → search → investigation → manual patch → reject, preserving the original source.
- Synthetic retrieval report: `evals/reports/retrieval.md` and `retrieval.json`.
- Packaged backend smoke: `scripts/smoke_packaged.py`.
- One Windows symlink test needs Developer Mode/admin privilege and skips when unavailable.
- Live Docker test explicitly skips when the engine or prepared image is unavailable; skipped tests are not passing safety evidence.

## Required local setup to finish live validation

1. Start Docker Desktop and build the image described in `sandbox/README.md`.
2. Configure a valid private model credential or start Ollama with an installed model.
3. Choose a license-compatible embedding model if semantic retrieval is wanted.
4. Provide publisher signing credentials only when preparing a signed public release.

## Final closure state

The implementation and offline verification work is complete. The remaining release gates are environmental or organizational:

- Docker Desktop must expose its engine pipe before the live sandbox test can run. The current Windows session has Docker Desktop processes, but no working `docker_engine` pipe, so the live isolation test was skipped rather than marked passed.
- A valid Ollama model or remote-provider credential is required for live generation-quality testing. Provider contract, streaming, cancellation, redaction, structured-output, and fallback tests pass without sending data externally.
- An embedding model must be selected and license-reviewed before semantic retrieval can be evaluated beyond the deterministic adapter tests.
- Installer signing requires the publisher’s certificate. The unsigned NSIS installer is built and its SHA-256 checksum is recorded.
- The workspace is not initialized as a Git repository in this environment; no commit, push, or remote release operation was performed.

Offline closure checks currently pass: 32 backend/security tests, browser E2E, Ruff, React build, Tauri cargo check, npm audits, Python dependency check, synthetic retrieval evaluation, packaged backend smoke, desktop lifecycle smoke, and NSIS packaging.

Optional long-term catalog capabilities (cloud collaboration, connectors, specialist multi-agent swarms, full IDE replacement) are not implemented and were explicit non-goals of the original MVP backlog. No release publication or remote Git operation has been performed.
