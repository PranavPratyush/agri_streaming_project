"""Evaluation harness for Agronomy RAG retrieval against gold benchmark set."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List

from agri_agronomy_rag.retriever import retrieve_agronomy_guidance

logger = logging.getLogger("agri_agronomy_rag.eval")


def run_retrieval_evaluation(
    gold_set_path: Path,
    chroma_dir: Path,
    k: int = 3,
    threshold: float = 0.45,
) -> Dict[str, Any]:
    """Runs gold benchmark queries, computing Precision@k, Recall@k, and MRR."""
    data = json.loads(gold_set_path.read_text(encoding="utf-8"))
    queries: List[Dict[str, Any]] = data.get("queries", [])

    results_per_query: List[Dict[str, Any]] = []
    latencies: List[float] = []

    mrr_sum = 0.0
    recall_hits = 0
    precision_sum = 0.0

    for item in queries:
        q_id = item["query_id"]
        q_text = item["query"]
        target_sources = item.get("target_source_ids", [])
        expected_prefix = item.get("expected_citation_prefix", "")

        t0 = time.perf_counter()
        bundle = retrieve_agronomy_guidance(
            query=q_text,
            limit=k,
            threshold=threshold,
            persist_dir=chroma_dir,
        )
        latency_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(latency_ms)

        retrieved_sources = [c.source_id for c in bundle.chunks]
        retrieved_citations = [c.citation_id for c in bundle.chunks]

        # Check precision@k: fraction of retrieved chunks that match target_sources or expected_prefix
        matches = 0
        first_correct_rank = None

        for rank, chunk in enumerate(bundle.chunks, 1):
            is_match = False
            if chunk.source_id in target_sources:
                is_match = True
            elif expected_prefix and chunk.citation_id.startswith(expected_prefix):
                is_match = True

            if is_match:
                matches += 1
                if first_correct_rank is None:
                    first_correct_rank = rank

        p_at_k = matches / k if k > 0 else 0.0
        r_at_k = 1.0 if matches > 0 else 0.0
        reciprocal_rank = (1.0 / first_correct_rank) if first_correct_rank else 0.0

        precision_sum += p_at_k
        recall_hits += 1 if r_at_k > 0 else 0
        mrr_sum += reciprocal_rank

        results_per_query.append({
            "query_id": q_id,
            "query": q_text,
            "target_sources": target_sources,
            "retrieved_citations": retrieved_citations,
            "precision_at_k": round(p_at_k, 4),
            "recall_at_k": round(r_at_k, 4),
            "reciprocal_rank": round(reciprocal_rank, 4),
            "latency_ms": round(latency_ms, 2),
        })

    n = len(queries)
    mean_precision = precision_sum / n if n > 0 else 0.0
    mean_recall = recall_hits / n if n > 0 else 0.0
    mean_mrr = mrr_sum / n if n > 0 else 0.0
    avg_latency = sum(latencies) / n if n > 0 else 0.0

    report = {
        "benchmark_set_size": n,
        "evaluated_at_k": k,
        "relevance_threshold": threshold,
        "corpus_version": data.get("corpus_version", "unknown"),
        "metrics": {
            "mean_precision_at_k": round(mean_precision, 4),
            "mean_recall_at_k": round(mean_recall, 4),
            "mean_reciprocal_rank": round(mean_mrr, 4),
            "mean_latency_ms": round(avg_latency, 2),
        },
        "query_results": results_per_query,
    }
    return report

