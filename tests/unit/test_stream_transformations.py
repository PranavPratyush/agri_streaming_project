"""Unit tests for PySpark Structured Streaming transformations, feature formulas, and schemas."""

import math
import pytest
from datetime import datetime, timezone
import uuid

from agri_contracts.enums import (
    ObservedVariable,
    ProvenanceClass,
    StandardUnit,
    ValidationStatus,
)
from agri_stream_processor.config import StreamProcessorConfig
from agri_stream_processor.features import (
    calculate_dew_point,
    calculate_leaf_wetness_proxy,
    calculate_saturation_vapor_pressure,
    calculate_soil_moisture_depletion_rate,
    calculate_vapor_pressure_deficit,
)
from agri_stream_processor.schemas import (
    get_dead_letter_schema,
    get_observation_schema,
    get_provenance_schema,
    get_weather_schema,
)
from agri_stream_processor.validation import (
    create_dead_letter_dict,
    validate_observation_dict,
)


# ===========================================================================
# 1. Agronomic Feature Engineering Tests
# ===========================================================================

class TestFeatureEngineeringMath:
    """Test pure mathematical formulations for derived agronomic features."""

    def test_saturation_vapor_pressure_at_standard_points(self) -> None:
        """Verify Tetens equation against known meteorological reference points."""
        # At 0 °C, es is approx 0.611 kPa
        es_0 = calculate_saturation_vapor_pressure(0.0)
        assert pytest.approx(es_0, rel=1e-2) == 0.611

        # At 20 °C, es is approx 2.34 kPa
        es_20 = calculate_saturation_vapor_pressure(20.0)
        assert pytest.approx(es_20, rel=1e-2) == 2.338

        # At 35 °C (hot tropical day in Kolar), es is approx 5.62 kPa
        es_35 = calculate_saturation_vapor_pressure(35.0)
        assert pytest.approx(es_35, rel=1e-2) == 5.622

    def test_vapor_pressure_deficit_bounds(self) -> None:
        """VPD must be 0 at 100% RH and strictly increase as air dries."""
        temp = 28.0
        # 100% RH -> zero deficit
        vpd_saturated = calculate_vapor_pressure_deficit(temp, 100.0)
        assert vpd_saturated == 0.0

        # 50% RH -> positive deficit
        vpd_50 = calculate_vapor_pressure_deficit(temp, 50.0)
        assert vpd_50 > 1.0

        # 20% RH -> higher deficit
        vpd_20 = calculate_vapor_pressure_deficit(temp, 20.0)
        assert vpd_20 > vpd_50

        # Invalid RH bounds must raise ValueError
        with pytest.raises(ValueError):
            calculate_vapor_pressure_deficit(temp, -5.0)
        with pytest.raises(ValueError):
            calculate_vapor_pressure_deficit(temp, 105.0)

    def test_dew_point_magnus_formula(self) -> None:
        """Dew point must equal ambient temperature at 100% RH."""
        temp = 25.0
        dp_100 = calculate_dew_point(temp, 100.0)
        assert pytest.approx(dp_100, abs=0.1) == temp

        # At lower RH, dew point must be lower than ambient temperature
        dp_60 = calculate_dew_point(temp, 60.0)
        assert dp_60 < temp
        assert pytest.approx(dp_60, abs=0.5) == 16.7

    def test_leaf_wetness_proxy_bounds_and_transitions(self) -> None:
        """Leaf wetness proxy must remain in [0.0, 1.0] and trigger during dew formation."""
        # Low humidity (e.g. 40%) -> exactly 0.0
        lw_dry = calculate_leaf_wetness_proxy(temp_c=30.0, rh_pct=40.0)
        assert lw_dry == 0.0

        # High humidity (95%) and small dew depression (0.2 °C) -> close to 1.0
        lw_dew = calculate_leaf_wetness_proxy(temp_c=18.0, rh_pct=95.0, dew_point_c=17.8)
        assert lw_dew >= 0.8
        assert lw_dew <= 1.0

        # High humidity (85%) but larger dew depression (3.0 °C) -> moderate/low
        lw_moderate = calculate_leaf_wetness_proxy(temp_c=25.0, rh_pct=85.0, dew_point_c=22.0)
        assert 0.0 <= lw_moderate < 0.5

    def test_soil_moisture_depletion_rate(self) -> None:
        """Depletion rate must accurately report drying and wetting rates."""
        # Drying from 0.25 to 0.23 over 2 hours
        rate_drying = calculate_soil_moisture_depletion_rate(
            current_sm=0.23, previous_sm=0.25, delta_hours=2.0
        )
        assert pytest.approx(rate_drying, abs=1e-5) == 0.01000

        # Infiltration (rain/irrigation) from 0.18 to 0.28 over 1 hour
        rate_wetting = calculate_soil_moisture_depletion_rate(
            current_sm=0.28, previous_sm=0.18, delta_hours=1.0
        )
        assert pytest.approx(rate_wetting, abs=1e-5) == -0.10000

        # Zero delta hours must return 0.0 safely
        rate_zero = calculate_soil_moisture_depletion_rate(0.20, 0.20, 0.0)
        assert rate_zero == 0.0


# ===========================================================================
# 2. PySpark Canonical Schema Tests
# ===========================================================================

