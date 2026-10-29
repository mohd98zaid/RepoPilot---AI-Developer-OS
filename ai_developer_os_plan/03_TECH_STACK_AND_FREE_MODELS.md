# Free/Open-Source Technology and Model Plan — RepoPilot

## 1. Requirements
- No required paid SaaS.
- Local inference by default.
- License audit for every dependency and model.
- Replaceable interfaces to avoid lock-in.
- Optional hosted services must be clearly marked optional.

## 2. Recommended stack

| Need | Primary choice | Alternative | Notes |
|---|---|---|---|
| Desktop shell | Tauri 2 | Web app first | Cross-platform shell; audit plugins |
| UI | React + TypeScript | Svelte | Choose one; avoid framework mixing |
| Components | shadcn/ui + Tailwind | Radix UI directly | Audit dependency licenses |
| API | FastAPI | Starlette | Python ecosystem |
| Schemas | Pydantic | dataclasses + validation | API contract |
| Orchestration | LangGraph | Explicit Python state machine | LangGraph is requested; keep graph bounded |
| Model integration | LangChain core | Direct runtime adapter | Use only needed integrations |
| Local inference | Ollama | llama.cpp | Ollama is simpler; llama.cpp gives lower-level control |
| Code parser | tree-sitter | Language-native AST parsers | Exact grammar/license checks |
| Metadata | SQLite | PostgreSQL | SQLite simplest for local app |
| Lexical search | SQLite FTS5 | Tantivy | Exact identifiers and error text |
| Vector search | pgvector/Qdrant | Local FAISS index | Add only if semantic retrieval helps benchmark |
| Embeddings | sentence-transformers-compatible local model | Runtime-specific embedding model | Verify model license and dimensions |
| Git | Git CLI | libgit2 binding | Wrap commands with strict argument validation |
| Sandbox | Docker/Podman | OS-specific isolated runner | Windows support and license details vary |
| Tests | pytest, httpx, Playwright | unittest | UI/API/e2e |
| Tracing | OpenTelemetry | Structured JSON logs first | Avoid unnecessary infra in MVP |
| Evaluation | Custom Python harness | Ragas/DeepEval where suitable | Tool metrics often need custom rubrics |
| Packaging | Tauri bundler | PyInstaller backend packaging | Validate update/signing approach |
| CI | GitHub Actions | Local CI runner | Public repo free quotas may change; local tests remain possible |

## 3. License checklist
- Verify current license of every library and optional plugin.
- Verify model-weight license independently from runtime license.
- Confirm redistribution rights before packaging model weights.
- Include third-party notices and attribution.
- Pin versions and review security advisories.
- Do not assume a free API is open source or suitable for commercial production.
- Keep hosted model support optional.

## 4. Local LLM approach
Use Ollama or llama.cpp to run a compatible code model locally. Select model size/quantization based on actual CPU, RAM, VRAM, context length, and latency. Benchmark code understanding and patch tasks instead of selecting by leaderboard alone.

For limited VRAM:
- Start with a small quantized model.
- Reduce context size and retrieved snippets.
- Keep indexing and embeddings separate from generation.
- Avoid running multiple large models concurrently.
- Measure tokens/second, memory use, and task accuracy.
- Treat local inference as no per-token API bill, not zero total cost.

## 5. NVIDIA option
NVIDIA hosted inference is optional and excluded from the strict all-free/open-source baseline. Endpoint access, free quota, model availability, usage terms, and commercial rights can change. NVIDIA GPU acceleration may be used if hardware and drivers support it, but the MVP does not require NVIDIA hardware.

## 6. Initial install strategy
- Install Git.
- Install Python using a supported version.
- Install Node.js for the UI build.
- Install Tauri system prerequisites.
- Install Ollama or llama.cpp.
- Pull/download a license-compatible code model manually.
- Create Python virtual environment and install pinned dependencies.
- Run API, UI, and tests locally.
- Install Docker/Podman only when sandbox milestone begins.

Exact version pins should be selected and tested at project kickoff; this document deliberately avoids inventing current versions.
