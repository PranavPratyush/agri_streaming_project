"""Deterministic scenario injection adapter for benchmarking sensor fault detectors and crop stress rules."""

from __future__ import annotations

import datetime
import logging
import uuid
from typing import Any, Dict, List, Optional

from agri_contracts import (
    AgriObservationEvent,
    LocationMetadata,
    ObservedVariable,
    ProvenanceClass,
    ProvenanceMetadata,
    QualityFlags,
    SensorHealthFlag,
    SensorPlacementMetadata,
    StandardUnit,
    ValidationStatus,
)
from agri_ingestion.adapters.base import BaseIngestionAdapter
from agri_ingestion.config import IngestionConfig
from agri_ingestion.producer import AgriKafkaProducer

logger = logging.getLogger("agri_ingestion.injected")


class InjectedScenarioAdapter(BaseIngestionAdapter):
    """Generates and publishes reproducible, labeled stress and fault injection scenarios."""

    SCENARIO_TYPES = [
        # Sensor Faults
        "sensor_stuck_value",
        "sensor_spike_out_of_bounds",
        "sensor_linear_drift",
        "sensor_intermittent_dropout",
        # Agronomic Crop Stress
        "drought_drydown_ragi",
        "heat_shock_flowering",
        "fungal_blast_window",
        # Baseline / Transient
        "transient_natural_noise",
    ]

    def __init__(
        self,
        scenario_type: str = "drought_drydown_ragi",
        field_id: Optional[str] = None,
        steps: int = 10,
        config: Optional[IngestionConfig] = None,
        producer: Optional[AgriKafkaProducer] = None,
        dry_run: bool = False,
    ) -> None:
        super().__init__(config=config, producer=producer, dry_run=dry_run)
        if scenario_type not in self.SCENARIO_TYPES:
            raise ValueError(f"Unknown scenario_type '{scenario_type}'. Allowed: {self.SCENARIO_TYPES}")
        self.scenario_type = scenario_type
        self.field_id = field_id or self.config.default_field_id
        self.steps = steps

    @property
    def adapter_name(self) -> str:
        return f"injected_{self.scenario_type}"

    def generate_events(self) -> List[AgriObservationEvent]:
        """Synthesizes deterministic sequence of observations for the selected scenario."""
        events: List[AgriObservationEvent] = []
        base_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=self.steps)
        ingestion_time = datetime.datetime.now(datetime.timezone.utc)

        location = LocationMetadata(
            latitude=self.config.openmeteo_kolar_lat,
            longitude=self.config.openmeteo_kolar_lon,
            elevation_m=self.config.openmeteo_elevation_m,
        )

        provenance = ProvenanceMetadata(
            provenance_class=ProvenanceClass.INJECTED_SCENARIO,
            dataset_origin=f"scenario_harness:{self.scenario_type}",
            is_synthetic=True,
            scenario_id=self.scenario_type,
            source_uri="synthetic://internal/harness",
            raw_payload_hash=f"synthetic:{self.scenario_type}:{self.steps}",
        )

        for step in range(self.steps):
            event_time = base_time + datetime.timedelta(hours=step)

            if self.scenario_type == "sensor_stuck_value":
                # Flatline: Soil moisture identical to 4 decimal places across days
                val = 0.2800
                var = ObservedVariable.SOIL_MOISTURE_15CM
                unit = StandardUnit.M3_PER_M3
                health_flag = SensorHealthFlag.STUCK_VALUE

            elif self.scenario_type == "sensor_spike_out_of_bounds":
                # Step 5 has non-physical spike of 95.0 °C
                val = 95.0 if step == 5 else 26.5 + (step % 3) * 0.5
                var = ObservedVariable.TEMPERATURE_2M
                unit = StandardUnit.CELSIUS
                health_flag = SensorHealthFlag.OUT_OF_BOUNDS if step == 5 else SensorHealthFlag.HEALTHY

            elif self.scenario_type == "sensor_linear_drift":
                # Artificial upward calibration drift of +0.015 m3/m3 per step
                val = 0.20 + (step * 0.02)
                var = ObservedVariable.SOIL_MOISTURE_15CM
                unit = StandardUnit.M3_PER_M3
                health_flag = SensorHealthFlag.DRIFT_ANOMALY if step > 5 else SensorHealthFlag.HEALTHY

            elif self.scenario_type == "sensor_intermittent_dropout":
                # Zero / null dropout at step 4 and 7
                val = 0.0 if step in (4, 7) else 28.0
                var = ObservedVariable.TEMPERATURE_2M
                unit = StandardUnit.CELSIUS
                health_flag = SensorHealthFlag.DROPOUT if step in (4, 7) else SensorHealthFlag.HEALTHY

            elif self.scenario_type == "drought_drydown_ragi":
                # Severe depletion below PWP (<0.09 m3/m3 for Red Sandy Loam)
                val = max(0.05, 0.22 - (step * 0.02))
                var = ObservedVariable.SOIL_MOISTURE_15CM
                unit = StandardUnit.M3_PER_M3
                health_flag = SensorHealthFlag.HEALTHY

            elif self.scenario_type == "heat_shock_flowering":
                # Sustained temperatures > 38.0 °C
                val = 35.0 + (step * 0.8)
                var = ObservedVariable.TEMPERATURE_2M
                unit = StandardUnit.CELSIUS
                health_flag = SensorHealthFlag.HEALTHY

            elif self.scenario_type == "fungal_blast_window":
                # High humidity (>90%) with warm temperatures (24°C)
                val = 91.0 + (step % 4) * 1.5
                var = ObservedVariable.RELATIVE_HUMIDITY_2M
                unit = StandardUnit.PERCENT
                health_flag = SensorHealthFlag.HEALTHY

            else:  # transient_natural_noise
                val = 24.0 + (step % 2) * 0.4
                var = ObservedVariable.TEMPERATURE_2M
                unit = StandardUnit.CELSIUS
                health_flag = SensorHealthFlag.HEALTHY

            ev = AgriObservationEvent(
                event_id=str(uuid.uuid4()),
                schema_version="1.0.0",
                event_time=event_time,
                ingestion_time=ingestion_time,
                field_id=self.field_id,
                idempotency_key=f"scenario:{self.scenario_type}:{self.field_id}:step{step}",
                correlation_id=f"benchmark_{self.scenario_type}",
                provenance=provenance,
                source_provider="scenario_injection_harness",
                sensor_id=f"probe_{self.scenario_type}",
                station_id=None,
                variable=var,
                value=val,
                unit=unit,
                location=location,
                sensor_metadata=SensorPlacementMetadata(
                    depth_cm=15.0 if "soil" in var.value else None,
                    height_m=2.0 if "temperature" in var.value or "humidity" in var.value else None,
                    sensor_model="SyntheticFaultGenerator",
                    serial_number=f"synth_{self.scenario_type}",
                ),
                quality_flags=QualityFlags(
                    is_imputed=False,
                    is_out_of_range=val > 50.0 if "temp" in var.value else False,
                    freshness_latency_sec=0.0,
                    sensor_health_flag=health_flag,
                ),
                validation_status=ValidationStatus.UNKNOWN,
            )
            events.append(ev)

        return events

    def poll_once(self) -> int:
        """Generates the scenario and publishes all events to Kafka."""
        events = self.generate_events()
        published_count = 0
        for ev in events:
            if self.producer.publish_observation(ev, topic=self.config.topic_raw_observations):
                published_count += 1

        self.producer.flush(timeout=5.0)
        logger.info(
            "Adapter '%s' injected %d synthetic scenario events into topic '%s'.",
            self.adapter_name,
            published_count,
            self.config.topic_raw_observations,
        )
        return published_count
