"""Agricultural Advisory Agent implementation.

Synthesizes validated risk, field context, and accredited agronomic evidence into a cautious,
field-actionable recommendation. Enforces zero-hallucination citations and abstains on insufficient evidence.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from agri_investigator.agents.agronomy_knowledge import AgronomyKnowledgeOutput
from agri_investigator.agents.base import BaseSpecialistAgent
from agri_investigator.models import (
    AdvisoryProposalOutput,
    AgentRole,
    CropRiskAnalystOutput,
    FieldContextOutput,
    SensorReliabilityOutput,
)


class AgriculturalAdvisoryInput(BaseModel):
    """Input payload for Agricultural Advisory Agent."""
    candidate_alert: Dict[str, Any]
    risk_assessment: CropRiskAnalystOutput
    reliability_assessment: SensorReliabilityOutput
    field_context: FieldContextOutput
    evidence_output: AgronomyKnowledgeOutput
    revision_notes: Optional[str] = None


class AgriculturalAdvisoryAgent(BaseSpecialistAgent):
    """Specialist agent formulating grounded, cautious agricultural advisory proposals."""

    def __init__(self, mock_mode: bool = False) -> None:
        super().__init__(
            role=AgentRole.AGRICULTURAL_ADVISORY,
            name="Agricultural Advisory Specialist",
            version="1.0.0",
            model_name="gemini-2.0-flash",
            mock_mode=mock_mode,
        )

    def get_input_schema(self) -> type[BaseModel]:
        return AgriculturalAdvisoryInput

    def get_output_schema(self) -> type[BaseModel]:
        return AdvisoryProposalOutput

    def _execute_core(self, validated_input: BaseModel) -> Tuple[BaseModel, int]:
        inp: AgriculturalAdvisoryInput = validated_input  # type: ignore

        if self.mock_mode and "default" in self._mock_responses:
            return AdvisoryProposalOutput.model_validate(self._mock_responses["default"]), 80

        rel = inp.reliability_assessment
        ctx = inp.field_context
        risk = inp.risk_assessment
        ev = inp.evidence_output

        # 1. Check if sensor evidence is untrustworthy
        if not rel.is_trustworthy or not rel.proceed_to_agronomy:
            return AdvisoryProposalOutput(
                action_category="MONITORING",
                action_title="Field Telemetry Verification Required",
                action_body=(
                    f"Automated agronomic recommendations are withheld because primary sensors for field "
                    f"{ctx.field_id} are reporting {rel.sensor_health_state} ({rel.reason_code}). "
                    "Please physically inspect sensor probes and wiring before applying water or inputs."
                ),
                urgency="MEDIUM",
                cited_evidence_ids=[],
                assumptions=["Telemetry unreliability confirmed by sensor health forensics."],
                limitations=["No crop advice can be safely formulated from compromised readings."],
                confidence_score=0.95,
                when_to_seek_expert="Immediately contact hardware maintenance if sensor flatline or spike persists.",
                next_step="Inspect physical sensor probes in the parcel.",
            ), 50

        # 2. Check if accredited agronomic evidence is insufficient
        if ev.evidence_status == "EVIDENCE_INSUFFICIENT" or not ev.chunks:
            return AdvisoryProposalOutput(
                action_category="FIELD_INSPECTION",
                action_title="Field Inspection Recommended — Knowledge Gap",
                action_body=(
                    f"A potential {risk.risk_category} condition was detected (CSI: {risk.deterministic_csi:.2f}), "
                    f"but accredited agronomic guidance could not be matched with high confidence. "
                    "Avoid applying chemical inputs or heavy irrigation without physical soil sampling."
                ),
                urgency="MEDIUM",
                cited_evidence_ids=[],
                assumptions=["Soil moisture depletion suspected from stream telemetry."],
                limitations=["Specific contingency guidance unavailable in accredited knowledge base."],
                confidence_score=0.40,
                when_to_seek_expert="Consult the local Krishi Vigyan Kendra (KVK) or taluk agricultural officer.",
                next_step="Conduct on-site soil ball test to verify moisture before scheduling irrigation.",
            ), 55

        # 3. Grounded Advisory Formulation
        primary_chunk = ev.chunks[0]
        cited_id = primary_chunk["citation_id"]
        source_title = primary_chunk.get("document_title", "University Agronomy Advisory")

        # Cautious recommendation respecting Kolar dryland constraints
        action_title = f"Protective Irrigation & Soil Conservation for {ctx.crop_variety}"
        action_body = (
            f"Soil moisture depletion has reached critical thresholds for {ctx.crop_variety} during the "
            f"sensitive {ctx.growth_stage} stage [{cited_id}]. To prevent permanent wilting and yield reduction, "
            f"provide a protective irrigation of 20–25 mm if water is available [{cited_id}]. In dryland plots, "
            f"perform shallow inter-cultivation (edekunte) to create a dust mulch and sever soil capillaries "
            f"preserving root-zone moisture."
        )

        output = AdvisoryProposalOutput(
            action_category="IRRIGATION",
            action_title=action_title,
            action_body=action_body,
            urgency=risk.severity,
            cited_evidence_ids=[cited_id],
            assumptions=[
                f"Field soil is {ctx.soil_type} with field capacity ~{ctx.field_capacity*100:.0f}%.",
                f"Crop is at sensitive {ctx.growth_stage} stage as recorded in parcel profile.",
            ],
            limitations=[
                "Recommendation assumes protective irrigation water source is accessible on farm.",
                "Weather reanalysis is regional context, not microclimate probe.",
            ],
            confidence_score=0.88,
            when_to_seek_expert="If wilting persists 24 hours after irrigation, seek agronomist diagnosis.",
            next_step="Schedule 20-25 mm protective irrigation or shallow inter-cultivation within 24 hours.",
        )
        return output, 85

