from __future__ import annotations

import math
import time


def evaluate(cases, retrieve):
    results = []
    for case in cases:
        start = time.perf_counter()
        items = retrieve(case["query"])
        paths = list(dict.fromkeys(item["path"] for item in items))[:5]
        expected = set(case["expected_paths"])
        hits = expected.intersection(paths)
        rank = next((i for i, path in enumerate(paths, 1) if path in expected), None)
        results.append(
            {
                "task_id": case["task_id"],
                "recall_at_5": len(hits) / len(expected),
                "reciprocal_rank": 1 / rank if rank else 0,
                "latency_ms": (time.perf_counter() - start) * 1000,
                "paths": paths,
            }
        )
    count = len(results)
    latency = sorted(r["latency_ms"] for r in results)
    return {
        "cases": count,
        "recall_at_5": sum(r["recall_at_5"] for r in results) / max(count, 1),
        "mrr": sum(r["reciprocal_rank"] for r in results) / max(count, 1),
        "p50_ms": latency[math.ceil(count * 0.5) - 1] if count else 0,
        "p95_ms": latency[math.ceil(count * 0.95) - 1] if count else 0,
        "results": results,
    }
