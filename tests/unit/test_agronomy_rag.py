"""Unit tests for AgriKafka-Agent agronomy knowledge base, chunking, and grounded retrieval."""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from agri_agronomy_rag.ingest import (
    compute_corpus_version,
    load_source_register,
    parse_and_chunk_document,
)
from agri_agronomy_rag.models import (
    AgronomyMetadataFilter,
    CitationValidationResult,
    EvidenceBundle,
    EvidenceChunk,
    SourceMetadata,
)
from agri_agronomy_rag.retriever import AgronomyRetriever, retrieve_agronomy_guidance
from agri_agronomy_rag.store import AgronomyVectorStore
from agri_agronomy_rag.validator import CitationValidator


REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO_ROOT / "knowledge" / "corpus"
REGISTER_CSV = REPO_ROOT / "knowledge" / "source-register.csv"
CHROMA_DIR = REPO_ROOT / "knowledge" / "chroma_db"


def test_source_register_loading():
    """Verify source-register.csv loads with all mandatory fields and zero empty IDs."""
    registry = load_source_register(REGISTER_CSV)
    assert len(registry) >= 5
    assert "FAO-56-CH06" in registry
    assert "UASB-POP-RAGI-2022" in registry

    for source_id, meta in registry.items():
        assert meta.source_id == source_id
        assert len(meta.title) > 5
        assert len(meta.author_institution) > 2
        assert meta.canonical_url.startswith("http")
        assert meta.retrieval_status == "PARSED_AND_INDEXED"


