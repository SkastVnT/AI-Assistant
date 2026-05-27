"""GraphRAG extension — optional knowledge graph layer for the RAG platform.

Architecture:
    ┌──────────────────────────────────────────────────────────────────┐
    │                      GraphRAG Extension                          │
    │                                                                  │
    │  ┌──────────┐   ┌───────────┐   ┌──────────┐   ┌────────────┐  │
    │  │ Entity   │   │ Graph     │   │ Graph    │   │ Community  │  │
    │  │ Extractor│──▶│ Store     │──▶│ Indexer  │──▶│ Detector   │  │
    │  └──────────┘   │(Abstract) │   └──────────┘   └────────────┘  │
    │                 └───────────┘                                    │
    │                      │                                           │
    │          ┌───────────┴───────────┐                              │
    │          ▼                       ▼                              │
    │  ┌──────────────┐   ┌────────────────┐                         │
    │  │ Local Search │   │ Global Search  │                         │
    │  │ (Entity      │   │ (Community     │                         │
    │  │  neighbours) │   │  summaries)    │                         │
    │  └──────────────┘   └────────────────┘                         │
    │          │                       │                              │
    │          └───────────┬───────────┘                              │
    │                      ▼                                          │
    │              ┌──────────────┐                                   │
    │              │ Query Router │ ←── decides vector|graph|hybrid   │
    │              └──────────────┘                                   │
    └──────────────────────────────────────────────────────────────────┘

Modules:
    store.py        — GraphStore protocol + PostgresGraphStore + Neo4jGraphStore
    extraction.py   — LLM-based entity & relationship extraction
    indexer.py       — Graph indexing workflow (extract → store → embed → community)
    community.py    — Community detection and summarization
    local_search.py — Entity-neighbourhood retrieval
    global_search.py— Community-summary retrieval
    router.py       — Query routing (vector vs graph vs hybrid)
    types.py        — Shared dataclasses for the graph layer
"""
