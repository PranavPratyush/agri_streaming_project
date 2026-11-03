"""Kafka streaming risk service consuming observations and publishing candidate crop alerts."""

from datetime import datetime, timezone
import json
import logging
from typing import Any

from agri_contracts.enums import CropRiskLevel, ObservedVariable, ProvenanceClass
from agri_contracts.models.crop_risk import CropRiskCandidateAlertEvent
from agri_contracts.models.observation import AgriObservationEvent
from agri_risk_engine.risk.engine import DeterministicCropRiskEngine
from agri_risk_engine.risk.field_profile import FieldProfile, get_verified_kolar_ragi_profile

logger = logging.getLogger("agri_risk_engine.risk.kafka_service")


class CropRiskKafkaService:
    """Service consuming validated observations and publishing candidate alerts to agri.candidate-alerts."""

    def __init__(
        self,
        bootstrap_servers: str = "127.0.0.1:9092",
        output_topic: str = "agri.candidate-alerts",
        field_profiles: dict[str, FieldProfile] | None = None,
        rule_version: str = "1.0.0",
    ) -> None:
        self.bootstrap_servers = bootstrap_servers
        self.output_topic = output_topic
        self.profiles: dict[str, FieldProfile] = field_profiles or {
            "field_kolar_ragi_01": get_verified_kolar_ragi_profile("field_kolar_ragi_01"),
        }
        self.engine = DeterministicCropRiskEngine(rule_version=rule_version)

    def process_field_telemetry(
        self,
        field_id: str,
        event_time: datetime,
        temperature_c: float,
        relative_humidity_pct: float,
        soil_moisture_m3_m3: float | None = None,
        soil_moisture_provenance: ProvenanceClass = ProvenanceClass.PHYSICAL_SENSOR,
        precipitation_mm: float = 0.0,
        vpd_kpa: float | None = None,
        wind_speed_mps: float = 1.5,
        leaf_wetness_hours: float = 0.0,
        sensor_health_status: str = "HEALTHY",
        is_sensor_suppressed: bool = False,
    ) -> CropRiskCandidateAlertEvent:
        """Evaluate field telemetry against the registered field profile and return candidate alert event."""
        profile = self.profiles.get(field_id)

        alert_event = self.engine.evaluate_field_risk(
            field_profile=profile,
            event_time=event_time,
            temperature_c=temperature_c,
            relative_humidity_pct=relative_humidity_pct,
            soil_moisture_m3_m3=soil_moisture_m3_m3,
            soil_moisture_provenance=soil_moisture_provenance,
            precipitation_mm=precipitation_mm,
            vpd_kpa=vpd_kpa,
            wind_speed_mps=wind_speed_mps,
            leaf_wetness_hours=leaf_wetness_hours,
            sensor_health_status=sensor_health_status,
            is_sensor_suppressed=is_sensor_suppressed,
        )

        if alert_event.is_suppressed:
            logger.info(
                f"[Alert Suppressed/Abstained] Field '{field_id}': "
                f"risk_type='{alert_event.risk_type}', reason='{alert_event.suppression_reason}'"
            )
        else:
            logger.warning(
                f"[CANDIDATE ALERT EMITTED] Field '{field_id}': "
                f"risk_type='{alert_event.risk_type}', level='{alert_event.risk_level.value}', "
                f"CSI={alert_event.composite_stress_index:.2f}. "
                f"Dispatching to Bounded Alert Investigator."
            )

        return alert_event

