# Retrieval baseline

25 synthetic retrieval queries, 10 MIT fixture modules; no diagnosis or patch-quality claims

OS: Windows-11-10.0.26300-SP0

Python: 3.14.7

Recall@5: 1.000

MRR: 1.000

p50: 3.29 ms; p95: 5.10 ms

Reproduce: `.venv/Scripts/python.exe scripts/run_evaluation.py`. Fixture code is covered by the project MIT license. Semantic retrieval requires a configured local embedding model and a separate comparison.
