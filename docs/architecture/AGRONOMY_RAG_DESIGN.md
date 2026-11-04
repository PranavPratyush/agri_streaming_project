# Agronomy RAG Retrieval Subsystem Architecture

- **Domain:** Stage 15 — Agronomy Knowledge Base & Vector Retrieval Service
- **Status:** IMPLEMENTED AND VERIFIED
- **Date:** 2026-11-04
- **Author:** AgriKafka Engineering Team
- **Package Path:** `packages/agronomy-rag/` (`src/agri_agronomy_rag`)
- **Corpus Location:** `knowledge/corpus/`
- **Source Register:** `knowledge/source-register.csv`
- **Vector Store Persistence:** `knowledge/chroma_db/`

---

## 1. Executive Summary & Architectural Scope

The **Agronomy RAG Subsystem** is an independent, offline-capable knowledge retrieval engine designed to ground automated agricultural advisories in peer-reviewed and government-accredited agronomic literature. 

Per the AgriKafka-Agent design principles:
1. **Decoupled Architecture:** Retrieval is strictly independent from agent orchestration (Stage 16). The retrieval service operates as an isolated library that can be tested, benchmarked, and evaluated standalone.
2. **Deterministic Safety Guardrails:** The subsystem enforces strict zero-hallucination citation validation and deterministic prohibition against unverified chemical dosage recommendations (`agronomic-safety.md`).
3. **Explicit No-Result Path:** If retrieval yields insufficient evidence or falls below confidence thresholds, the system emits an explicit `EVIDENCE_INSUFFICIENT` status, forcing downstream agents to flag uncertainty rather than hallucinating guidance.
4. **Offline Resilience:** Document parsing, chunking, and dense vector embeddings run completely offline via an ONNX-runtime accelerated MiniLM model, requiring zero cloud API calls or runtime network access.

---

## 2. Source Register & Corpus Governance

All documents in the knowledge base undergo strict audit prior to ingestion. Candidate sources are registered in `knowledge/source-register.csv`.

### 2.1 Approved Source Register

