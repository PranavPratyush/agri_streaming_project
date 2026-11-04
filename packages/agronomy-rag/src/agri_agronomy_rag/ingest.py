"""Document parser, semantic heading-aware chunker, and citation ID generator."""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Tuple

from agri_agronomy_rag.models import EvidenceChunk, SourceMetadata


def load_source_register(csv_path: Path) -> Dict[str, SourceMetadata]:
    """Loads and validates the official source register CSV."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Source register CSV not found at: {csv_path}")

    registry: Dict[str, SourceMetadata] = {}
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            s_id = row["source_id"].strip()
            registry[s_id] = SourceMetadata(
                source_id=s_id,
                title=row["title"].strip(),
                author_institution=row["author_institution"].strip(),
                publication_date=row["publication_date"].strip(),
                canonical_url=row["canonical_url"].strip(),
                access_date=row["access_date"].strip(),
                document_type=row["document_type"].strip(),
                language=row.get("language", "en").strip(),
                crop_applicability=row.get("crop_applicability", "unknown").strip(),
                region_applicability=row.get("region_applicability", "unknown").strip(),
                soil_applicability=row.get("soil_applicability", "unknown").strip(),
                growth_stage_applicability=row.get("growth_stage_applicability", "unknown").strip(),
                license_rights=row["license_rights"].strip(),
                retrieval_status=row.get("retrieval_status", "PARSED_AND_INDEXED").strip(),
                known_limitations=row.get("known_limitations", "").strip(),
            )
    return registry


def compute_corpus_version(corpus_dir: Path, register_path: Path) -> str:
    """Computes a deterministic SHA-256 hash representing the exact corpus version."""
    hasher = hashlib.sha256()

    # Hash source register
    if register_path.exists():
        hasher.update(register_path.read_bytes())

    # Hash all markdown files sorted by name
    for file_path in sorted(corpus_dir.glob("*.md")):
        hasher.update(file_path.name.encode("utf-8"))
        hasher.update(file_path.read_bytes())

    return f"v1.0-{hasher.hexdigest()[:12]}"


def _slugify(text: str) -> str:
    """Converts a heading string to a clean alphanumeric slug."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").upper()
    return slug[:24] if slug else "GEN"


def _extract_topic_from_text(heading: str, text: str) -> str:
    """Infers the agronomic topic tag strictly from keywords in heading and text."""
    combined = (heading + " " + text).lower()
    if any(k in combined for k in ["water", "evapotranspiration", "irrigation", "kc", "et0", "etc", "raw", "taw"]):
        return "water_management"
    if any(k in combined for k in ["drought", "dry spell", "wilting", "water stress", "contingency"]):
        return "drought_management"
    if any(k in combined for k in ["soil", "red sandy loam", "alfisol", "moisture capacity", "field capacity"]):
        return "soil_management"
    if any(k in combined for k in ["tillage", "mulch", "inter-cultivation", "edekunte", "hoe"]):
        return "cultural_practices"
    if any(k in combined for k in ["variety", "gpu-28", "phenology", "tillering", "flowering", "grain fill"]):
        return "crop_phenology"
    return "general_agronomy"


def parse_and_chunk_document(
    doc_path: Path, source_meta: SourceMetadata, max_words_per_chunk: int = 350
) -> List[EvidenceChunk]:
    """Parses a markdown document, preserving section headers, boundaries, and metadata."""
    content = doc_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    doc_title = source_meta.title
    current_section = "General Overview"
    current_section_idx = 0
    section_paragraphs: List[Tuple[str, int, str]] = []  # (section_heading, sec_num, paragraph_text)

    # Accumulate paragraphs under their respective section heading
    active_paragraph: List[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# ") and not current_section_idx:
            # Document title
            doc_title = stripped[2:].strip()
            continue

        if stripped.startswith("## "):
            # Flush existing paragraph
            if active_paragraph:
                p_text = "\n".join(active_paragraph).strip()
                if p_text:
                    section_paragraphs.append((current_section, current_section_idx, p_text))
                active_paragraph = []

            current_section = stripped[3:].strip()
            current_section_idx += 1
            continue

        if not stripped:
            if active_paragraph:
                p_text = "\n".join(active_paragraph).strip()
                if p_text:
                    section_paragraphs.append((current_section, current_section_idx, p_text))
                active_paragraph = []
        else:
            active_paragraph.append(stripped)

    # Flush any remaining text
    if active_paragraph:
        p_text = "\n".join(active_paragraph).strip()
        if p_text:
            section_paragraphs.append((current_section, current_section_idx, p_text))

    chunks: List[EvidenceChunk] = []
    chunk_counter_by_sec: Dict[int, int] = {}

    # Group into chunks up to max_words_per_chunk
    curr_heading = ""
    curr_sec_idx = 0
    curr_buf: List[str] = []
    curr_word_count = 0

    def emit_chunk(heading: str, sec_idx: int, text: str) -> None:
        if not text.strip():
            return
        sec_num = max(1, sec_idx)
        count = chunk_counter_by_sec.get(sec_num, 0) + 1
        chunk_counter_by_sec[sec_num] = count

        sec_slug = f"SEC{sec_num:02d}"
        citation_id = f"{source_meta.source_id}:{sec_slug}:CH{count:02d}"
        topic = _extract_topic_from_text(heading, text)

        # Contextual header prepended for grounding and citation clarity
        full_text = (
            f"[SOURCE: {source_meta.source_id} | Title: {source_meta.title} | "
            f"Section: {heading}]\n\n{text}"
        )

        chunk = EvidenceChunk(
            citation_id=citation_id,
            source_id=source_meta.source_id,
            document_title=doc_title,
            author_institution=source_meta.author_institution,
            section_heading=heading,
            page_or_section=f"Section {sec_num}: {heading}",
            canonical_url=source_meta.canonical_url,
            text=full_text,
            crop=source_meta.crop_applicability,
            region=source_meta.region_applicability,
            soil=source_meta.soil_applicability,
            growth_stage=source_meta.growth_stage_applicability,
            document_type=source_meta.document_type,
            topic=topic,
            relevance_score=0.0,
            retrieval_method="dense_cosine_similarity",
        )
        chunks.append(chunk)

    for heading, sec_idx, paragraph in section_paragraphs:
        words = paragraph.split()
        if curr_heading and heading != curr_heading:
            # Section change -> flush previous section
            emit_chunk(curr_heading, curr_sec_idx, "\n\n".join(curr_buf))
            curr_buf = [paragraph]
            curr_heading = heading
            curr_sec_idx = sec_idx
            curr_word_count = len(words)
        else:
            curr_heading = heading
            curr_sec_idx = sec_idx
            if curr_word_count + len(words) > max_words_per_chunk and curr_buf:
                emit_chunk(curr_heading, curr_sec_idx, "\n\n".join(curr_buf))
                curr_buf = [paragraph]
                curr_word_count = len(words)
            else:
                curr_buf.append(paragraph)
                curr_word_count += len(words)

    if curr_buf and curr_heading:
        emit_chunk(curr_heading, curr_sec_idx, "\n\n".join(curr_buf))

    return chunks