class TestPySparkSchemas:
    """Verify PySpark StructType schemas match canonical event contracts."""

    def test_observation_schema_fields(self) -> None:
        schema = get_observation_schema()
        field_names = [f.name for f in schema.fields]

        assert "event_id" in field_names
        assert "schema_version" in field_names
        assert "event_time" in field_names
        assert "field_id" in field_names
        assert "idempotency_key" in field_names
        assert "variable" in field_names
        assert "value" in field_names
        assert "unit" in field_names
        assert "provenance" in field_names
        assert "location" in field_names
        assert "sensor_metadata" in field_names
        assert "quality_flags" in field_names

    def test_weather_schema_fields(self) -> None:
        schema = get_weather_schema()
        field_names = [f.name for f in schema.fields]

        assert "event_id" in field_names
        assert "forecast_horizon_hours" in field_names
        assert "temperature_2m_c" in field_names
        assert "relative_humidity_2m_pct" in field_names
        assert "reanalysis_soil_moisture_0_7cm" in field_names
        assert "location" in field_names

    def test_dead_letter_schema_fields(self) -> None:
        schema = get_dead_letter_schema()
        field_names = [f.name for f in schema.fields]

        assert "dlq_id" in field_names
        assert "failed_topic" in field_names
        assert "error_reason" in field_names
        assert "error_class" in field_names
        assert "raw_payload" in field_names
        assert "failed_at" in field_names


# ===========================================================================
# 3. Stream Validation & DLQ Handling Tests
# ===========================================================================

class TestStreamValidationAndDLQ:
    """Verify validation boundaries, unit checking, and DLQ serialization."""

    def test_valid_observation_passes(self) -> None:
        record = {
            "event_id": str(uuid.uuid4()),
            "schema_version": "1.0.0",
            "event_time": datetime.now(timezone.utc).isoformat(),
            "field_id": "field_kolar_ragi_01",
            "idempotency_key": "kolar:temp:12345",
            "variable": "temperature_2m",
            "value": 28.5,
            "unit": "celsius",
        }
        is_valid, reason = validate_observation_dict(record)
        assert is_valid is True
        assert reason is None

    def test_missing_mandatory_field_fails(self) -> None:
        record = {
            "event_id": str(uuid.uuid4()),
            # missing field_id
            "variable": "temperature_2m",
            "value": 28.5,
            "unit": "celsius",
        }
        is_valid, reason = validate_observation_dict(record)
        assert is_valid is False
        assert "Missing required field" in reason

    def test_out_of_bounds_value_fails(self) -> None:
        record = {
            "event_id": str(uuid.uuid4()),
            "schema_version": "1.0.0",
            "event_time": datetime.now(timezone.utc).isoformat(),
            "field_id": "field_kolar_ragi_01",
            "idempotency_key": "kolar:temp:12345",
            "variable": "temperature_2m",
            "value": 85.0,  # exceeds 55 °C bound
            "unit": "celsius",
        }
        is_valid, reason = validate_observation_dict(record)
        assert is_valid is False
        assert "out of plausible agronomic range" in reason

    def test_unit_mismatch_fails(self) -> None:
        record = {
            "event_id": str(uuid.uuid4()),
            "schema_version": "1.0.0",
            "event_time": datetime.now(timezone.utc).isoformat(),
            "field_id": "field_kolar_ragi_01",
            "idempotency_key": "kolar:temp:12345",
            "variable": "temperature_2m",
            "value": 85.0,
            "unit": "fahrenheit",  # unnormalized provider unit
        }
        is_valid, reason = validate_observation_dict(record)
        assert is_valid is False
        assert "Unit mismatch" in reason

    def test_dead_letter_envelope_creation(self) -> None:
        dlq = create_dead_letter_dict(
            raw_payload='{"corrupt": true}',
            failed_topic="agri.sensor-readings",
            error_reason="Missing mandatory event_id",
            error_class="ValidationError",
            correlation_id="trace-abc-123",
            partition=0,
            offset=42,
        )
        assert dlq["failed_topic"] == "agri.sensor-readings"
        assert dlq["source_partition"] == 0
        assert dlq["source_offset"] == 42
        assert dlq["error_reason"] == "Missing mandatory event_id"
        assert dlq["correlation_id"] == "trace-abc-123"
        assert uuid.UUID(dlq["dlq_id"]).version == 4


# ===========================================================================
# 4. Configuration Tests
# ===========================================================================

class TestStreamProcessorConfig:
    """Verify configuration defaults, topic mappings, and checkpoint paths."""

    def test_default_config_parameters(self) -> None:
        cfg = StreamProcessorConfig()
        assert cfg.topic_sensor_readings == "agri.sensor-readings"
        assert cfg.topic_weather_data == "agri.weather-data"
        assert cfg.topic_validated_observations == "agri.validated-observations"
        assert cfg.topic_dead_letter_queue == "agri.dead-letter-queue"
        assert cfg.watermark_duration == "10 minutes"
        assert cfg.tumbling_window_duration == "5 minutes"
        assert cfg.sliding_window_duration == "30 minutes"
        assert cfg.trigger_interval == "5 seconds"

    def test_checkpoint_subpath_generation(self) -> None:
        cfg = StreamProcessorConfig(checkpoint_dir="/opt/checkpoints")
        valid_path = cfg.get_query_checkpoint_path("validated_observations")
        dlq_path = cfg.get_query_checkpoint_path("dead_letter_queue")

        assert valid_path == "/opt/checkpoints/validated_observations"
        assert dlq_path == "/opt/checkpoints/dead_letter_queue"