| Source ID | Title / Institution | Publication Year | Document Type | Focus / Applicability | Canonical Reference / URL |
|---|---|---|---|---|---|
| `FAO-56-CH06` | FAO Irrigation and Drainage Paper 56: Single Crop Coefficient ($K_c$) | 1998 | Extension Manual | Finger millet, water depletion fraction ($p$), yield response ($K_y$) | [fao.org/3/x0490e/x0490e0b.htm](https://www.fao.org/3/x0490e/x0490e0b.htm) |
| `UASB-POP-RAGI-2022` | Package of Practices for Finger Millet (Ragi), Zone 5 | 2022 | Extension Package | Variety GPU-28, red sandy loams, critical flowering stage, safety rules | University of Agricultural Sciences, Bangalore |
| `ICAR-AICRP-FM-2021` | All India Coordinated Research Project on Small Millets | 2021 | Research Advisory | Dryland drought dynamics, visual wilting symptoms, protective sprays | ICAR-IIMR / UAS Bangalore |
| `TNAU-AGRITECH-RAGI-2020` | TNAU Agritech Portal: Millets Water Management | 2020 | Advisory Portal | Finger millet water requirement (350–500 mm), irrigation intervals, drainage | Tamil Nadu Agricultural University Agritech |
| `ICAR-CRIDA-DRYLAND-2019` | Contingency Plan for Kolar District: Drought Mitigation | 2019 | Contingency Plan | Kolar rainfall (740 mm), inter-cultivation (*edekunte*), dry spells | ICAR-CRIDA, Hyderabad |

### 2.2 Ingestion & Corpus Versioning
- Every source document is maintained as clean Markdown in `knowledge/corpus/{source_id}.md`.
- Ingestion computes a deterministic SHA-256 hash across all document contents and timestamps.
- The active corpus version is: **`v1.0-1b95cf635c01`** (recorded in vector store collection metadata).

---

## 3. Chunking & Ingestion Pipeline

The ingestion pipeline (`agri_agronomy_rag.ingest`) converts structured markdown documents into semantically coherent, retrieval-ready chunks.

```mermaid
flowchart TD
    MD[Markdown Document in knowledge/corpus/] --> Frontmatter[Parse YAML Metadata & Section Headings]
    Frontmatter --> Splitter[Heading-Aware Semantic Splitter]
    Splitter --> ContextPrepender[Context Header Injection: Doc Title + Section Path]
    ContextPrepender --> IDGen[Deterministic Citation ID Generator]
    IDGen --> Embedder[ONNX MiniLM-L6-v2 Embedder (384-dim)]
    Embedder --> ChromaDB[(Chroma Vector Store: agri_agronomy_knowledge)]
```

### 3.1 Heading-Aware Chunking Strategy
- **Preserved Boundaries:** Document boundaries and top-level markdown headers (`#`, `##`, `###`) are strictly respected. Chunks are never split across unrelated sections.
- **Context Injection:** To prevent loss of semantic context during vector retrieval, each chunk prepends a structured contextual header:
  ```markdown
  [Document: Package of Practices for Finger Millet (Ragi), Zone 5]
  [Section: Soil Moisture & Soil Type Characteristics]
  [Topic: soil_water_dynamics | Crop: Finger Millet | Region: Karnataka Zone 5 (Kolar)]
  ... content body ...
  ```
- **Chunk Parameters:**
  - Maximum chunk size: 1,000 characters
  - Target chunk size: 600–800 characters
  - Overlap: 100 characters (preserving intra-paragraph continuity)
  - Total chunks generated across corpus: **21 chunks**

### 3.2 Deterministic Citation Identifier Scheme
Each chunk receives an immutable, globally unique Citation ID:
$$\text{Citation ID} = \{\text{Source ID}\} : \text{SEC}\{\text{Section Number}\} : \text{CH}\{\text{Chunk Index}\}$$
*Example:* `UASB-POP-RAGI-2022:SEC02:CH01` references Section 2 (Soil Moisture), Chunk 1 of the UAS Bangalore Package of Practices.

---

## 4. Vector Embedding & Storage Architecture

### 4.1 Embedding Model
- **Model:** `all-MiniLM-L6-v2` (Sentence-Transformers)
- **Runtime:** `onnxruntime` v1.31.1 (pure local CPU inference, zero PyTorch/CUDA bloat)
- **Embedding Dimensions:** 384
- **Local Disk Cache:** `~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/` (79.3 MB)
- **Inference Latency:** 8–18 ms per single query embedding on standard x86 CPU.

### 4.2 ChromaDB Configuration
- **Persist Directory:** `knowledge/chroma_db/`
- **Collection Name:** `agri_agronomy_knowledge`
- **Distance Metric:** Cosine Distance (`"hnsw:space": "cosine"`)
- **Metadata Indexing:** Each entry contains indexed filter attributes:
  - `source_id`: String (e.g. `FAO-56-CH06`)
  - `document_title`: String
  - `section_heading`: String
  - `topic`: String (e.g. `water_requirements`, `soil_water_dynamics`, `drought_contingency`)
  - `crop`: String (`Finger Millet`)
  - `region`: String (`Karnataka Zone 5 / Kolar`)
  - `soil`: String (`Red Sandy Loam / Alfisols`)
  - `growth_stage`: String (`General`, `Flowering`, `Vegetative`, etc.)
  - `citation_id`: String
  - `canonical_url`: String

---

## 5. Retrieval Gating & Safety Guardrails

### 5.1 Retrieval Flow & Confidence Gating
1. **Query Filtering:** Downstream agents provide query text and optional `AgronomyMetadataFilter` (filter by crop, topic, soil, or growth stage).
2. **HNSW Vector Search:** Chroma executes cosine similarity search returning top-$k$ nearest chunks.
3. **Similarity Score Calculation:**
   $$\text{Similarity} = 1.0 - \text{Cosine Distance}$$
4. **Relevance Gating:** Chunks with $\text{Similarity} < \text{threshold}$ (default: $0.50$) are rejected.
5. **No-Result Short-Circuit:**
   - If zero chunks satisfy the threshold or filter:
     - `evidence_status = "EVIDENCE_INSUFFICIENT"`
     - `no_result_reason = "No matching agronomic guidance found meeting minimum relevance threshold (0.50)"`
     - Downstream agents are strictly forbidden from hallucinating recommendations.

### 5.2 Deterministic Citation & Chemical Safety Validator
The `CitationValidator` (`agri_agronomy_rag.validator`) implements two mandatory checks:
1. **Citation Authenticity Check:** Inspects advisory text for bracketed citations (e.g. `[UASB-POP-RAGI-2022:SEC02:CH01]`). If any citation does not exist in the retrieved `EvidenceBundle`, the advisory is rejected (`valid=False`, reason: `HALLUCINATED_CITATION`).
2. **Chemical Dosage Guardrail (`agronomic-safety.md`):** Regex audits advisory text against unauthorized chemical concentration patterns:
   - Matches: `\b\d+(\.\d+)?\s*(ml|g|kg|ppm|%)\s*(per|\/)\s*(liter|litre|l|ha|acre)\b`
   - If unverified chemical prescriptions are detected, validation halts immediately:
     - `valid = False`
     - `safety_violation = "UNAUTHORIZED_CHEMICAL_DOSAGE"`
     - Message: "Automated systems are strictly prohibited from prescribing chemical pesticide or fertilizer dosages without accredited human agronomist approval."

