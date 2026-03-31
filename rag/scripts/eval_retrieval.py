"""Evaluation harness — compare retrieval strategies.

Compares dense-only, lexical-only, hybrid (RRF), and hybrid+rerank on a
set of query/ground-truth pairs. Computes Precision@K, Recall@K, MRR@K,
and NDCG@K for each strategy.

Usage (offline, with in-memory fakes):
    python -m scripts.eval_retrieval

For production evaluation against a live database:
    EVAL_MODE=live python -m scripts.eval_retrieval

The script outputs a formatted table comparing all strategies.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import time
import uuid
from dataclasses import dataclass

from libs.retrieval.fusion import reciprocal_rank_fusion
from libs.retrieval.rerankers import (
    SearchResult,
    _word_overlap_scores,
)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("eval_retrieval")


# ── Evaluation data structures ─────────────────────────────────────────────


@dataclass
class EvalQuery:
    """A query with known relevant chunk IDs for evaluation."""

    query: str
    relevant_chunk_ids: set[uuid.UUID]
    query_id: str = ""


@dataclass
class StrategyResult:
    """Results from one strategy on one query."""

    strategy: str
    returned_ids: list[uuid.UUID]
    scores: list[float]
    latency_ms: int = 0


@dataclass
class EvalMetrics:
    """Aggregated metrics for one strategy across all queries."""

    strategy: str
    precision_at_k: float = 0.0
    recall_at_k: float = 0.0
    mrr: float = 0.0
    ndcg: float = 0.0
    avg_latency_ms: float = 0.0
    num_queries: int = 0


# ── Metric computations ───────────────────────────────────────────────────


def precision_at_k(returned: list[uuid.UUID], relevant: set[uuid.UUID], k: int) -> float:
    """Precision@K: fraction of top-K results that are relevant."""
    top = returned[:k]
    if not top:
        return 0.0
    return len(set(top) & relevant) / len(top)


def recall_at_k(returned: list[uuid.UUID], relevant: set[uuid.UUID], k: int) -> float:
    """Recall@K: fraction of relevant docs found in top-K."""
    if not relevant:
        return 0.0
    top = returned[:k]
    return len(set(top) & relevant) / len(relevant)


def reciprocal_rank(returned: list[uuid.UUID], relevant: set[uuid.UUID]) -> float:
    """MRR: 1/rank of the first relevant result."""
    for i, rid in enumerate(returned):
        if rid in relevant:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(returned: list[uuid.UUID], relevant: set[uuid.UUID], k: int) -> float:
    """NDCG@K: normalized discounted cumulative gain."""
    top = returned[:k]
    dcg = sum(
        (1.0 if rid in relevant else 0.0) / math.log2(i + 2)
        for i, rid in enumerate(top)
    )
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    if idcg == 0:
        return 0.0
    return dcg / idcg


def compute_metrics(
    strategy: str,
    results: list[StrategyResult],
    queries: list[EvalQuery],
    k: int,
) -> EvalMetrics:
    """Compute aggregated metrics for a strategy."""
    n = len(results)
    if n == 0:
        return EvalMetrics(strategy=strategy)

    p_sum = r_sum = mrr_sum = ndcg_sum = lat_sum = 0.0
    for sr, eq in zip(results, queries, strict=True):
        p_sum += precision_at_k(sr.returned_ids, eq.relevant_chunk_ids, k)
        r_sum += recall_at_k(sr.returned_ids, eq.relevant_chunk_ids, k)
        mrr_sum += reciprocal_rank(sr.returned_ids, eq.relevant_chunk_ids)
        ndcg_sum += ndcg_at_k(sr.returned_ids, eq.relevant_chunk_ids, k)
        lat_sum += sr.latency_ms

    return EvalMetrics(
        strategy=strategy,
        precision_at_k=p_sum / n,
        recall_at_k=r_sum / n,
        mrr=mrr_sum / n,
        ndcg=ndcg_sum / n,
        avg_latency_ms=lat_sum / n,
        num_queries=n,
    )


# ── Synthetic evaluation corpus ───────────────────────────────────────────


def _build_synthetic_corpus() -> tuple[list[SearchResult], list[EvalQuery]]:
    """Build a small synthetic corpus for offline evaluation."""
    chunks: list[SearchResult] = []
    queries: list[EvalQuery] = []

    # Corpus: 20 chunks across 4 topics
    topics = {
        "revenue": [
            "Q4 2024 revenue was $48.2M, a 12% increase year-over-year.",
            "Revenue growth was driven primarily by enterprise subscriptions.",
            "Annual recurring revenue (ARR) reached $180M by end of fiscal year.",
            "The SaaS revenue model shifted from perpetual licenses.",
            "Revenue recognition follows ASC 606 guidelines for contracts.",
        ],
        "engineering": [
            "The platform runs on Kubernetes with auto-scaling enabled.",
            "Microservices architecture uses gRPC for internal communication.",
            "CI/CD pipeline deploys to production via GitHub Actions.",
            "Database sharding was implemented for horizontal scalability.",
            "The search infrastructure uses pgvector for similarity search.",
        ],
        "hr_policy": [
            "Remote work policy allows fully distributed teams.",
            "Annual performance reviews occur in Q1 each year.",
            "Stock options vest over a 4-year cliff schedule.",
            "The company offers 20 days of paid time off annually.",
            "Health insurance covers dental and vision for all employees.",
        ],
        "security": [
            "All data at rest is encrypted using AES-256.",
            "SOC 2 Type II audit was completed in October 2024.",
            "Multi-factor authentication is mandatory for all employees.",
            "Incident response playbook is tested quarterly.",
            "RBAC controls access to production environments.",
        ],
    }

    chunk_map: dict[str, list[uuid.UUID]] = {}
    doc_id = uuid.uuid4()
    ver_id = uuid.uuid4()

    for topic, contents in topics.items():
        chunk_map[topic] = []
        for i, content in enumerate(contents):
            cid = uuid.uuid4()
            chunk_map[topic].append(cid)
            chunks.append(
                SearchResult(
                    chunk_id=cid,
                    document_id=doc_id,
                    version_id=ver_id,
                    content=content,
                    score=0.0,
                    metadata={"topic": topic},
                    filename=f"{topic}.pdf",
                    chunk_index=i,
                    sensitivity_level="internal",
                    language="en",
                    document_title=f"{topic.title()} Report",
                    version_number=1,
                )
            )

    # Eval queries
    queries = [
        EvalQuery(
            query="What was the Q4 revenue?",
            relevant_chunk_ids=set(chunk_map["revenue"][:3]),
            query_id="q1",
        ),
        EvalQuery(
            query="How does the CI/CD pipeline work?",
            relevant_chunk_ids=set(chunk_map["engineering"][2:4]),
            query_id="q2",
        ),
        EvalQuery(
            query="What is the remote work policy?",
            relevant_chunk_ids={chunk_map["hr_policy"][0]},
            query_id="q3",
        ),
        EvalQuery(
            query="SOC 2 audit compliance and encryption",
            relevant_chunk_ids=set(chunk_map["security"][:2]),
            query_id="q4",
        ),
        EvalQuery(
            query="stock options vesting schedule",
            relevant_chunk_ids={chunk_map["hr_policy"][2]},
            query_id="q5",
        ),
        EvalQuery(
            query="pgvector search and database sharding",
            relevant_chunk_ids=set(chunk_map["engineering"][3:5]),
            query_id="q6",
        ),
    ]

    return chunks, queries


# ── Strategy simulators ────────────────────────────────────────────────────


def _simulate_dense_search(
    query: str, corpus: list[SearchResult], top_k: int
) -> list[SearchResult]:
    """Simulate dense search using word overlap as proxy for embedding similarity."""
    q_words = set(query.lower().split())

    scored = []
    for chunk in corpus:
        c_words = set(chunk.content.lower().split())
        if not q_words:
            continue
        # Jaccard-like similarity as embedding proxy
        overlap = len(q_words & c_words)
        union = len(q_words | c_words)
        sim = overlap / union if union > 0 else 0.0
        scored.append(
            SearchResult(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                version_id=chunk.version_id,
                content=chunk.content,
                score=sim,
                metadata=chunk.metadata,
                filename=chunk.filename,
                chunk_index=chunk.chunk_index,
                sensitivity_level=chunk.sensitivity_level,
                language=chunk.language,
                document_title=chunk.document_title,
                version_number=chunk.version_number,
            )
        )
    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:top_k]


def _simulate_lexical_search(
    query: str, corpus: list[SearchResult], top_k: int
) -> list[SearchResult]:
    """Simulate BM25/lexical search using term frequency scoring."""
    q_terms = query.lower().split()
    term_set = set(q_terms)

    scored = []
    for chunk in corpus:
        c_lower = chunk.content.lower()
        c_words = c_lower.split()
        # Simple TF scoring: count of query term occurrences / doc length
        tf_score = sum(c_words.count(t) for t in term_set)
        if len(c_words) > 0:
            tf_score = tf_score / (len(c_words) + 10)  # +10 as smoothing
        scored.append(
            SearchResult(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                version_id=chunk.version_id,
                content=chunk.content,
                score=tf_score,
                metadata=chunk.metadata,
                filename=chunk.filename,
                chunk_index=chunk.chunk_index,
                sensitivity_level=chunk.sensitivity_level,
                language=chunk.language,
                document_title=chunk.document_title,
                version_number=chunk.version_number,
            )
        )
    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:top_k]


async def _simulate_rerank(
    query: str, candidates: list[SearchResult], top_n: int
) -> list[SearchResult]:
    """Simulate reranking using word overlap (cross-encoder proxy)."""
    pairs = [(query, c.content) for c in candidates]
    scores = _word_overlap_scores(pairs)
    combined = list(zip(candidates, scores, strict=True))
    combined.sort(key=lambda x: x[1], reverse=True)
    results = []
    for chunk, score in combined[:top_n]:
        results.append(
            SearchResult(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                version_id=chunk.version_id,
                content=chunk.content,
                score=score,
                metadata=chunk.metadata,
                filename=chunk.filename,
                chunk_index=chunk.chunk_index,
                sensitivity_level=chunk.sensitivity_level,
                language=chunk.language,
                document_title=chunk.document_title,
                version_number=chunk.version_number,
            )
        )
    return results


# ── Main evaluation ───────────────────────────────────────────────────────


async def run_evaluation(k: int = 5) -> dict[str, EvalMetrics]:
    """Run evaluation of all strategies and return metrics."""
    corpus, queries = _build_synthetic_corpus()

    strategies = {
        "dense_only": [],
        "lexical_only": [],
        "hybrid_rrf": [],
        "hybrid_rrf+rerank": [],
    }

    for eq in queries:
        # Dense only
        t0 = time.perf_counter()
        dense = _simulate_dense_search(eq.query, corpus, top_k=20)
        dense_ms = int((time.perf_counter() - t0) * 1000)
        strategies["dense_only"].append(
            StrategyResult(
                strategy="dense_only",
                returned_ids=[r.chunk_id for r in dense[:k]],
                scores=[r.score for r in dense[:k]],
                latency_ms=dense_ms,
            )
        )

        # Lexical only
        t0 = time.perf_counter()
        lexical = _simulate_lexical_search(eq.query, corpus, top_k=20)
        lex_ms = int((time.perf_counter() - t0) * 1000)
        strategies["lexical_only"].append(
            StrategyResult(
                strategy="lexical_only",
                returned_ids=[r.chunk_id for r in lexical[:k]],
                scores=[r.score for r in lexical[:k]],
                latency_ms=lex_ms,
            )
        )

        # Hybrid RRF
        t0 = time.perf_counter()
        fused = reciprocal_rank_fusion(
            [dense, lexical], k=60, weights=[1.0, 1.0], top_k=20
        )
        fused_ms = int((time.perf_counter() - t0) * 1000)
        strategies["hybrid_rrf"].append(
            StrategyResult(
                strategy="hybrid_rrf",
                returned_ids=[r.chunk_id for r in fused[:k]],
                scores=[r.score for r in fused[:k]],
                latency_ms=dense_ms + lex_ms + fused_ms,
            )
        )

        # Hybrid RRF + Rerank
        t0 = time.perf_counter()
        reranked = await _simulate_rerank(eq.query, fused[:20], top_n=k)
        rerank_ms = int((time.perf_counter() - t0) * 1000)
        strategies["hybrid_rrf+rerank"].append(
            StrategyResult(
                strategy="hybrid_rrf+rerank",
                returned_ids=[r.chunk_id for r in reranked],
                scores=[r.score for r in reranked],
                latency_ms=dense_ms + lex_ms + fused_ms + rerank_ms,
            )
        )

    metrics = {}
    for name, results in strategies.items():
        metrics[name] = compute_metrics(name, results, queries, k)

    return metrics


def print_metrics_table(metrics: dict[str, EvalMetrics], k: int = 5) -> str:
    """Format metrics into a readable table."""
    p_label = f"P@{k}"
    r_label = f"R@{k}"
    n_label = f"NDCG@{k}"
    header = (
        f"{'Strategy':<25} {p_label:<8} {r_label:<8} "
        f"{'MRR':<8} {n_label:<9} {'Latency(ms)':<12}"
    )
    sep = "-" * len(header)
    lines = [sep, header, sep]

    for name in ["dense_only", "lexical_only", "hybrid_rrf", "hybrid_rrf+rerank"]:
        m = metrics[name]
        lines.append(
            f"{m.strategy:<25} {m.precision_at_k:<8.4f} {m.recall_at_k:<8.4f} "
            f"{m.mrr:<8.4f} {m.ndcg:<9.4f} {m.avg_latency_ms:<12.1f}"
        )
    lines.append(sep)
    return "\n".join(lines)


async def main() -> None:
    k = 5
    print(f"\n=== Retrieval Strategy Evaluation (K={k}) ===\n")
    metrics = await run_evaluation(k=k)
    table = print_metrics_table(metrics, k=k)
    print(table)

    # JSON output for CI/CD integration
    print("\n--- JSON metrics ---")
    json_out = {
        name: {
            "precision_at_k": round(m.precision_at_k, 4),
            "recall_at_k": round(m.recall_at_k, 4),
            "mrr": round(m.mrr, 4),
            "ndcg": round(m.ndcg, 4),
            "avg_latency_ms": round(m.avg_latency_ms, 1),
        }
        for name, m in metrics.items()
    }
    print(json.dumps(json_out, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
