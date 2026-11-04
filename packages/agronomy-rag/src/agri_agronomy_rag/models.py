"""Pydantic schemas and typed data contracts for the Agronomy RAG retrieval service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class SourceMetadata(BaseModel):
    """Metadata representing an official, registered agronomic reference document."""

    source_id: str = Field(description="Stable unique identifier for the document (e.g., UASB-POP-RAGI-2022)")
    title: str = Field(description="Full title of the publication")
    author_institution: str = Field(description="Author(s) or publishing institution")
    publication_date: str = Field(description="Publication date or release version (YYYY-MM-DD or YYYY)")
    canonical_url: str = Field(description="Official or permanent URL where the document is hosted")
    access_date: str = Field(description="Date on which the document was accessed and archived")
    document_type: str = Field(description="Type of document (e.g., standard_reference_manual, university_extension_guide)")
    language: str = Field(default="en", description="Document language code")
    crop_applicability: str = Field(default="unknown", description="Crop or cultivar applicability stated by source")
    region_applicability: str = Field(default="unknown", description="Geographic or agro-climatic region applicability")
    soil_applicability: str = Field(default="unknown", description="Soil type applicability (e.g., red sandy loam)")
    growth_stage_applicability: str = Field(default="unknown", description="Semicolon-separated growth stages")
    license_rights: str = Field(description="Usage rights, copyright, or licensing terms")
    retrieval_status: str = Field(default="PARSED_AND_INDEXED", description="Ingestion status in the knowledge base")
    known_limitations: str = Field(default="", description="Stated or evaluated limitations of the document")


class EvidenceChunk(BaseModel):
    """A granular, citation-addressable passage retrieved from the knowledge base."""

    citation_id: str = Field(description="Stable addressable citation ID (e.g., UASB-POP-RAGI-2022:SEC02:CH01)")
    source_id: str = Field(description="Foreign key back to SourceMetadata")
    document_title: str = Field(description="Title of parent document")
    author_institution: str = Field(description="Author or publishing institution")
    section_heading: str = Field(description="Heading of the section containing this chunk")
    page_or_section: str = Field(description="Section or page identifier for human audit")
    canonical_url: str = Field(description="Canonical URL for grounding")
    text: str = Field(description="Extracted text excerpt of the chunk")
    crop: str = Field(default="unknown", description="Crop metadata associated with chunk")
    region: str = Field(default="unknown", description="Region metadata associated with chunk")
    soil: str = Field(default="unknown", description="Soil metadata associated with chunk")
    growth_stage: str = Field(default="unknown", description="Growth stage metadata associated with chunk")
    document_type: str = Field(default="unknown", description="Document type classification")
    topic: str = Field(default="general", description="Subject matter topic (e.g., water_management, drought, soil)")
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Normalized similarity or relevance score")
    retrieval_method: str = Field(default="dense_cosine_similarity", description="Method used to retrieve chunk")


class AgronomyMetadataFilter(BaseModel):
    """Metadata filters for narrowing agronomy retrieval without hallucination."""

    crop: Optional[str] = Field(default=None, description="Target crop (e.g., 'Finger Millet', 'Ragi')")
    region: Optional[str] = Field(default=None, description="Target region (e.g., 'Karnataka', 'Kolar')")
    soil: Optional[str] = Field(default=None, description="Soil type (e.g., 'Red sandy loam')")
    growth_stage: Optional[str] = Field(default=None, description="Growth stage (e.g., 'flowering', 'tillering')")
    document_type: Optional[str] = Field(default=None, description="Document type filter")
    topic: Optional[str] = Field(default=None, description="Topic filter (e.g., 'water_management', 'drought')")


class EvidenceBundle(BaseModel):
    """Validated, typed evidence container returned to the Stage 16 Agronomy Knowledge Agent."""

    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for this retrieval request")
    investigation_id: Optional[str] = Field(default=None, description="Investigation session ID if passed by caller")
    query_text: str = Field(description="Original search query string")
    corpus_version: str = Field(description="Version hash or identifier of the ingested corpus")
    embedding_model: str = Field(description="Identifier and version of the embedding model used")
    embedding_dimensions: int = Field(description="Dimensionality of embedding vectors (e.g., 384)")
    retrieval_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of retrieval execution",
    )
    evidence_status: str = Field(
        description="'SUCCESS' if relevant evidence found; 'EVIDENCE_INSUFFICIENT' if no chunk met threshold"
    )
    no_result_reason: Optional[str] = Field(
        default=None, description="Explicit explanation when evidence_status is EVIDENCE_INSUFFICIENT"
    )
    chunks: List[EvidenceChunk] = Field(default_factory=list, description="Ranked list of retrieved evidence chunks")
    total_chunks_retrieved: int = Field(default=0, description="Number of chunks matching the query above threshold")
    filters_applied: Optional[dict[str, Any]] = Field(default=None, description="Active metadata filters during query")
    limit_requested: int = Field(default=3, description="Maximum chunks requested by caller")
    relevance_threshold: float = Field(default=0.60, description="Minimum similarity threshold enforced")


class CitationValidationResult(BaseModel):
    """Audit result verifying whether citations in an AI advisory resolve to genuine retrieved evidence."""

    is_valid: bool = Field(description="True if all extracted citations resolve to verified evidence")
    cited_ids: List[str] = Field(default_factory=list, description="All citation IDs found in the advisory text")
    resolved_ids: List[str] = Field(default_factory=list, description="Citation IDs successfully resolved to bundle")
    unresolved_ids: List[str] = Field(default_factory=list, description="Hallucinated or unknown citation IDs")
    rejection_reasons: List[str] = Field(default_factory=list, description="Diagnostic reasons if validation fails")

