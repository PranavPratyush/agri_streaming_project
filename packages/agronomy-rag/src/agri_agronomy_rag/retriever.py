"""Read-only agronomy retrieval service returning typed EvidenceBundle containers."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from agri_agronomy_rag.models import AgronomyMetadataFilter, EvidenceBundle, EvidenceChunk
from agri_agronomy_rag.store import (
    AgronomyVectorStore,
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL_NAME,
)

logger = logging.getLogger("agri_agronomy_rag.retriever")

DEFAULT_RELEVANCE_THRESHOLD = 0.50


class AgronomyRetriever:
    """Provides typed, metadata-filtered, citation-grounded retrieval over verified agronomy literature."""

    def __init__(self, vector_store: AgronomyVectorStore) -> None:
        self.vector_store = vector_store

    def retrieve(
        self,
        query: str,
        filters: Optional[AgronomyMetadataFilter] = None,
        limit: int = 3,
        threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
        investigation_id: Optional[str] = None,
    ) -> EvidenceBundle:
        """Executes a dense vector similarity query with metadata filtering and relevance gating."""
        query_id = str(uuid.uuid4())
        corpus_version = self.vector_store.get_corpus_version()
        applied_filters: Dict[str, Any] = {}

        if not query or not query.strip():
            return EvidenceBundle(
                query_id=query_id,
                investigation_id=investigation_id,
                query_text="",
                corpus_version=corpus_version,
                embedding_model=EMBEDDING_MODEL_NAME,
                embedding_dimensions=EMBEDDING_DIMENSIONS,
                evidence_status="EVIDENCE_INSUFFICIENT",
                no_result_reason="Query string was empty or contained only whitespace.",
                chunks=[],
                total_chunks_retrieved=0,
                filters_applied=None,
                limit_requested=limit,
                relevance_threshold=threshold,
            )

        # Build Chroma 'where' filter
        where_conditions: List[Dict[str, Any]] = []
        if filters:
            if filters.crop and filters.crop != "unknown":
                where_conditions.append({"crop": filters.crop})
                applied_filters["crop"] = filters.crop
            if filters.topic:
                where_conditions.append({"topic": filters.topic})
                applied_filters["topic"] = filters.topic
            if filters.soil and filters.soil != "unknown":
                where_conditions.append({"soil": filters.soil})
                applied_filters["soil"] = filters.soil
            if filters.document_type:
                where_conditions.append({"document_type": filters.document_type})
                applied_filters["document_type"] = filters.document_type

        where_clause: Optional[Dict[str, Any]] = None
        if len(where_conditions) == 1:
            where_clause = where_conditions[0]
        elif len(where_conditions) > 1:
            where_clause = {"$and": where_conditions}

        # Query Chroma collection
        # Request more than limit to allow post-threshold gating
        n_results = max(limit * 2, 6)
        query_kwargs: Dict[str, Any] = {
            "query_texts": [query.strip()],
            "n_results": min(n_results, max(1, self.vector_store.count())),
        }
        if where_clause:
            query_kwargs["where"] = where_clause

        try:
            results = self.vector_store.collection.query(**query_kwargs)
        except Exception as exc:
            logger.error("Chroma query failed: %s", exc)
            return EvidenceBundle(
                query_id=query_id,
                investigation_id=investigation_id,
                query_text=query,
                corpus_version=corpus_version,
                embedding_model=EMBEDDING_MODEL_NAME,
                embedding_dimensions=EMBEDDING_DIMENSIONS,
                evidence_status="EVIDENCE_INSUFFICIENT",
                no_result_reason=f"Vector database query exception: {exc}",
                chunks=[],
                total_chunks_retrieved=0,
                filters_applied=applied_filters or None,
                limit_requested=limit,
                relevance_threshold=threshold,
            )

        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0] if "distances" in results else [0.0] * len(ids)

        qualified_chunks: List[EvidenceChunk] = []

        for c_id, text, meta, dist in zip(ids, documents, metadatas, distances):
            # Chroma with cosine space returns cosine distance = 1.0 - cosine_similarity
            # For squared L2 or cosine distance, normalized similarity:
            sim_score = max(0.0, min(1.0, 1.0 - (float(dist) / 2.0 if float(dist) > 1.0 else float(dist))))
            # If hnsw:space is cosine, dist is cosine distance directly:
            sim_score = max(0.0, min(1.0, 1.0 - float(dist)))

            if sim_score >= threshold:
                chunk = EvidenceChunk(
                    citation_id=c_id,
                    source_id=meta.get("source_id", "unknown"),
                    document_title=meta.get("document_title", "Unknown Title"),
                    author_institution=meta.get("author_institution", "Unknown Author"),
                    section_heading=meta.get("section_heading", "General"),
                    page_or_section=meta.get("page_or_section", "General Section"),
                    canonical_url=meta.get("canonical_url", ""),
                    text=text,
                    crop=meta.get("crop", "unknown"),
                    region=meta.get("region", "unknown"),
                    soil=meta.get("soil", "unknown"),
                    growth_stage=meta.get("growth_stage", "unknown"),
                    document_type=meta.get("document_type", "unknown"),
                    topic=meta.get("topic", "general"),
                    relevance_score=round(sim_score, 4),
                    retrieval_method="dense_cosine_similarity",
                )
                qualified_chunks.append(chunk)

            if len(qualified_chunks) >= limit:
                break

        if not qualified_chunks:
            logger.info("No evidence chunks met relevance threshold %.2f for query '%s'", threshold, query)
            return EvidenceBundle(
                query_id=query_id,
                investigation_id=investigation_id,
                query_text=query,
                corpus_version=corpus_version,
                embedding_model=EMBEDDING_MODEL_NAME,
                embedding_dimensions=EMBEDDING_DIMENSIONS,
                evidence_status="EVIDENCE_INSUFFICIENT",
                no_result_reason=(
                    f"No retrieved agronomy evidence exceeded similarity threshold {threshold:.2f} "
                    f"for query: '{query}'."
                ),
                chunks=[],
                total_chunks_retrieved=0,
                filters_applied=applied_filters or None,
                limit_requested=limit,
                relevance_threshold=threshold,
            )

        return EvidenceBundle(
            query_id=query_id,
            investigation_id=investigation_id,
            query_text=query,
            corpus_version=corpus_version,
            embedding_model=EMBEDDING_MODEL_NAME,
            embedding_dimensions=EMBEDDING_DIMENSIONS,
            retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
            evidence_status="SUCCESS",
            no_result_reason=None,
            chunks=qualified_chunks,
            total_chunks_retrieved=len(qualified_chunks),
            filters_applied=applied_filters or None,
            limit_requested=limit,
            relevance_threshold=threshold,
        )


# Global singleton access for clean integration
_DEFAULT_RETRIEVER: Optional[AgronomyRetriever] = None


def get_default_retriever(persist_dir: Path | str | None = None) -> AgronomyRetriever:
    """Returns or initializes the singleton AgronomyRetriever."""
    global _DEFAULT_RETRIEVER
    if _DEFAULT_RETRIEVER is None:
        if persist_dir is None:
            # Resolve relative to repo root
            repo_root = Path(__file__).resolve().parents[4]
            persist_dir = repo_root / "knowledge" / "chroma_db"
        store = AgronomyVectorStore(persist_dir=persist_dir)
        _DEFAULT_RETRIEVER = AgronomyRetriever(store)
    return _DEFAULT_RETRIEVER


def retrieve_agronomy_guidance(
    query: str,
    filters: Optional[AgronomyMetadataFilter] = None,
    limit: int = 3,
    threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    investigation_id: Optional[str] = None,
    persist_dir: Path | str | None = None,
) -> EvidenceBundle:
    """Public integration interface for the Stage 16 Agronomy Knowledge Agent."""
    retriever = get_default_retriever(persist_dir=persist_dir)
    return retriever.retrieve(
        query=query,
        filters=filters,
        limit=limit,
        threshold=threshold,
        investigation_id=investigation_id,
    )
