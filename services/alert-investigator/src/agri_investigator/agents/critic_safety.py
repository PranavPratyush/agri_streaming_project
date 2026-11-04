"""Critic / Safety Agent implementation.

Independently evaluates proposed advisories for cross-agent consistency, empirical citation backing,
unauthorized chemical recommendations, unwarranted certainty, and physical actuation risks.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from agri_investigator.agents.agronomy_knowledge import AgronomyKnowledgeOutput
from agri_investigator.agents.base import BaseSpecialistAgent
from agri_investigator.models import (
    AdvisoryProposalOutput,
    AgentRole,
    CropRiskAnalystOutput,
    CriticReviewOutput,
    CriticVerdict,
    FieldContextOutput,
    SensorReliabilityOutput,
)


class CriticSafetyInput(BaseModel):
    """Input payload for Critic / Safety Agent."""
    proposed_advisory: AdvisoryProposalOutput
    reliability_assessment: SensorReliabilityOutput
    field_context: FieldContextOutput
    risk_assessment: CropRiskAnalystOutput
    evidence_output: AgronomyKnowledgeOutput


class CriticSafetyAgent(BaseSpecialistAgent):
    """Specialist agent critically auditing proposed advisories before human presentation."""

    def __init__(self, mock_mode: bool = False) -> None:
        super().__init__(
            role=AgentRole.CRITIC_SAFETY,
            name="Critic and Safety Auditor Specialist",
            version="1.0.0",
            model_name="gemini-2.0-flash",
            mock_mode=mock_mode,
        )

    def get_input_schema(self) -> type[BaseModel]:
        return CriticSafetyInput

    def get_output_schema(self) -> type[BaseModel]:
        return CriticReviewOutput

    def _execute_core(self, validated_input: BaseModel) -> Tuple[BaseModel, int]:
        inp: CriticSafetyInput = validated_input  # type: ignore

        if self.mock_mode and "default" in self._mock_responses:
            return CriticReviewOutput.model_validate(self._mock_responses["default"]), 70

        adv = inp.proposed_advisory
        rel = inp.reliability_assessment
        ctx = inp.field_context
        risk = inp.risk_assessment
        ev = inp.evidence_output

        findings: List[str] = []
        failed_checks: List[str] = []
        target_agent: Optional[str] = None
        revision_instructions: Optional[str] = None
        consistency_score = 0.95

        # Check 1: Telemetry and Reliability Consistency
        if not rel.is_trustworthy and adv.action_category == "IRRIGATION":
            failed_checks.append("TELEMETRY_UNTRUSTWORTHY_CONFLICT")
            findings.append("Advisory proposes physical irrigation despite Sensor Reliability reporting faulty/suspect probes.")
            target_agent = AgentRole.AGRICULTURAL_ADVISORY.value
            revision_instructions = "Re-draft advisory to focus strictly on sensor maintenance and physical soil inspection."
            consistency_score = 0.20

        # Check 2: Citation Grounding against Knowledge Agent
        valid_citations = {c["citation_id"] for c in ev.chunks if "citation_id" in c}
        for cited_id in adv.cited_evidence_ids:
            if cited_id not in valid_citations:
                failed_checks.append("HALLUCINATED_CITATION_REFERENCE")
                findings.append(f"Advisory references citation ID '{cited_id}' which was not returned by Knowledge Agent.")
                target_agent = AgentRole.AGRICULTURAL_ADVISORY.value
                revision_instructions = f"Remove or replace citation '{cited_id}' with genuine evidence from the retrieved bundle."
                consistency_score = 0.30

        # Check 3: Chemical Dosage Pattern Detection
        chem_pattern = re.compile(r"\b\d+(\.\d+)?\s*(ml|g|kg|ppm|%)\s*(per|\/)\s*(liter|litre|l|ha|acre)\b", re.IGNORECASE)
        combined_text = f"{adv.action_title} {adv.action_body} {adv.next_step}"
        if chem_pattern.search(combined_text):
            failed_checks.append("UNAUTHORIZED_CHEMICAL_DOSAGE")
            findings.append("Advisory prescribes chemical pesticide/fertilizer dosages, violating agronomic-safety.md.")
            target_agent = AgentRole.AGRICULTURAL_ADVISORY.value
            revision_instructions = "Remove all chemical dosages and concentrations immediately. Advise consultation with local KVK agronomist."
            consistency_score = 0.10

        # Check 4: Missing Evidence Abstention Check
        if ev.evidence_status == "EVIDENCE_INSUFFICIENT" and adv.confidence_score > 0.60:
            failed_checks.append("OVERCONFIDENT_WITHOUT_EVIDENCE")
            findings.append("Advisory claims high confidence despite knowledge base signaling EVIDENCE_INSUFFICIENT.")
            target_agent = AgentRole.AGRICULTURAL_ADVISORY.value
            revision_instructions = "Acknowledge evidence gap and reduce confidence score."
            consistency_score = 0.40

        # Determine Verdict
        if failed_checks:
            verdict = CriticVerdict.REVISION_REQUIRED
            findings.append(f"Critic audit rejected proposal: {len(failed_checks)} violation(s) detected.")
        else:
            verdict = CriticVerdict.APPROVED_FOR_HUMAN_REVIEW
            findings.append("Advisory is consistent with sensor reliability, parcel metadata, and verified agronomic evidence.")

        output = CriticReviewOutput(
            verdict=verdict,
            findings=findings,
            failed_checks=failed_checks,
            target_agent_for_revision=target_agent,
            revision_instructions=revision_instructions,
            evidence_consistency_score=consistency_score,
        )
        return output, 75

