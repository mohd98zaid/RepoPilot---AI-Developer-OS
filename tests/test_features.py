import json

import httpx
import pytest
from repopilot_api.database import connect
from repopilot_api.evaluation import evaluate
from repopilot_api.model import ModelError, ModelGateway
from repopilot_api.semantic import LocalEmbeddings, hybrid_search, index_embeddings
from repopilot_api.symbols import extract_relationships, extract_symbols
from test_runtime import ready


def test_model_adapter_redacts_request_and_handles_malformed_output(monkeypatch):
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": []})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    model = ModelGateway(
        "openai_compatible", "https://provider.invalid/v1", "private-test-value", "test-model", None
    )
    with pytest.raises(ModelError):
        model.complete(
            "password=super-secret", [{"path": "a.py", "excerpt": "API_KEY=123456789abcdef"}]
        )
    assert "super-secret" not in str(requests)
    assert "123456789abcdef" not in str(requests)


def test_tsx_and_nested_symbols_have_real_boundaries():
    symbols = extract_symbols(
        "class A:\n    def f(self):\n        return 1\n\ndef g():\n    return 2\n", "python"
    )
    assert [(s["name"], s["start_line"], s["end_line"]) for s in symbols] == [
        ("A", 1, 3),
        ("f", 2, 3),
        ("g", 5, 6),
    ]
    tsx = extract_symbols(
        "export function Card() { return <div>Hi</div>; }", "typescript", "Card.tsx"
    )
    assert tsx[0]["name"] == "Card"
    relations = extract_relationships("from x import y\ndef f():\n    y()\n", "python")
    assert any(
        r["kind"] == "call_candidate" and r["source"] == "f" and r["target"] == "y"
        for r in relations
    )


def test_semantic_cache_is_repo_scoped_and_invalidates_changed_files(tmp_path, git_repository):
    client, repo = ready(tmp_path, git_repository)

    class Embeddings:
        model = "deterministic-test-vector-v1"
        calls = 0

        def embed(self, text):
            self.calls += 1
            return [1.0, 0.0] if "auth" in text else [0.0, 1.0]

    adapter = Embeddings()
    with connect(tmp_path / "api.sqlite3") as db:
        assert index_embeddings(db, repo, adapter) == 3
        assert index_embeddings(db, repo, adapter) == 0
        assert adapter.calls == 3
        hits = hybrid_search(db, repo, "auth", adapter)
        assert hits[0]["path"] == "src/auth.py"
    (git_repository / "src/auth.py").unlink()
    client.post(f"/repositories/{repo}/index")
    with connect(tmp_path / "api.sqlite3") as db:
        index_embeddings(db, repo, adapter)
        assert db.execute("SELECT 1 FROM embeddings WHERE path = 'src/auth.py'").fetchone() is None
    with pytest.raises(ValueError, match="loopback"):
        LocalEmbeddings("model", "https://remote.invalid")


def test_recall_is_fraction_of_expected_files_not_hit_rate():
    report = evaluate(
        [{"task_id": "multi", "query": "q", "expected_paths": ["a.py", "b.py"]}],
        lambda query: [{"path": "x.py"}, {"path": "a.py"}, {"path": "a.py"}],
    )
    assert report["recall_at_5"] == 0.5
    assert report["mrr"] == 0.5


def test_streaming_provider_consumes_sse_and_honors_cancel(monkeypatch):
    def handler(request):
        assert json.loads(request.content)["stream"] is True
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=b'data: {"choices":[{"delta":{"content":"Hello "}}]}\n\ndata: {"choices":[{"delta":{"content":"world"}}]}\n\ndata: [DONE]\n\n',
        )

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    seen = []
    model = ModelGateway(
        "openai_compatible",
        "https://example.invalid",
        "test-value",
        "model",
        None,
        on_text=seen.append,
    )
    assert model.complete("Hello", []) == "Hello world"
    assert seen[-1] == "Hello world"
    from dataclasses import replace

    with pytest.raises(ModelError, match="cancelled"):
        replace(model, cancelled=lambda: True).complete("Hello", [])
