"""Forensic health state models, diagnostic reason codes, evidence structures, and advisory gating."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agri_contracts.enums import HealthState, SensorHealthFlag


class ForensicReasonCode(str, Enum):
    """Standardized forensic diagnostic codes for sensor health evaluation."""
    
    # Healthy / Normal Baselines
    OK_HEALTHY = "OK_HEALTHY"
    OK_CORROBORATED_NATURAL_FLATLINE = "OK_CORROBORATED_NATURAL_FLATLINE"
    OK_MODELLED_REANALYSIS_BYPASS = "OK_MODELLED_REANALYSIS_BYPASS"

    # Temporal & Cadence Defects
    ERR_STALE_OBSERVATION = "ERR_STALE_OBSERVATION"
    ERR_EXCESSIVE_AGE = "ERR_EXCESSIVE_AGE"
    ERR_TIMESTAMP_REVERSAL = "ERR_TIMESTAMP_REVERSAL"
    ERR_CLOCK_SKEW = "ERR_CLOCK_SKEW"
    ERR_DUPLICATE_EVENT_ID = "ERR_DUPLICATE_EVENT_ID"
    ERR_IRREGULAR_CADENCE = "ERR_IRREGULAR_CADENCE"

    # Signal & Hardware Defects
    ERR_MISSING_DROPOUT = "ERR_MISSING_DROPOUT"
    ERR_STUCK_VALUE = "ERR_STUCK_VALUE"
    ERR_IMPLAUSIBLE_RANGE = "ERR_IMPLAUSIBLE_RANGE"
    ERR_ABRUPT_SPIKE = "ERR_ABRUPT_SPIKE"
    ERR_SENSOR_DRIFT = "ERR_SENSOR_DRIFT"

    # Outage Scopes
    ERR_SOURCE_OUTAGE = "ERR_SOURCE_OUTAGE"
    ERR_SENSOR_OUTAGE = "ERR_SENSOR_OUTAGE"

    # Ambiguous / Boundary States
    SUSPECT_UNVERIFIED_FLATLINE = "SUSPECT_UNVERIFIED_FLATLINE"
    SUSPECT_INSUFFICIENT_CORROBORATION = "SUSPECT_INSUFFICIENT_CORROBORATION"
    SUSPECT_CADENCE_JITTER = "SUSPECT_CADENCE_JITTER"
    UNKNOWN_INSUFFICIENT_HISTORY = "UNKNOWN_INSUFFICIENT_HISTORY"


@dataclass
class HealthEvidence:
    """Structured evidence package supporting a deterministic forensic diagnosis."""
    detector_name: str
    reason_code: ForensicReasonCode
    metrics: dict[str, Any] = field(default_factory=dict)
    thresholds_applied: dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "detector_name": self.detector_name,
            "reason_code": self.reason_code.value,
            "metrics": self.metrics,
            "thresholds_applied": self.thresholds_applied,
            "summary": self.summary,
        }


def is_measurement_usable_for_advisory(
    health_state: HealthState,
    is_suppressed: bool = False,
    allow_suspect: bool = False,
) -> bool:
    """Safety gate evaluating whether an observation is reliable enough for agronomic recommendations.
    
    In accordance with .agents/rules/agronomic-safety.md:
    Faulty, stale, or suppressed measurements must NEVER trigger or bias crop risk recommendations.
    """
    if is_suppressed:
        return False

    if health_state in (HealthState.FAULTY, HealthState.STALE):
        return False

    if health_state == HealthState.SUSPECT:
        return allow_suspect

    # HEALTHY and UNKNOWN (with explicit non-fault state) are permitted
    return True

