"""Guardrail layer — content safety, PII redaction, and output validation.

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                     INGESTION PATH                          │
    │  upload → sanitize() → [hidden text / malform detect]       │
    │         → classify_source_trust()                           │
    │         → redact_pii() on raw text                          │
    │         → persist → chunk → embed                           │
    └─────────────────────────────────────────────────────────────┘
    ┌─────────────────────────────────────────────────────────────┐
    │                     RETRIEVAL PATH                          │
    │  query → retrieve chunks                                    │
    │        → scan_prompt_injection() on each chunk              │
    │        → isolate untrusted sources in prompt                │
    │        → generate answer via LLM                            │
    │        → validate_output() on LLM response                  │
    │        → redact_pii() on final answer                       │
    │        → return (or queue for human review)                  │
    └─────────────────────────────────────────────────────────────┘

    All blocked/flagged events → security_events table.
"""
