"""Chroma persistent vector store manager and corpus collection indexer."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from agri_agronomy_rag.ingest import compute_corpus_version, load_source_register, parse_and_chunk_document
from agri_agronomy_rag.models import EvidenceChunk

logger = logging.getLogger("agri_agronomy_rag.store")

COLLECTION_NAME = "agri_agronomy_knowledge"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2 (ONNX)"
EMBEDDING_DIMENSIONS = 384


class AgronomyVectorStore:
    """Encapsulates Chroma persistence, embedding generation, and metadata indexing."""

    def __init__(self, persist_dir: Path | str) -> None:
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        self._embedding_fn = DefaultEmbeddingFunction()
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._embedding_fn,
            metadata={
                "description": "AgriKafka-Agent verified agronomic reference collection",
                "embedding_model": EMBEDDING_MODEL_NAME,
                "embedding_dimensions": EMBEDDING_DIMENSIONS,
                "hnsw:space": "cosine",
            },
        )

    @property
    def collection(self) -> Any:
        return self._collection

    def count(self) -> int:
        return self._collection.count()

    def get_corpus_version(self) -> str:
        meta = self._collection.metadata or {}
        return meta.get("corpus_version", "v1.0-unindexed")

    def index_corpus(
        self,
        corpus_dir: Path,
        register_csv: Path,
        force_reindex: bool = False,
    ) -> Dict[str, Any]:
        """Indexes all verified markdown documents in corpus_dir registered in register_csv."""
        registry = load_source_register(register_csv)
        corpus_version = compute_corpus_version(corpus_dir, register_csv)

        current_version = self.get_corpus_version()
        if not force_reindex and current_version == corpus_version and self.count() > 0:
            logger.info("Corpus version matches current indexed version (%s). Skipping reindex.", corpus_version)
            return {
                "status": "UP_TO_DATE",
                "corpus_version": corpus_version,
                "total_chunks": self.count(),
                "indexed_documents": len(registry),
            }

        logger.info("Indexing corpus into Chroma collection '%s' (version: %s)...", COLLECTION_NAME, corpus_version)

        # Recreate collection cleanly if force_reindex is requested
        if force_reindex:
            try:
                self._client.delete_collection(COLLECTION_NAME)
            except Exception:
                pass
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=self._embedding_fn,
                metadata={
                    "description": "AgriKafka-Agent verified agronomic reference collection",
                    "embedding_model": EMBEDDING_MODEL_NAME,
                    "embedding_dimensions": EMBEDDING_DIMENSIONS,
                    "hnsw:space": "cosine",
                },
            )
        elif self.count() > 0:
            existing_ids = self._collection.get().get("ids", [])
            if existing_ids:
                self._collection.delete(ids=existing_ids)

        all_chunks: List[EvidenceChunk] = []

        for doc_file in sorted(corpus_dir.glob("*.md")):
            source_id = doc_file.stem
            if source_id not in registry:
                logger.warning("File %s has no matching source ID in source register. Skipping.", doc_file.name)
                continue

            source_meta = registry[source_id]
            doc_chunks = parse_and_chunk_document(doc_file, source_meta)
            all_chunks.extend(doc_chunks)

        if not all_chunks:
            logger.warning("No valid chunks were parsed from corpus directory: %s", corpus_dir)
            return {
                "status": "EMPTY",
                "corpus_version": corpus_version,
                "total_chunks": 0,
                "indexed_documents": 0,
            }

        # Prepare batch payloads for Chroma
        ids = [c.citation_id for c in all_chunks]
        documents = [c.text for c in all_chunks]
        metadatas = [
            {
                "citation_id": c.citation_id,
                "source_id": c.source_id,
                "document_title": c.document_title,
                "author_institution": c.author_institution,
                "section_heading": c.section_heading,
                "page_or_section": c.page_or_section,
                "canonical_url": c.canonical_url,
                "crop": c.crop,
                "region": c.region,
                "soil": c.soil,
                "growth_stage": c.growth_stage,
                "document_type": c.document_type,
                "topic": c.topic,
                "corpus_version": corpus_version,
            }
            for c in all_chunks
        ]

        # Add to Chroma in batches
        batch_size = 50
        for i in range(0, len(ids), batch_size):
            self._collection.add(
                ids=ids[i : i + batch_size],
                documents=documents[i : i + batch_size],
                metadatas=metadatas[i : i + batch_size],
            )

        # Update collection metadata with corpus version
        self._collection.modify(
            metadata={
                "description": "AgriKafka-Agent verified agronomic reference collection",
                "embedding_model": EMBEDDING_MODEL_NAME,
                "embedding_dimensions": EMBEDDING_DIMENSIONS,
                "corpus_version": corpus_version,
            }
        )

        logger.info(
            "Successfully indexed %d chunks across %d documents. Corpus version: %s",
            len(all_chunks),
            len(registry),
            corpus_version,
        )

        return {
            "status": "INDEXED",
            "corpus_version": corpus_version,
            "total_chunks": len(all_chunks),
            "indexed_documents": len(registry),
        }