def test_malformed_or_missing_source_register():
    """Verify loading a nonexistent register raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_source_register(Path("nonexistent/source-register.csv"))


def test_chunking_preserves_headings_and_page_sections():
    """Verify document parser extracts section headings and creates stable citation IDs."""
    registry = load_source_register(REGISTER_CSV)
    uasb_meta = registry["UASB-POP-RAGI-2022"]
    uasb_file = CORPUS_DIR / "UASB-POP-RAGI-2022.md"

    chunks = parse_and_chunk_document(uasb_file, uasb_meta)
    assert len(chunks) >= 3

    for chunk in chunks:
        assert chunk.source_id == "UASB-POP-RAGI-2022"
        assert chunk.citation_id.startswith("UASB-POP-RAGI-2022:SEC")
        assert len(chunk.section_heading) > 0
        assert chunk.page_or_section.startswith("Section ")
        assert chunk.crop == "Finger Millet (Ragi GPU-28)"
        assert "Alfisols" in chunk.soil or "red" in chunk.soil.lower()
        # Ensure context header is prepended
        assert "[SOURCE: UASB-POP-RAGI-2022" in chunk.text


def test_chunk_boundaries_and_no_empty_chunks():
    """Verify no chunk has empty text or zero words."""
    registry = load_source_register(REGISTER_CSV)
    fao_meta = registry["FAO-56-CH06"]
    fao_file = CORPUS_DIR / "FAO-56-CH06.md"

    chunks = parse_and_chunk_document(fao_file, fao_meta)
    for c in chunks:
        assert len(c.text.split()) > 15
        assert c.citation_id != ""


def test_corpus_version_deterministic_hash():
    """Verify compute_corpus_version produces identical hashes for identical content."""
    v1 = compute_corpus_version(CORPUS_DIR, REGISTER_CSV)
    v2 = compute_corpus_version(CORPUS_DIR, REGISTER_CSV)
    assert v1 == v2
    assert v1.startswith("v1.0-")


def test_empty_query_returns_evidence_insufficient():
    """Verify empty query immediately returns EVIDENCE_INSUFFICIENT without crashing."""
    bundle = retrieve_agronomy_guidance(query="", persist_dir=CHROMA_DIR)
    assert bundle.evidence_status == "EVIDENCE_INSUFFICIENT"
    assert bundle.total_chunks_retrieved == 0
    assert "empty" in bundle.no_result_reason.lower()


def test_out_of_domain_query_below_threshold():
    """Verify an irrelevant query (e.g. quantum cryptography) fails threshold check."""
    bundle = retrieve_agronomy_guidance(
        query="quantum entanglement cryptography in semiconductor silicon lasers",
        threshold=0.75,
        persist_dir=CHROMA_DIR,
    )
    assert bundle.evidence_status == "EVIDENCE_INSUFFICIENT"
    assert bundle.total_chunks_retrieved == 0
    assert "threshold" in bundle.no_result_reason.lower()


def test_metadata_filtering():
    """Verify metadata filtering returns only chunks matching the filter criteria."""
    filters = AgronomyMetadataFilter(topic="water_management")
    bundle = retrieve_agronomy_guidance(
        query="irrigation evapotranspiration",
        filters=filters,
        limit=3,
        threshold=0.35,
        persist_dir=CHROMA_DIR,
    )
    if bundle.chunks:
        for chunk in bundle.chunks:
            assert chunk.topic == "water_management"


def test_citation_validator_accepts_valid_citations():
    """Verify CitationValidator passes when citations match retrieved evidence."""
    bundle = retrieve_agronomy_guidance(
        query="water requirements for finger millet",
        limit=2,
        threshold=0.40,
        persist_dir=CHROMA_DIR,
    )
    assert len(bundle.chunks) > 0
    top_cite = bundle.chunks[0].citation_id

    advisory_text = (
        f"According to research guidance [{top_cite}], finger millet requires concentrated "
        "irrigation at flowering and grain filling to prevent yield penalties."
    )

    result = CitationValidator.validate_advisory(advisory_text, bundle)
    assert result.is_valid is True
    assert top_cite in result.resolved_ids
    assert len(result.unresolved_ids) == 0
    assert len(result.rejection_reasons) == 0


def test_citation_validator_rejects_hallucinated_citations():
    """Verify CitationValidator catches and rejects ungrounded citation IDs."""
    bundle = retrieve_agronomy_guidance(
        query="water requirements for finger millet",
        limit=2,
        threshold=0.40,
        persist_dir=CHROMA_DIR,
    )
    advisory_text = (
        "Based on [IMAGINARY-ICAR-DOC-2099:SEC01], apply heavy watering immediately."
    )

    result = CitationValidator.validate_advisory(advisory_text, bundle)
    assert result.is_valid is False
    assert "IMAGINARY-ICAR-DOC-2099:SEC01" in result.unresolved_ids
    assert any("Hallucinated" in r for r in result.rejection_reasons)


def test_citation_validator_blocks_chemical_dosages():
    """Verify zero-tolerance agronomic safety rule: chemical mixing concentrations are banned."""
    bundle = retrieve_agronomy_guidance(
        query="water requirements for finger millet",
        limit=2,
        threshold=0.40,
        persist_dir=CHROMA_DIR,
    )
    top_cite = bundle.chunks[0].citation_id

    # Advisory contains a valid citation but illegally prescribes a chemical concentration
    advisory_text = (
        f"Based on [{top_cite}], spray 2.5 ml/L of Mancozeb 75 WP on foliage."
    )

    result = CitationValidator.validate_advisory(advisory_text, bundle)
    assert result.is_valid is False
    assert any("Unauthorized chemical dosage" in r for r in result.rejection_reasons)


def test_provenance_invariant_modelled_inputs_not_physical():
    """Verify RAG evidence text strictly enforces distinction between reanalysis and physical sensors."""
    registry = load_source_register(REGISTER_CSV)
    uasb_meta = registry["UASB-POP-RAGI-2022"]
    uasb_file = CORPUS_DIR / "UASB-POP-RAGI-2022.md"

    chunks = parse_and_chunk_document(uasb_file, uasb_meta)
    for c in chunks:
        # None of the chunks should claim reanalysis model equals in-situ field sensor
        assert "modelled sensor" not in c.text.lower()

