"""RAGOps — observability and evaluation for the RAG platform.

Architecture:

    ┌──────────────────────────────────────────────────┐
    │                 RAGOps Layer                      │
    │                                                  │
    │  tracing.py     SpanCollector, Span              │
    │  judge.py       LLM-as-judge protocol            │
    │  metrics/       context_relevance, groundedness,  │
    │                 answer_relevance                  │
    │  eval_harness   dataset runner + case evaluator   │
    │  report.py      Markdown / JSON report generator  │
    └──────────────────────────────────────────────────┘
"""
