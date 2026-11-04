"""Sensor Reliability Agent implementation.

Evaluates sensor telemetry integrity, differentiates natural flatlines from sensor faults,
and issues structured reliability assessments determining whether downstream agricultural analysis
is safe to proceed.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from agri_investigator.agents.base import BaseSpecialistAgent
from agri_investigator.models import AgentRole, SensorReliabilityOutput


class SensorReliabilityInput(BaseModel):
    """Input payload for Sensor Reliability Agent."""
    candidate_alert: Dict[str, Any]
    sensor_health_results: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    recent_observations: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    provenance: Optional[str] = "mixed"


class SensorReliabilityAgent(BaseSpecialistAgent):
    """Specialist agent assessing telemetry reliability and data provenance."""

    def __init__(self, mock_mode: bool = False) -> None:
        super().__init__(
            role=AgentRole.SENSOR_RELIABILITY,
            name="Sensor Reliability Specialist",
            version="1.0.0",
            model_name="gemini-2.0-flash",
            mock_mode=mock_mode,
        )

    def get_input_schema(self) -> type[BaseModel]:
        return SensorReliabilityInput

    def get_output_schema(self) -> type[BaseModel]:
        return SensorReliabilityOutput

    def _execute_core(self, validated_input: BaseModel) -> Tuple[BaseModel, int]:
        inp: SensorReliabilityInput = validated_input  # type: ignore

        if self.mock_mode and "default" in self._mock_responses:
            return SensorReliabilityOutput.model_validate(self._mock_responses["default"]), 45

        alert = inp.candidate_alert
        health_state = alert.get("sensor_health_state", "HEALTHY")
        field_id = alert.get("field_id", "unknown-field")
        alert_type = alert.get("risk_type", "UNKNOWN")

        # Stage 11 authoritative health interpretation
        # Suspect or faulty sensors MUST prevent agricultural advice
        is_trustworthy = True
        proceed_to_agronomy = True
        reason_code = "ALL_SENSORS_VALID"
        trusted_inputs: List[str] = []
        untrusted_inputs: List[str] = []
        evidence_refs: List[str] = []
        uncertainty = 0.10

        if health_state in ("FAULTY", "DEGRADED", "SUSPECT"):
            is_trustworthy = False
            proceed_to_agronomy = False
            reason_code = f"SENSOR_{health_state}_DETECTED"
            untrusted_inputs.append(f"sensor_health_state={health_state}")
            evidence_refs.append(f"alert_id={alert.get('alert_id', 'unknown')}")
            uncertainty = 0.85
            summary = (
                f"Telemetry from field {field_id} is classified as {health_state} by Stage 11 forensics. "
                "Downstream crop advisory generation is blocked to prevent ungrounded or hazardous advice."
            )
        else:
            trusted_inputs.append("soil_moisture_primary")
            trusted_inputs.append("weather_ambient_temp")
            evidence_refs.append(f"field_id={field_id}")
            summary = (
                f"Telemetry from field {field_id} is healthy and validated. Natural sensor patterns verified; "
                "safe to proceed with agronomic interpretation."
            )

        # Check for natural rain zero / residual dry exemptions if present
        for h in (inp.sensor_health_results or []):
            if h.get("reason_code") == "NATURAL_RAIN_ZERO":
                reason_code = "NATURAL_RAIN_ZERO"
                trusted_inputs.append("precipitation_gauge_zero_confirmed")
            elif h.get("reason_code") == "STUCK_VALUE":
                is_trustworthy = False
                proceed_to_agronomy = False
                reason_code = "STUCK_VALUE_DETECTED"
                untrusted_inputs.append(h.get("sensor_id", "unknown_sensor"))
                uncertainty = 0.90

        output = SensorReliabilityOutput(
            is_trustworthy=is_trustworthy,
            proceed_to_agronomy=proceed_to_agronomy,
            sensor_health_state=health_state,
            reason_code=reason_code,
            trusted_inputs=trusted_inputs,
            untrusted_inputs=untrusted_inputs,
            evidence_references=evidence_refs,
            uncertainty_score=uncertainty,
            summary=summary,
        )
        return output, 50

