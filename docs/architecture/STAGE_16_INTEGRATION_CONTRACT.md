# Stage 16 Integration Contract: Agronomy Knowledge Agent Boundary

- **Domain:** Interface Specification between Stage 15 (Agronomy RAG Retrieval) and Stage 16 (Agronomy Knowledge Agent)
- **Status:** APPROVED & FROZEN
- **Date:** 2026-11-04
- **Provider Package:** `packages/agronomy-rag/src/agri_agronomy_rag`
- **Consumer Component:** `services/alert-investigator` / Stage 16 Agronomy Knowledge Agent

---

## 1. Architectural Boundary Principles

1. **Read-Only Invariant:** Stage 16 agents interact with the RAG knowledge base exclusively through a read-only Python function call. Agents are strictly prohibited from writing, mutating, or deleting Chroma collections or corpus files.
2. **Decoupled Orchestration:** Retrieval logic does not invoke LLMs, prompt templates, or agent state machines. It takes a query and optional filter, and returns an immutable `EvidenceBundle`.
3. **Structured Citation Contract:** All retrieved advice chunks carry an immutable `citation_id`. Downstream agents **MUST** cite these exact IDs in any synthesized advisory.
4. **Mandatory Citation & Safety Validation:** Prior to persisting or notifying an advisory, Stage 16 **MUST** invoke `CitationValidator.validate_advisory()`. Any advisory containing hallucinated citations or chemical dosage prescriptions is automatically rejected.

---

## 2. Python API Specification

### 2.1 Core Retrieval Function

```python
def retrieve_agronomy_guidance(
    query: str,
    filters: Optional[AgronomyMetadataFilter] = None,
    limit: int = 3,
    threshold: float = 0.50,
    persist_dir: Optional[Path] = None,
) -> EvidenceBundle:
    """Retrieve grounded agronomic evidence chunks matching a query.
    
    Args:
        query: Natural language domain query.
        filters: Optional structured metadata filter (crop, topic, soil, stage).
        limit: Maximum number of top chunks to return (default: 3).
        threshold: Minimum cosine similarity score [0.0 - 1.0] required (default: 0.50).
        persist_dir: Optional custom path to chroma_db directory.
        
    Returns:
        EvidenceBundle dataclass containing status, version, chunks, or no_result_reason.
    """
```

### 2.2 Input Filter Model (`AgronomyMetadataFilter`)

```python
@dataclass
class AgronomyMetadataFilter:
    crop: Optional[str] = None          # e.g. "Finger Millet"
    topic: Optional[str] = None         # e.g. "water_requirements", "drought_contingency"
    region: Optional[str] = None        # e.g. "Karnataka Zone 5 / Kolar"
    soil: Optional[str] = None          # e.g. "Red Sandy Loam / Alfisols"
    growth_stage: Optional[str] = None  # e.g. "Flowering", "Vegetative"
```

### 2.3 Output Evidence Bundle Model (`EvidenceBundle`)

```python
@dataclass
class EvidenceChunk:
    chunk_id: str                      # UUID or internal ID
    citation_id: str                   # Deterministic ID: {source_id}:SEC{sec}:CH{idx}
    source_id: str                     # e.g. "UASB-POP-RAGI-2022"
    document_title: str
    section_heading: str
    topic: str
    crop: str
    region: str
    soil: str
    growth_stage: str
    canonical_url: str
    relevance_score: float             # Cosine similarity in range [0.0, 1.0]
    text: str                          # Chunk excerpt body

@dataclass
class EvidenceBundle:
    query: str
    evidence_status: str               # "EVIDENCE_FOUND" or "EVIDENCE_INSUFFICIENT"
    corpus_version: str                # e.g. "v1.0-1b95cf635c01"
    embedding_model: str               # "all-MiniLM-L6-v2"
    embedding_dimensions: int          # 384
    total_chunks_retrieved: int
    chunks: List[EvidenceChunk]
    no_result_reason: Optional[str] = None
```

---

## 3. Downstream Agent Handling Rules

### 3.1 Handling `EVIDENCE_FOUND`
When `bundle.evidence_status == "EVIDENCE_FOUND"`:
- The agent may synthesize an advisory using **only** information grounded in `bundle.chunks`.
- Every recommended action must explicitly reference one or more citation IDs in brackets, e.g.:
  > *"During the critical flowering stage of finger millet, soil moisture must be maintained above 50% Available Water Capacity to prevent yield loss [UASB-POP-RAGI-2022:SEC03:CH01]. Farmers in Kolar should practice shallow inter-cultivation (edekunte) to break soil capillaries [ICAR-CRIDA-DRYLAND-2019:SEC02:CH01]."*

### 3.2 Handling `EVIDENCE_INSUFFICIENT`
When `bundle.evidence_status == "EVIDENCE_INSUFFICIENT"`:
- The agent **MUST NOT** generate ungrounded agronomic recommendations.
- The agent **MUST** return a fallback advisory acknowledging evidence insufficiency:
  > *"Agronomic guidance could not be verified in the accredited knowledge base for the specified conditions (Reason: {bundle.no_result_reason}). Please consult a local agricultural extension officer or KVK scientist before applying treatments."*

---

## 4. Citation and Safety Validation Contract

Stage 16 agents must execute post-generation validation before emitting any advisory:

```python
from agri_agronomy_rag.validator import CitationValidator

validator = CitationValidator()
result = validator.validate_advisory(
    advisory_text=draft_advisory_text,
    bundle=retrieved_bundle,
)

if not result.valid:
    # Action rejected! Handle validation failure
    logger.error("Advisory validation failed: %s (%s)", result.failure_reason, result.violations)
```

### Validation Failure Conditions:
1. **`HALLUCINATED_CITATION`:** Advisory contains `[CITATION-ID]` that does not exist in `bundle.chunks`.
2. **`UNAUTHORIZED_CHEMICAL_DOSAGE`:** Advisory contains unverified chemical concentration metrics (e.g. `2.5 ml/L`, `500 g/ha`), violating `agronomic-safety.md`.

