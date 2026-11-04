# AgriKafka-Agent: Agronomy RAG & Knowledge Retrieval Package
**Package:** `agri-agronomy-rag`  
**Purpose:** Agronomic reference document ingestion, semantic chunking, Chroma vector persistence, metadata-filtered retrieval, and citation validation for Finger Millet (Ragi GPU-28) in Kolar, Karnataka.

---

## Key Invariants
1. **Grounded Retrieval:** Returns typed `EvidenceBundle` instances with stable citation IDs and exact page/section provenance.
2. **Strict Metadata Provenance:** Does NOT invent crop, soil, or growth stage applicability. Unspecified metadata is explicitly tagged `unknown`.
3. **Citation Validation:** Validates that citations cited in AI advisories exist in the retrieved evidence corpus.
4. **Independent Retrieval:** Decoupled from agent state machines, enabling standalone testing and evaluation.

