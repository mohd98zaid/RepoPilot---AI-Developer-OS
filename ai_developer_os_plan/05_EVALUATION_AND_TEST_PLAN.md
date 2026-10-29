# Evaluation and Test Plan — RepoPilot

## 1. Purpose
Measure whether RepoPilot retrieves relevant code, provides evidence-supported diagnoses, proposes useful patches, and respects safety boundaries. Evaluation must be repeatable and must distinguish prototype targets from measured outcomes.

## 2. Benchmark design
Start with 25–50 tasks from permissively licensed repositories or synthetic fixtures. Record the exact commit hash. Include:
- Architecture questions.
- Exact symbol and identifier questions.
- Bug reports with known affected files.
- Regression scenarios with tests.
- Missing-information tasks where the correct response is to ask a question.
- Adversarial prompt-injection content.
- Malicious test-command attempts.

Dataset fields:
- task_id
- repository and commit
- prompt
- expected relevant files/symbols
- reference evidence
- expected behavior
- allowed tools
- test commands
- forbidden actions
- reviewer rubric
- license/source provenance

## 3. Retrieval evaluation
Metrics:
- Recall@5 and Recall@10 for relevant files/symbols.
- MRR for first relevant result.
- Evidence freshness: cited commit matches target commit.
- Line-range validity.
- Exact identifier search success.
- Retrieval latency.

Compare:
1. FTS/keyword only.
2. Vector only.
3. Hybrid lexical + vector.
4. Hybrid + symbol/call-site expansion.
5. Hybrid + reranking, if available.

## 4. Diagnosis evaluation
Use a human-reviewed rubric:
- Correctness of likely cause.
- Evidence quality.
- Consideration of alternative hypotheses.
- Testability of proposed diagnosis.
- Appropriate uncertainty.
- No unsupported claims.

## 5. Patch evaluation
- Patch applies cleanly.
- Relevant tests pass.
- Existing regression tests pass.
- New tests cover the bug.
- No unrelated files changed.
- No forbidden path modified.
- Human reviewer acceptance.
- Regression rate after patch.

Do not equate passing tests with full correctness.

## 6. Safety evaluation
- Disallowed tool call blocked.
- Path traversal blocked.
- No host secret available in sandbox.
- Network access denied by default.
- Approval required for sensitive action.
- Rejected approval results in no mutation.
- Cancellation terminates processes.
- No cross-repository context leakage.
- Prompt injection does not change permissions.

## 7. Operational metrics
- Task success rate.
- p50/p95 end-to-end latency.
- Local model tokens/second.
- Peak RAM/VRAM.
- Indexing throughput.
- Tool timeout rate.
- Retry count.
- Cancellation completion time.
- Cost per task (hosted mode only; local hardware costs tracked separately).

## 8. Regression gates
Every release must:
- Pass unit, integration, security, and end-to-end tests.
- Not regress retrieval metrics beyond an agreed tolerance.
- Pass all critical safety tests.
- Document any benchmark changes.
- Record model, prompt, workflow, and indexer versions.

## 9. Test tooling
- pytest for unit and integration tests.
- httpx TestClient for FastAPI.
- Playwright for desktop/web UI workflows where supported.
- Temporary Git repositories for worktree tests.
- Mock model adapter for deterministic workflow tests.
- Optional local model smoke tests separate from deterministic CI.

## 10. Reporting
Publish:
- Hardware and OS.
- Model name, quantization, context length, runtime version.
- Dataset license and commit hashes.
- Metrics and confidence/limitations.
- Failure categories.
- Comparison against baseline.
- Reproduction instructions.
