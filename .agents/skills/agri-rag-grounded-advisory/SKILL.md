---
name: "agri-rag-grounded-advisory"
description: "Procedures for building and querying the agronomic knowledge retrieval system (ICAR, FAO-56, UAS packages), validating citation grounding, preventing hallucinations, and enforcing advisory abstention."
---

# AgriKafka Skill: Agri-RAG Grounded Advisory

## Purpose
This skill governs the ingestion, chunking, embedding, retrieval, citation verification, and guardrail validation of agronomic reference literature used to back up AI farmer advisories.

---

## When to Use
- Ingesting and indexing verified agricultural guidance (ICAR, FAO, UAS Bangalore packages of practices) into the Chroma vector store (`knowledge/`).
- Constructing RAG prompts that require strict citation IDs.
- Validating citation integrity in the deterministic guardrail service.
- Implementing abstention logic when retrieved evidence is insufficient or conflicting.

## When NOT to Use
- Running low-level vector similarity search benchmarking without agronomic context.
- Conducting sensor health hardware checks.
- Bypassing guardrails to generate ungrounded conversational advice.

---

## Step-by-Step Procedure

### 1. Document Ingestion & Provenance Registration
- Every document placed in `knowledge/` must have an entry in `knowledge/manifest.json`:
  ```json
  {
    "document_id": "FAO-56-CH06",
    "title": "Crop Evapotranspiration - Guidelines for Computing Crop Water Requirements",
    "author": "Allen, Pereira, Raes, Smith",
    "year": 1998,
    "source_url": "https://www.fao.org/3/x0490e/x0490e00.htm",
    "license": "Public Access / UN FAO"
  }
  ```
- Exclude all copyrighted or unverified materials.

### 2. Chunking & Dense Embeddings
- Apply chunking with semantic boundaries: chunk size 500 tokens, 100-token overlap.
- Prepend each chunk with source metadata: `[SOURCE: FAO-56-CH06 | Crop: Ragi | Section: Critical Growth Stages]`.
- Generate embeddings using local Sentence Transformers (`all-MiniLM-L6-v2`) and index into Chroma collection `agri_advisories`.

### 3. Contextual Retrieval
- Retrieve top $k=3$ passages using cosine similarity with a relevance threshold (minimum cosine similarity $\ge 0.68$).
- If no retrieved chunk exceeds the relevance threshold, return empty context and signal `EVIDENCE_INSUFFICIENT`.

### 4. Citation-Grounded Drafting
- The advisory prompt instructs the LLM:
  > *"Every factual statement and recommended action MUST include a citation tag `[DOC_ID]`. Do not prescribe exact chemical dosages. If evidence is missing, output `STATUS: ABSTAIN`."*

### 5. Deterministic Guardrail Validation (Non-LLM)
- Inspect the generated advisory JSON:
  1. Extract all citation tags (`[DOC_ID]`).
  2. Verify that every cited `DOC_ID` was present in the retrieved passages. If hallucinated citations exist, reject the draft.
  3. Scan for banned chemical dosage patterns (`\d+\s*(ml|mg|g|grams|litres)\s*(per|/)\s*(acre|hectare|litre|bucket)`). If found, reject immediately.
  4. If validation fails, fallback to a pre-approved rule-based template.
