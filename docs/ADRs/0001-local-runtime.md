# ADR 0001: Local authenticated API and bounded task workers

Status: implemented, 2026-10-26.

- Windows first; Python, JavaScript and TypeScript are the indexed source languages.
- The browser and desktop UI use the same FastAPI service and compiled web assets.
- Each launch generates a random session token. The browser receives it in a URL fragment, removes it from browser history, and keeps it in tab session storage. After the first valid request, the API also issues an HttpOnly same-origin cookie so a normal reload remains authenticated without exposing the token in the URL.
- API state uses SQLite with WAL and additive schema migrations. Model calls run outside database write transactions.
- Two concurrent task workers are permitted. LangGraph persists clarification checkpoints in a separate SQLite file.
- Read-only answers record immutable evidence excerpts and hashes. Evidence is rechecked before completion; the UI does not claim that model conclusions are formally proven.
- Patch generation requires a clean base and occurs in a separate worktree. Applying is an explicit approval bound to the current diff hash. Git hooks, filters, and fsmonitor are disabled for application operations.
- Tests run in Docker against a disposable source copy, without `.git`, secrets, network, or host dependency mounts. Images must already exist locally. There is no host fallback.
- Semantic retrieval is opt-in, uses a local embedding runtime, and remains disabled until a model is explicitly selected and benchmarked.

Trade-offs: no automatic dirty-worktree snapshot/merge; no arbitrary command support; local Git and Docker remain external prerequisites. The optional hosted model must be explicitly consented to in the UI.
