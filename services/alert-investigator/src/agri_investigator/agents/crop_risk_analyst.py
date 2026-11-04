"""Crop Risk Analyst Agent implementation.

Synthesizes upstream sensor reliability and field context with deterministic risk engine
features, formulating a structured agronomic risk hypothesis and an explicit evidence request
for the knowledge retrieval stage.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from agri_investigator.agents.base import BaseSpecialistAgent
from agri_investigator.models import (
    AgentRole,
    AgronomyEvidenceRequest,
    CropRiskAnalystOutput,
    FieldContextOutput,
    SensorReliabilityOutput,
)


class CropRiskAnalystInput(BaseModel):
    """Input payload for Crop Risk Analyst Agent."""
    candidate_alert: Dict[str, Any]
    reliability_assessment: SensorReliabilityOutput
    field_context: FieldContextOutput
    deterministic_risk_features: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CropRiskAnalystAgent(BaseSpecialistAgent):
    """Specialist agent synthesizing telemetry integrity and environmental context."""

    def __init__(self, mock_mode: bool = False) -> None:
        super().__init__(
            role=AgentRole.CROP_RISK_ANALYST,
            name="Crop Risk Analyst Specialist",
            version="1.0.0",
            model_name="gemini-2.0-flash",
            mock_mode=mock_mode,
        )

    def get_input_schema(self) -> type[BaseModel]:
        return CropRiskAnalystInput

    def get_output_schema(self) -> type[BaseModel]:
        return CropRiskAnalystOutput

    def _execute_core(self, validated_input: BaseModel) -> Tuple[BaseModel, int]:
        inp: CropRiskAnalystInput = validated_input  # type: ignore

        if self.mock_mode and "default" in self._mock_responses:
            return CropRiskAnalystOutput.model_validate(self._mock_responses["default"]), 60

        alert = inp.candidate_alert
        rel = inp.reliability_assessment
        ctx = inp.field_context

        # Extract deterministic metrics strictly without recalculating
        csi = float(alert.get("composite_stress_index", alert.get("csi_score", 0.72)))
        severity = alert.get("severity", "HIGH")
        risk_type = alert.get("risk_type", "SOIL_MOISTURE_DEPLETION")

        supporting_features: List[str] = [
            f"alert_id:{alert.get('alert_id', 'unknown')}",
            f"deterministic_csi:{csi:.2f}",
        ]
        contradictory_evidence: List[str] = []

        # Corroborate with sensor reliability
        if not rel.is_trustworthy:
            contradictory_evidence.append(f"Sensor unreliability: {rel.reason_code}")
            hypothesis = (
                f"Candidate alert {alert.get('alert_id')} reflects an instrumentation anomaly "
                f"({rel.sensor_health_state}) rather than physiological crop water stress."
            )
            uncertainty = 0.90
            category = "SENSOR_ARTEFACT"
            topics = ["sensor_fault_recovery"]
            questions = ["How to re-verify physical sensor calibration in dryland soils?"]
        else:
            supporting_features.extend(rel.trusted_inputs)
            hypothesis = (
                f"Candidate alert indicates genuine {risk_type} (CSI: {csi:.2f}) on {ctx.crop_variety} "
                f"at {ctx.growth_stage} in {ctx.soil_type}. Available water is depleted beyond safety threshold."
            )
            uncertainty = 0.15
            category = "MOISTURE_DEFICIT" if "MOISTURE" in risk_type else "COMBINED_STRESS"
            topics = ["water_requirements", "drought_contingency", "soil_water_dynamics"]
            questions = [
                f"What is the critical moisture threshold for {ctx.crop_variety} during {ctx.growth_stage}?",
                "What non-chemical soil conservation measures are recommended during mid-season dry spells?",
            ]

        evidence_req = AgronomyEvidenceRequest(
            query=f"Moisture stress contingency management for {ctx.crop_variety} during {ctx.growth_stage}",
            topics=topics,
            target_crop="Finger Millet",
            growth_stage=ctx.growth_stage,
            soil_type=ctx.soil_type,
            region="Karnataka Zone 5 / Kolar",
            specific_questions=questions,
        )

        output = CropRiskAnalystOutput(
            risk_hypothesis=hypothesis,
            severity=severity,
            risk_category=category,
            deterministic_csi=csi,
            supporting_feature_ids=supporting_features,
            contradictory_evidence=contradictory_evidence,
            uncertainty_score=uncertainty,
            evidence_request=evidence_req,
        )
        return output, 65

