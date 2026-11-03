"""Integration test for SensorHealthKafkaService streaming evaluation and advisory suppression."""

from datetime import datetime, timedelta, timezone
import pytest
import uuid

from agri_contracts.enums import (
    HealthState,
    ObservedVariable,
    ProvenanceClass,
    StandardUnit,
)
from agri_contracts.models.observation import AgriObservationEvent
from agri_risk_engine.health import (
    ForensicReasonCode,
    SensorHealthKafkaService,
)


class TestSensorHealthKafkaServiceIntegration:
    """Verify streaming tracking, history accumulation, and advisory gating."""

    def setup_method(self) -> None:
        self.service = SensorHealthKafkaService()
        self.base_time = datetime(2026, 11, 3, 10, 0, 0, tzinfo=timezone.utc)

    def test_multi_cycle_stream_tracking_and_stuck_detection(self) -> None:
        """Simulate an ingested sensor stream that starts healthy and then freezes."""
        field_id = "field_kolar_01"
        sensor_id = "probe_temp_live_01"

        # 1. Stream 5 varying healthy readings
        for i, val in enumerate([24.0, 24.5, 25.1, 25.8, 26.2]):
            t = self.base_time + timedelta(minutes=5 * i)
            obs = AgriObservationEvent(
                event_id=str(uuid.uuid4()),
                schema_version="1.0.0",
                event_time=t,
                ingestion_time=t,
                field_id=field_id,
                sensor_id=sensor_id,
                idempotency_key=f"kolar:temp:{i}",
                source_provider="opensensemap",
                variable=ObservedVariable.TEMPERATURE_2M,
                value=val,
                unit=StandardUnit.CELSIUS,
                provenance={
                    "provenance_class": ProvenanceClass.PHYSICAL_SENSOR,
                    "dataset_origin": "openSenseMap",
                    "is_synthetic": False,
                },
            )
            result = self.service.process_observation(obs, now=t)
            assert result.health_state in (HealthState.HEALTHY, HealthState.UNKNOWN)
            assert result.is_usable_for_advisory is True

        # 2. Sensor freezes at 26.2°C for 15 consecutive readings
        for j in range(5, 20):
            t = self.base_time + timedelta(minutes=5 * j)
            obs = AgriObservationEvent(
                event_id=str(uuid.uuid4()),
                schema_version="1.0.0",
                event_time=t,
                ingestion_time=t,
                field_id=field_id,
                sensor_id=sensor_id,
                idempotency_key=f"kolar:temp:{j}",
                source_provider="opensensemap",
                variable=ObservedVariable.TEMPERATURE_2M,
                value=26.2,  # Stuck identical reading
                unit=StandardUnit.CELSIUS,
                provenance={
                    "provenance_class": ProvenanceClass.PHYSICAL_SENSOR,
                    "dataset_origin": "openSenseMap",
                    "is_synthetic": False,
                },
            )
            result = self.service.process_observation(obs, now=t)

        # After 15 frozen cycles, state must be FAULTY with ERR_STUCK_VALUE and advisory must be blocked!
        assert result.health_state == HealthState.FAULTY
        assert result.reason_code == ForensicReasonCode.ERR_STUCK_VALUE.value
        assert result.is_suppressed is True
        assert result.is_usable_for_advisory is False

    def test_advisory_safety_gate_blocks_on_out_of_bounds(self) -> None:
        """Plausibility violation must immediately trigger safety suppression."""
        obs = AgriObservationEvent(
            event_id=str(uuid.uuid4()),
            schema_version="1.0.0",
            event_time=self.base_time,
            ingestion_time=self.base_time,
            field_id="field_kolar_01",
            sensor_id="probe_temp_02",
            idempotency_key="kolar:temp:oob",
            source_provider="opensensemap",
            variable=ObservedVariable.TEMPERATURE_2M,
            value=82.0,  # Impossible terrestrial temperature
            unit=StandardUnit.CELSIUS,
            provenance={
                "provenance_class": ProvenanceClass.PHYSICAL_SENSOR,
                "dataset_origin": "openSenseMap",
                "is_synthetic": False,
            },
        )
        result = self.service.process_observation(obs, now=self.base_time)
        assert result.health_state == HealthState.FAULTY
        assert result.reason_code == ForensicReasonCode.ERR_IMPLAUSIBLE_RANGE.value
        assert result.is_usable_for_advisory is False
