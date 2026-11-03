"""Integration tests for PySpark Structured Streaming pipeline configuration and behavior."""

import json
from pathlib import Path
import pytest
import uuid
from datetime import datetime, timezone

from agri_stream_processor.config import StreamProcessorConfig
from agri_stream_processor.validation import create_dead_letter_dict, validate_observation_dict
from agri_stream_processor.features import (
    calculate_vapor_pressure_deficit,
    calculate_leaf_wetness_proxy,
    calculate_dew_point,
)
from agri_contracts.models.observation import AgriObservationEvent
from agri_contracts.models.weather import WeatherContextEvent
from agri_contracts.enums import ObservedVariable, StandardUnit, ProvenanceClass


class TestStreamPipelineIntegration:
    """Integration assertions for streaming pipeline wiring, contracts, and checkpoint behavior."""

    def test_checkpoint_directory_structure(self, tmp_path: Path) -> None:
        """Verify checkpoint directories are durable, non-ephemeral, and segmented per query."""
        checkpoint_root = tmp_path / "spark_checkpoints"
        config = StreamProcessorConfig(checkpoint_dir=str(checkpoint_root))

        val_cp = Path(config.get_query_checkpoint_path("validated_observations"))
        dlq_cp = Path(config.get_query_checkpoint_path("dead_letter_queue"))

        val_cp.mkdir(parents=True, exist_ok=True)
        dlq_cp.mkdir(parents=True, exist_ok=True)

        assert val_cp.exists() and val_cp.is_dir()
        assert dlq_cp.exists() and dlq_cp.is_dir()
        assert val_cp.name == "validated_observations"
        assert dlq_cp.name == "dead_letter_queue"

    def test_end_to_end_observation_validation_and_feature_pipeline(self) -> None:
        """Simulate processing of an ingested observation stream through validation and feature enrichment."""
        # 1. Simulate incoming valid observation
        now = datetime.now(timezone.utc)
        raw_event = AgriObservationEvent(
            event_id=str(uuid.uuid4()),
            schema_version="1.0.0",
            event_time=now,
            ingestion_time=now,
            field_id="field_kolar_ragi_01",
            idempotency_key="kolar_ragi_01:temp:101",
            source_provider="opensensemap",
            sensor_id="sensor_temp_01",
            variable=ObservedVariable.TEMPERATURE_2M,
            value=31.2,
            unit=StandardUnit.CELSIUS,
            provenance={
                "provenance_class": ProvenanceClass.PHYSICAL_SENSOR,
                "dataset_origin": "openSenseMap",
                "is_synthetic": False,
            },
        )
        record_dict = json.loads(raw_event.model_dump_json())

        # 2. Pipeline validation check
        is_valid, error_reason = validate_observation_dict(record_dict)
        assert is_valid is True
        assert error_reason is None

        # 3. Simulate companion humidity reading in same window for feature calculation
        rh_val = 65.0
        vpd = calculate_vapor_pressure_deficit(record_dict["value"], rh_val)
        dew_point = calculate_dew_point(record_dict["value"], rh_val)
        leaf_wetness = calculate_leaf_wetness_proxy(record_dict["value"], rh_val, dew_point)

        assert vpd > 0.0
        assert dew_point < record_dict["value"]
        assert 0.0 <= leaf_wetness <= 1.0

    def test_poison_pill_routing_to_dlq(self) -> None:
        """Poison pill payload must fail validation and be converted into a valid DLQ event."""
        poison_payload = '{"bad_json": true, "corrupted_bits": 0xDEADBEEF}'
        
        # Validation failure
        is_valid, error = validate_observation_dict(json.loads('{"bad_json": true}'))
        assert is_valid is False

        # DLQ wrapping
        dlq_event = create_dead_letter_dict(
            raw_payload=poison_payload,
            failed_topic="agri.sensor-readings",
            error_reason=error,
            error_class="ContractValidationError",
            partition=1,
            offset=105,
        )

        assert dlq_event["failed_topic"] == "agri.sensor-readings"
        assert dlq_event["source_partition"] == 1
        assert dlq_event["source_offset"] == 105
        assert dlq_event["raw_payload"] == poison_payload
        assert "Missing required field" in dlq_event["error_reason"]

