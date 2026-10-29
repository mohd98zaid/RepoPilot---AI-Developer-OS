from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field

from .model import ModelGateway


class InvestigationState(TypedDict, total=False):
    request: str
    plan: list[dict]
    evidence: list[dict]
    hypotheses: list[dict]
    answer: str
    status: str
    error: str | None
    step_count: int
    tool_call_count: int
    verification: dict


class Hypothesis(BaseModel):
    statement: str = Field(max_length=2000)
    evidence_ids: list[int] = Field(max_length=20)
    distinguishing_check: str = Field(max_length=2000)


class Analysis(BaseModel):
    answer: str = Field(min_length=1, max_length=24000)
    hypotheses: list[Hypothesis] = Field(default_factory=list, max_length=5)
    evidence_ids: list[int] = Field(min_length=1, max_length=20)


Retriever = Callable[[str], list[dict]]


def build_investigation_graph(
    retriever: Retriever,
    model: ModelGateway,
    *,
    checkpointer=None,
    cancelled=lambda: False,
    timeout=120,
    on_event=lambda *args: None,
    verifier=lambda evidence: True,
):
    started = time.monotonic()

    def bounded(name, fn):
        def node(state):
            if cancelled():
                raise ValueError("task cancelled")
            if time.monotonic() - started > timeout or state.get("step_count", 0) >= 12:
                raise ValueError("workflow budget exhausted")
            result = fn(state)
            result["step_count"] = state.get("step_count", 0) + 1
            on_event(name, result)
            return result

        return node

    def validate(state):
        if not state["request"].strip():
            raise ValueError("request is empty")
        return {"status": "running"}

    def plan(state):
        # Deterministic tool plan; the model cannot add host execution permissions.
        return {
            "plan": [
                {"action": "search_code", "query": state["request"], "limit": 12},
                {"action": "inspect_evidence", "max_characters": 24000},
                {"action": "analyze", "require_evidence_ids": True},
                {"action": "verify", "check_file_hashes": True},
            ]
        }

    def retrieve(state):
        if state.get("tool_call_count", 0) >= 4:
            raise ValueError("tool-call budget exhausted")
        evidence = retriever(state["request"])[:12]
        return {"evidence": evidence, "tool_call_count": state.get("tool_call_count", 0) + 1}

    def clarify(state):
        reply = interrupt(
            {
                "question": "No matching current evidence was found. Provide a function name, file path, or exact error and re-index if files changed."
            }
        )
        if not isinstance(reply, str) or not reply.strip() or len(reply) > 10000:
            raise ValueError("clarification must contain 1..10000 characters")
        return {"request": reply, "status": "running"}

    def analyze(state):
        evidence = state["evidence"]
        if model.provider == "mock":
            return {
                "answer": model.complete(state["request"], evidence),
                "hypotheses": [],
                "verification": {
                    "evidence_ids": list(range(len(evidence))),
                    "model": "mock",
                    "claims_verified": False,
                },
            }
        prompt = (
            "Investigate the request. Return JSON matching this schema: "
            + str(Analysis.model_json_schema())
            + " Evidence IDs are zero-based indices in the supplied list. "
            "Distinguish observations from hypotheses; never assert tests ran. Request: "
            + state["request"]
        )
        analysis = Analysis.model_validate(model.structured(prompt, evidence))
        ids = analysis.evidence_ids + [i for h in analysis.hypotheses for i in h.evidence_ids]
        if any(i < 0 or i >= len(evidence) for i in ids):
            raise ValueError("model returned an invalid evidence ID")
        return {
            "answer": analysis.answer,
            "hypotheses": [h.model_dump() for h in analysis.hypotheses],
            "verification": {"evidence_ids": analysis.evidence_ids, "claims_verified": False},
        }

    def verify(state):
        if not verifier(state["evidence"]):
            raise ValueError("evidence changed during inference; re-index and retry")
        return {
            "status": "completed",
            "verification": {
                **state.get("verification", {}),
                "evidence_fresh": True,
                "tests_run": False,
            },
        }

    graph = StateGraph(InvestigationState)
    for name, fn in (
        ("validate", validate),
        ("plan", plan),
        ("retrieve", retrieve),
        ("clarify", clarify),
        ("analyze", analyze),
        ("verify", verify),
    ):
        graph.add_node(name, bounded(name, fn))
    graph.add_edge(START, "validate")
    graph.add_edge("validate", "plan")
    graph.add_edge("plan", "retrieve")
    graph.add_conditional_edges("retrieve", lambda s: "analyze" if s["evidence"] else "clarify")
    graph.add_edge("clarify", "retrieve")
    graph.add_edge("analyze", "verify")
    graph.add_edge("verify", END)
    return graph.compile(checkpointer=checkpointer)


def run_investigation(
    retriever,
    model,
    request,
    *,
    checkpoint_path: Path | None = None,
    task_id="local",
    resume=None,
    **options,
) -> InvestigationState:
    initial = {"request": request, "status": "running", "step_count": 0, "tool_call_count": 0}
    config = {"recursion_limit": 16, "configurable": {"thread_id": task_id}}
    if checkpoint_path:
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        with SqliteSaver.from_conn_string(str(checkpoint_path)) as saver:
            graph = build_investigation_graph(retriever, model, checkpointer=saver, **options)
            result = graph.invoke(Command(resume=resume) if resume is not None else initial, config)
    else:
        result = build_investigation_graph(retriever, model, **options).invoke(initial, config)
    if result.get("__interrupt__"):
        result["status"] = "awaiting_input"
        result["answer"] = result["__interrupt__"][0].value["question"]
        del result["__interrupt__"]
    return result
