"""
src.rag.ops — Observability, tracing, and evaluation.

Responsibility:
    Instrument the RAG pipeline with structured logs, traces, and metrics
    so every retrieval can be audited and measured.

Planned modules:
    - tracing.py      — OpenTelemetry spans for embed → retrieve → generate
    - metrics.py      — counters / histograms (latency, hit-rate, chunk utilisation)
    - eval.py         — offline evaluation helpers (MRR, Recall@K, faithfulness)
"""
