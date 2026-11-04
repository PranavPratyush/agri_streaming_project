"""Command-line interface for the AgriKafka Agronomy RAG retrieval service."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure package is on sys.path when invoked directly
PKG_ROOT = Path(__file__).resolve().parent.parent
if str(PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(PKG_ROOT))

from agri_agronomy_rag.models import AgronomyMetadataFilter
from agri_agronomy_rag.retriever import retrieve_agronomy_guidance
from agri_agronomy_rag.store import AgronomyVectorStore
from agri_agronomy_rag.validator import CitationValidator

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CORPUS_DIR = REPO_ROOT / "knowledge" / "corpus"
DEFAULT_REGISTER_CSV = REPO_ROOT / "knowledge" / "source-register.csv"
DEFAULT_CHROMA_DIR = REPO_ROOT / "knowledge" / "chroma_db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("agri_agronomy_rag.cli")


def cmd_index(args: argparse.Namespace) -> int:
    corpus_dir = Path(args.corpus_dir)
    register_csv = Path(args.register_csv)
    chroma_dir = Path(args.chroma_dir)

    store = AgronomyVectorStore(persist_dir=chroma_dir)
    result = store.index_corpus(
        corpus_dir=corpus_dir,
        register_csv=register_csv,
        force_reindex=args.force,
    )
    print("\n--- Indexing Report ---")
    print(json.dumps(result, indent=2))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    filters = None
    if any([args.crop, args.topic, args.soil, args.stage]):
        filters = AgronomyMetadataFilter(
            crop=args.crop,
            topic=args.topic,
            soil=args.soil,
            growth_stage=args.stage,
        )

    bundle = retrieve_agronomy_guidance(
        query=args.query,
        filters=filters,
        limit=args.limit,
        threshold=args.threshold,
        persist_dir=Path(args.chroma_dir),
    )

    print("\n--- Retrieval Results ---")
    print(f"Status: {bundle.evidence_status}")
    print(f"Corpus Version: {bundle.corpus_version}")
    print(f"Embedding Model: {bundle.embedding_model} ({bundle.embedding_dimensions}d)")
    print(f"Total Chunks: {bundle.total_chunks_retrieved}")

    if bundle.no_result_reason:
        print(f"No-Result Reason: {bundle.no_result_reason}")

    for idx, chunk in enumerate(bundle.chunks, 1):
        print(f"\n[{idx}] Citation ID: {chunk.citation_id} (Relevance: {chunk.relevance_score:.4f})")
        print(f"    Title: {chunk.document_title}")
        print(f"    Section: {chunk.section_heading} | Topic: {chunk.topic}")
        print(f"    Applicability: Crop={chunk.crop} | Region={chunk.region} | Soil={chunk.soil}")
        print(f"    URL: {chunk.canonical_url}")
        print(f"    Excerpt: {chunk.text[:220]}...")

    return 0


def cmd_info(args: argparse.Namespace) -> int:
    chroma_dir = Path(args.chroma_dir)
    store = AgronomyVectorStore(persist_dir=chroma_dir)
    print("\n--- Knowledge Base Info ---")
    print(f"Chroma Directory: {chroma_dir}")
    print(f"Total Chunks: {store.count()}")
    print(f"Corpus Version: {store.get_corpus_version()}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="AgriKafka Agronomy RAG CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: index
    p_index = subparsers.add_parser("index", help="Index markdown corpus into Chroma")
    p_index.add_argument("--corpus-dir", default=str(DEFAULT_CORPUS_DIR), help="Directory of markdown docs")
    p_index.add_argument("--register-csv", default=str(DEFAULT_REGISTER_CSV), help="Source register CSV")
    p_index.add_argument("--chroma-dir", default=str(DEFAULT_CHROMA_DIR), help="Chroma persistence directory")
    p_index.add_argument("--force", action="store_true", help="Force re-indexing")
    p_index.set_defaults(func=cmd_index)

    # Subcommand: query
    p_query = subparsers.add_parser("query", help="Query the agronomy knowledge base")
    p_query.add_argument("query", help="Natural language query string")
    p_query.add_argument("--crop", default=None, help="Filter by crop")
    p_query.add_argument("--topic", default=None, help="Filter by topic")
    p_query.add_argument("--soil", default=None, help="Filter by soil")
    p_query.add_argument("--stage", default=None, help="Filter by growth stage")
    p_query.add_argument("--limit", type=int, default=3, help="Max results to return")
    p_query.add_argument("--threshold", type=float, default=0.55, help="Relevance score threshold")
    p_query.add_argument("--chroma-dir", default=str(DEFAULT_CHROMA_DIR), help="Chroma persistence directory")
    p_query.set_defaults(func=cmd_query)

    # Subcommand: info
    p_info = subparsers.add_parser("info", help="Inspect Chroma store info")
    p_info.add_argument("--chroma-dir", default=str(DEFAULT_CHROMA_DIR), help="Chroma persistence directory")
    p_info.set_defaults(func=cmd_info)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
