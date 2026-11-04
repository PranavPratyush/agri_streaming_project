"""Agronomy Knowledge Agent implementation.

Queries the Stage 15 Agronomy RAG vector retrieval service, selecting authoritative evidence
chunks and certifying citations without hallucination.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel

from agri_agronomy_rag.models import AgronomyMetadataFilter, EvidenceBundle
from agri_agronomy_rag.retriever import retrieve_agronomy_guidance
from agri_investigator.agents.base import BaseSpecialistAgent
from agri_investigator.models import AgentRole, AgronomyEvidenceRequest, FieldContextOutput

logger = logging.getLogger(__name__)


class AgronomyKnowledgeInput(BaseModel):
    """Input payload for Agronomy Knowledge Agent."""
    evidence_request: AgronomyEvidenceRequest
    field_context: FieldContextOutput
    chroma_dir: Optional[str] = None
    relevance_threshold: float = 0.45


class AgronomyKnowledgeOutput(BaseModel):
    """Output contract for Agronomy Knowledge Agent wrapping the EvidenceBundle."""
    evidence_status: str       # "EVIDENCE_FOUND" or "EVIDENCE_INSUFFICIENT"
    corpus_version: str
    query_used: str
    total_chunks: int
    chunks: list[Dict[str, Any]]
    no_result_reason: Optional[str] = None
    gaps: list[str] = []


class AgronomyKnowledgeAgent(BaseSpecialistAgent):
    """Specialist agent retrieving peer-reviewed and university-accredited agronomic evidence."""

    def __init__(self, chroma_dir: Optional[Path] = None, mock_mode: bool = False) -> None:
        super().__init__(
            role=AgentRole.AGRONOMY_KNOWLEDGE,
            name="Agronomy Knowledge Specialist",
            version="1.0.0",
            model_name="all-MiniLM-L6-v2-rag",
            mock_mode=mock_mode,
        )
        self.chroma_dir = chroma_dir

    def get_input_schema(self) -> type[BaseModel]:
        return AgronomyKnowledgeInput

    def get_output_schema(self) -> type[BaseModel]:
        return AgronomyKnowledgeOutput

    def _execute_core(self, validated_input: BaseModel) -> Tuple[BaseModel, int]:
        inp: AgronomyKnowledgeInput = validated_input  # type: ignore

        if self.mock_mode and "default" in self._mock_responses:
            return AgronomyKnowledgeOutput.model_validate(self._mock_responses["default"]), 30

        req = inp.evidence_request
        # For small targeted crop corpus, dense vector similarity across the audited finger millet
        # corpus provides highest recall without metadata string-mismatch exclusion
        filters = None

        p_dir = Path(inp.chroma_dir) if inp.chroma_dir else self.chroma_dir

        try:
            bundle: EvidenceBundle = retrieve_agronomy_guidance(
                query=req.query,
                filters=filters,
                limit=3,
                threshold=inp.relevance_threshold,
                persist_dir=p_dir,
            )
        except Exception as exc:
            logger.warning("RAG retrieval failed or vector store not found: %s. Emitting EVIDENCE_INSUFFICIENT.", exc)
            return AgronomyKnowledgeOutput(
                evidence_status="EVIDENCE_INSUFFICIENT",
                corpus_version="unknown",
                query_used=req.query,
                total_chunks=0,
                chunks=[],
                no_result_reason=f"Retrieval store unavailable or error: {str(exc)}",
                gaps=[req.query],
            ), 10

        chunks_data = [
            {
                "citation_id": c.citation_id,
                "source_id": c.source_id,
                "document_title": c.document_title,
                "section_heading": c.section_heading,
                "topic": c.topic,
                "canonical_url": c.canonical_url,
                "relevance_score": c.relevance_score,
                "text": c.text,
            }
            for c in bundle.chunks
        ]

        gaps = []
        if bundle.evidence_status == "EVIDENCE_INSUFFICIENT":
            gaps.append(f"Insufficient accredited evidence for query: {req.query}")

        output = AgronomyKnowledgeOutput(
            evidence_status=bundle.evidence_status,
            corpus_version=bundle.corpus_version,
            query_used=req.query,
            total_chunks=bundle.total_chunks_retrieved,
            chunks=chunks_data,
            no_result_reason=bundle.no_result_reason,
            gaps=gaps,
        )
        return output, 35
