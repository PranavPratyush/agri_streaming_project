"""Deterministic citation grounding validator and chemical dosage filter."""

from __future__ import annotations

import re
from typing import List, Set

from agri_agronomy_rag.models import CitationValidationResult, EvidenceBundle

# Strict regex detecting citation tags like [UASB-POP-RAGI-2022:SEC02:CH01] or [FAO-56-CH06]
CITATION_TAG_PATTERN = re.compile(r"\[([A-Za-z0-9_\-]+(?::[A-Za-z0-9_\-]+)*)\]")

# Regex detecting unauthorized chemical dosage mixing concentrations
BANNED_CHEMICAL_DOSAGE_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:ml|mg|g|grams|litres?|l)\s*(?:/|per)\s*(?:acre|hectare|ha|litre|l|bucket|tank)\b",
    re.IGNORECASE,
)


class CitationValidator:
    """Validates that cited references in downstream agent text resolve strictly to retrieved evidence."""

    @staticmethod
    def extract_citations(text: str) -> List[str]:
        """Extracts all citation identifiers enclosed in square brackets."""
        return [match.strip() for match in CITATION_TAG_PATTERN.findall(text)]

    @classmethod
    def validate_advisory(
        cls,
        advisory_text: str,
        evidence_bundle: EvidenceBundle,
        strict_mode: bool = True,
    ) -> CitationValidationResult:
        """Audits generated advisory text against the evidence bundle."""
        rejection_reasons: List[str] = []

        # 1. Check for banned chemical dosages (Zero-tolerance agronomic safety rule)
        dosage_matches = BANNED_CHEMICAL_DOSAGE_PATTERN.findall(advisory_text)
        if dosage_matches:
            rejection_reasons.append(
                f"Unauthorized chemical dosage prescription detected: {dosage_matches}. "
                f"Agronomic safety rules strictly prohibit prescribing chemical mixing concentrations."
            )

        # 2. Extract citations
        extracted_citations = cls.extract_citations(advisory_text)

        # Build valid reference universe from the bundle
        valid_citation_ids: Set[str] = set()
        valid_source_ids: Set[str] = set()

        for chunk in evidence_bundle.chunks:
            valid_citation_ids.add(chunk.citation_id)
            valid_source_ids.add(chunk.source_id)

        resolved: List[str] = []
        unresolved: List[str] = []

        for cite in extracted_citations:
            # Check if exact citation_id matches, or if base source_id matches
            if cite in valid_citation_ids or cite in valid_source_ids:
                resolved.append(cite)
            else:
                unresolved.append(cite)

        if unresolved:
            rejection_reasons.append(
                f"Hallucinated or ungrounded citation IDs detected: {unresolved}. "
                f"Every cited source must strictly resolve to the evidence bundle."
            )

        if strict_mode and not extracted_citations and evidence_bundle.chunks:
            rejection_reasons.append(
                "Advisory contains zero citation grounding tags despite available evidence chunks."
            )

        is_valid = len(rejection_reasons) == 0

        return CitationValidationResult(
            is_valid=is_valid,
            cited_ids=extracted_citations,
            resolved_ids=resolved,
            unresolved_ids=unresolved,
            rejection_reasons=rejection_reasons,
        )
