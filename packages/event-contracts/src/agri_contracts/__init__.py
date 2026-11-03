"""AgriKafka-Agent Canonical Event Contracts Package."""

from agri_contracts.enums import (
    ProvenanceClass,
    ObservedVariable,
    StandardUnit,
    ValidationStatus,
    SensorHealthFlag,
    HealthState,
    CropRiskLevel,
    InvestigationDecision,
    HumanFeedbackDecision,
)
from agri_contracts.models.base import (
    AgriKafkaBaseEvent,
    LocationMetadata,
    SensorPlacementMetadata,
    QualityFlags,
    ProvenanceMetadata,
)
from agri_contracts.models.observation import AgriObservationEvent
from agri_contracts.models.weather import WeatherContextEvent
from agri_contracts.models.sensor_health import SensorHealthResultEvent
from agri_contracts.models.crop_risk import CropRiskCandidateAlertEvent
from agri_contracts.models.investigation import AlertInvestigationResultEvent
from agri_contracts.models.approval import HumanDecisionEvent
from agri_contracts.models.dead_letter import DeadLetterRecordEvent
from agri_contracts.validation import (
    VARIABLE_BOUNDS,
    validate_observation_bounds,
    convert_to_standard_unit,
    wrap_in_dead_letter,
)

__all__ = [
    # Enums
    "ProvenanceClass",
    "ObservedVariable",
    "StandardUnit",
    "ValidationStatus",
    "SensorHealthFlag",
    "HealthState",
    "CropRiskLevel",
    "InvestigationDecision",
    "HumanFeedbackDecision",
    # Metadata
    "LocationMetadata",
    "SensorPlacementMetadata",
    "QualityFlags",
    "ProvenanceMetadata",
    # Event Contracts
    "AgriKafkaBaseEvent",
    "AgriObservationEvent",
    "WeatherContextEvent",
    "SensorHealthResultEvent",
    "CropRiskCandidateAlertEvent",
    "AlertInvestigationResultEvent",
    "HumanDecisionEvent",
    "DeadLetterRecordEvent",
    # Validation & Utilities
    "VARIABLE_BOUNDS",
    "validate_observation_bounds",
    "convert_to_standard_unit",
    "wrap_in_dead_letter",
]

__version__ = "1.0.0"
