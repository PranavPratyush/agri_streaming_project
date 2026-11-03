"""Comprehensive contract and schema validation test suite for AgriKafka-Agent."""

import json
from pathlib import Path
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from agri_contracts import (
    ProvenanceClass,
    ObservedVariable,
    StandardUnit,
    ValidationStatus,
    SensorHealthFlag,
    CropRiskLevel,
    InvestigationDecision,
    HumanFeedbackDecision,
    LocationMetadata,
    SensorPlacementMetadata,
    QualityFlags,
    ProvenanceMetadata,
    AgriObservationEvent,
    WeatherContextEvent,
    SensorHealthResultEvent,
    CropRiskCandidateAlertEvent,
    AlertInvestigationResultEvent,
    HumanDecisionEvent,
    DeadLetterRecordEvent,
    validate_observation_bounds,
    convert_to_standard_unit,
    wrap_in_dead_letter,
)

EXAMPLES_DIR = Path(__file__).parents[2] / "packages" / "event-contracts" / "examples"


class TestObservationContracts:
    """Tests for AgriObservationEvent contract and provenance rules."""

    def test_valid_physical_observation(self):
        event = AgriObservationEvent(
            event_time=datetime(2026, 11, 1, 14, 43, 14, tzinfo=timezone.utc),
            field_id="KA_KOLAR_EXTERNAL_01",
            idempotency_key="osm_test_01",
            source_provider="openSenseMap",
            sensor_id="689b2bdc569c2d0007586aea",
            station_id="689b2bdc569c2d0007586ae9",
            variable=ObservedVariable.TEMPERATURE_2M,
            value=25.39,
            unit=StandardUnit.CELSIUS,
            location=LocationMetadata(latitude=11.995079, longitude=79.804492, elevation_m=42.0),
            sensor_metadata=SensorPlacementMetadata(height_m=2.0, sensor_model="Generic temperature sensor"),
            quality_flags=QualityFlags(sensor_health_flag=SensorHealthFlag.HEALTHY),
            validation_status=ValidationStatus.VALID,
            provenance=ProvenanceMetadata(
                provenance_class=ProvenanceClass.PHYSICAL_SENSOR,
                dataset_origin="openSenseMap-Station-Sarvamangalam",
                is_synthetic=False,
                source_uri="https://api.opensensemap.org/boxes/689b2bdc569c2d0007586ae9",
            ),
        )
        assert event.schema_version == "1.0.0"
        assert event.value == 25.39
        assert event.provenance.provenance_class == ProvenanceClass.PHYSICAL_SENSOR
        assert event.sensor_id == "689b2bdc569c2d0007586aea"

    def test_modelled_reanalysis_soil_moisture_null_sensor_id(self):
        """Verifies that reanalysis soil moisture legitimately allows sensor_id=None."""
        event = AgriObservationEvent(
            event_time=datetime(2025, 7, 15, 10, 0, 0, tzinfo=timezone.utc),
            field_id="KA_KOLAR_RAGI_01",
            idempotency_key="era5_kolar_soil_test",
            source_provider="open_meteo_archive",
            sensor_id=None,  # Crucial: Must not fabricate a sensor_id for reanalysis!
            variable=ObservedVariable.SOIL_MOISTURE_0_TO_7CM,
            value=0.243,
            unit=StandardUnit.M3_PER_M3,
            location=LocationMetadata(latitude=13.13, longitude=78.13, elevation_m=822.0),
            sensor_metadata=None,
            provenance=ProvenanceMetadata(
                provenance_class=ProvenanceClass.MODELLED_REANALYSIS,
                dataset_origin="Open-Meteo-ERA5-Land",
                is_synthetic=False,
            ),
        )
        assert event.sensor_id is None
        assert event.sensor_metadata is None
        assert event.provenance.provenance_class == ProvenanceClass.MODELLED_REANALYSIS

    def test_rejection_of_non_finite_values(self):
        """Asserts that NaN, Inf, and -Inf are strictly rejected."""
        with pytest.raises(ValidationError):
            AgriObservationEvent(
                event_time=datetime.now(timezone.utc),
                field_id="KA_TEST",
                idempotency_key="test_nan",
                source_provider="test",
                variable=ObservedVariable.TEMPERATURE_2M,
                value=float("nan"),
                unit=StandardUnit.CELSIUS,
                provenance=ProvenanceMetadata(
                    provenance_class=ProvenanceClass.PHYSICAL_SENSOR,
                    dataset_origin="test",
                    is_synthetic=True,
                ),
            )

        with pytest.raises(ValidationError):
            AgriObservationEvent(
                event_time=datetime.now(timezone.utc),
                field_id="KA_TEST",
                idempotency_key="test_inf",
                source_provider="test",
                variable=ObservedVariable.TEMPERATURE_2M,
                value=float("inf"),
                unit=StandardUnit.CELSIUS,
                provenance=ProvenanceMetadata(
                    provenance_class=ProvenanceClass.PHYSICAL_SENSOR,
                    dataset_origin="test",
                    is_synthetic=True,
                ),
            )

    def test_rejection_of_invalid_uuid(self):
        """Asserts that malformed event_id strings fail validation."""
        with pytest.raises(ValidationError):
            AgriObservationEvent(
                event_id="not-a-valid-uuid",
                event_time=datetime.now(timezone.utc),
                field_id="KA_TEST",
                idempotency_key="test_uuid",
                source_provider="test",
                variable=ObservedVariable.TEMPERATURE_2M,
                value=25.0,
                unit=StandardUnit.CELSIUS,
                provenance=ProvenanceMetadata(
                    provenance_class=ProvenanceClass.PHYSICAL_SENSOR,
                    dataset_origin="test",
                    is_synthetic=True,
                ),
            )


class TestOtherEventContracts:
    """Tests for WeatherContext, SensorHealth, CropRisk, Investigation, HumanApproval, and DLQ."""

    def test_weather_context_contract(self):
        event = WeatherContextEvent(
            event_time=datetime(2026, 11, 1, 20, 0, tzinfo=timezone.utc),
            field_id="KA_KOLAR_RAGI_01",
            idempotency_key="weather_test_01",
            forecast_horizon_hours=24,
            temperature_2m_c=28.5,
            relative_humidity_2m_pct=65.0,
            precipitation_mm=2.5,
            wind_speed_10m_mps=3.4,
            reanalysis_soil_moisture_0_7cm=0.22,
            location=LocationMetadata(latitude=13.13, longitude=78.13, elevation_m=822.0),
            provenance=ProvenanceMetadata(
                provenance_class=ProvenanceClass.FORECAST,
                dataset_origin="Open-Meteo-NWP",
                is_synthetic=False,
            ),
        )
        assert event.forecast_horizon_hours == 24
        assert event.reanalysis_soil_moisture_0_7cm == 0.22

    def test_sensor_health_contract(self):
        event = SensorHealthResultEvent(
            event_time=datetime.now(timezone.utc),
            field_id="KA_KOLAR_RAGI_01",
            idempotency_key="health_test_01",
            sensor_id="probe_soil_01",
            variable=ObservedVariable.SOIL_MOISTURE_15CM,
            health_flag=SensorHealthFlag.STUCK_VALUE,
            confidence_score=0.98,
            detected_anomaly_reason="Zero variance for 24h",
            observed_mean_window=0.18,
            observed_std_window=0.0,
            is_suppressed=True,
            provenance=ProvenanceMetadata(
                provenance_class=ProvenanceClass.DERIVED,
                dataset_origin="HealthEngine",
                is_synthetic=False,
            ),
        )
        assert event.health_flag == SensorHealthFlag.STUCK_VALUE
        assert event.is_suppressed is True

    def test_crop_risk_candidate_contract(self):
        event = CropRiskCandidateAlertEvent(
            event_time=datetime.now(timezone.utc),
            field_id="KA_KOLAR_RAGI_01",
            idempotency_key="risk_test_01",
            alert_id="alert-001",
            crop_name="Finger Millet (Ragi)",
            growth_stage="flowering_grain_filling",
            risk_type="SOIL_MOISTURE_DEFICIT",
            risk_level=CropRiskLevel.HIGH,
            composite_stress_index=0.78,
            soil_depletion_fraction=0.68,
            current_soil_moisture_m3_m3=0.112,
            triggered_threshold="p > 0.60 in Red Sandy Loam",
            evidence_summary="Soil moisture depleted past RAW threshold",
            provenance=ProvenanceMetadata(
                provenance_class=ProvenanceClass.DERIVED,
                dataset_origin="RiskEngine",
                is_synthetic=False,
            ),
        )
        assert event.risk_level == CropRiskLevel.HIGH
        assert event.composite_stress_index == 0.78

    def test_investigation_result_contract_bounds(self):
        """Verifies step count bound (<=4) and citations."""
        event = AlertInvestigationResultEvent(
            event_time=datetime.now(timezone.utc),
            field_id="KA_KOLAR_RAGI_01",
            idempotency_key="invest_test_01",
            alert_id="alert-001",
            decision=InvestigationDecision.ADVISORY_ISSUED,
            is_escalated=True,
            investigation_steps_executed=4,
            tools_invoked=["get_telemetry", "check_health", "query_rag", "synthesize"],
            citations=["ICAR Ragi Package 2023"],
            draft_advisory_kannada="ನೀರು ನೀಡಿ",
            draft_advisory_english="Schedule irrigation",
            approval_token="appr-tok-1234",
            provenance=ProvenanceMetadata(
                provenance_class=ProvenanceClass.DERIVED,
                dataset_origin="BoundedAgent",
                is_synthetic=False,
            ),
        )
        assert event.investigation_steps_executed == 4

        # Verify steps > 4 fails validation
        with pytest.raises(ValidationError):
            AlertInvestigationResultEvent(
                event_time=datetime.now(timezone.utc),
                field_id="KA_KOLAR_RAGI_01",
                idempotency_key="invest_test_02",
                alert_id="alert-002",
                decision=InvestigationDecision.ADVISORY_ISSUED,
                is_escalated=True,
                investigation_steps_executed=5,
                tools_invoked=["step1", "step2", "step3", "step4", "step5"],
                provenance=ProvenanceMetadata(
                    provenance_class=ProvenanceClass.DERIVED,
                    dataset_origin="BoundedAgent",
                    is_synthetic=False,
                ),
            )

    def test_human_decision_contract(self):
        event = HumanDecisionEvent(
            event_time=datetime.now(timezone.utc),
            field_id="KA_KOLAR_RAGI_01",
            idempotency_key="human_test_01",
            alert_id="alert-001",
            approval_token="appr-tok-1234",
            decision=HumanFeedbackDecision.APPROVED,
            operator_id="farmer_01",
            decision_timestamp=datetime.now(timezone.utc),
            provenance=ProvenanceMetadata(
                provenance_class=ProvenanceClass.DERIVED,
                dataset_origin="FarmerPWA",
                is_synthetic=False,
            ),
        )
        assert event.decision == HumanFeedbackDecision.APPROVED

    def test_dead_letter_envelope(self):
        dlq = wrap_in_dead_letter(
            raw_payload='{"corrupt": true}',
            failed_topic="sensor-readings",
            error=ValueError("Invalid variable"),
            partition=2,
            offset=1042,
        )
        assert dlq.failed_topic == "sensor-readings"
        assert dlq.source_partition == 2
        assert dlq.source_offset == 1042
        assert "Invalid variable" in dlq.error_reason


class TestValidationAndConversions:
    """Tests for range bounds checks and unit conversion functions."""

    def test_plausible_bounds_checking(self):
        # Valid temperature
        status, reason = validate_observation_bounds(ObservedVariable.TEMPERATURE_2M, 25.0, StandardUnit.CELSIUS)
        assert status == ValidationStatus.VALID
        assert reason is None

        # Out-of-range temperature (-999 C)
        status, reason = validate_observation_bounds(ObservedVariable.TEMPERATURE_2M, -999.0, StandardUnit.CELSIUS)
        assert status == ValidationStatus.OUT_OF_RANGE
        assert "outside plausible range" in reason

        # Unit mismatch
        status, reason = validate_observation_bounds(ObservedVariable.TEMPERATURE_2M, 25.0, StandardUnit.PERCENT)
        assert status == ValidationStatus.INVALID
        assert "Unit mismatch" in reason

    def test_unit_conversions(self):
        # Wind speed km/h to m/s
        val, unit = convert_to_standard_unit(ObservedVariable.WIND_SPEED_10M, 36.0, "km/h")
        assert unit == StandardUnit.M_PER_S
        assert val == 10.0

        # Barometric pressure hPa to hPa, kPa to hPa
        val, unit = convert_to_standard_unit(ObservedVariable.BAROMETRIC_PRESSURE, 101.325, "kPa")
        assert unit == StandardUnit.HPA
        assert val == 1013.25

        # Temperature Fahrenheit to Celsius
        val, unit = convert_to_standard_unit(ObservedVariable.TEMPERATURE_2M, 77.0, "°F")
        assert unit == StandardUnit.CELSIUS
        assert val == 25.0


class TestJsonExamplesAgainstSchemas:
    """Validates every single JSON example file in packages/event-contracts/examples/ against schemas."""

    def test_all_examples_load_successfully(self):
        example_files = list(EXAMPLES_DIR.glob("*.json"))
        assert len(example_files) >= 10, f"Expected at least 10 JSON examples, found {len(example_files)}"

        for file_path in example_files:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Match and validate against corresponding Pydantic schema
            if "alert_id" in data and "investigation_steps_executed" in data:
                obj = AlertInvestigationResultEvent.model_validate(data)
            elif "alert_id" in data and "composite_stress_index" in data:
                obj = CropRiskCandidateAlertEvent.model_validate(data)
            elif "alert_id" in data and "operator_id" in data:
                obj = HumanDecisionEvent.model_validate(data)
            elif "health_flag" in data and "sensor_id" in data:
                obj = SensorHealthResultEvent.model_validate(data)
            elif "forecast_horizon_hours" in data:
                obj = WeatherContextEvent.model_validate(data)
            elif "dlq_id" in data:
                obj = DeadLetterRecordEvent.model_validate(data)
            elif "variable" in data and "value" in data:
                obj = AgriObservationEvent.model_validate(data)
            else:
                pytest.fail(f"Unrecognized example schema in {file_path.name}")

            assert obj is not None, f"Failed to validate {file_path.name}"


class TestSchemaEvolutionAndSerialization:
    """Tests schema evolution backwards compatibility and serialization round-trips."""

    def test_serialization_roundtrip(self):
        original = AgriObservationEvent(
            event_time=datetime(2026, 11, 1, 14, 43, 14, tzinfo=timezone.utc),
            field_id="KA_KOLAR_EXTERNAL_01",
            idempotency_key="roundtrip_test_01",
            source_provider="openSenseMap",
            sensor_id="probe_01",
            variable=ObservedVariable.TEMPERATURE_2M,
            value=25.39,
            unit=StandardUnit.CELSIUS,
            provenance=ProvenanceMetadata(
                provenance_class=ProvenanceClass.PHYSICAL_SENSOR,
                dataset_origin="openSenseMap",
                is_synthetic=False,
            ),
        )
        json_str = original.model_dump_json()
        restored = AgriObservationEvent.model_validate_json(json_str)
        assert restored.event_id == original.event_id
        assert restored.value == original.value
        assert restored.event_time == original.event_time
        assert restored.provenance.provenance_class == original.provenance.provenance_class

    def test_schema_evolution_backwards_compatibility(self):
        """Older payloads without newly introduced optional fields should parse cleanly."""
        legacy_payload = {
            "event_id": "99bdae86-be86-4add-a57b-97295ef92df1",
            "schema_version": "1.0.0",
            "event_time": "2026-11-01T12:00:00Z",
            "ingestion_time": "2026-11-01T12:00:01Z",
            "field_id": "KA_KOLAR_01",
            "idempotency_key": "legacy_key_001",
            "source_provider": "legacy_source",
            "variable": "temperature_2m",
            "value": 26.5,
            "unit": "celsius",
            "provenance": {
                "provenance_class": "physical_sensor",
                "dataset_origin": "Legacy-Feed",
                "is_synthetic": False
            }
        }
        event = AgriObservationEvent.model_validate(legacy_payload)
        assert event.sensor_id is None
        assert event.sensor_metadata is None
        assert event.quality_flags.is_imputed is False
        assert event.validation_status == ValidationStatus.UNKNOWN

    def test_location_out_of_bounds_rejected(self):
        with pytest.raises(ValidationError):
            LocationMetadata(latitude=95.0, longitude=77.0)  # lat > 90

        with pytest.raises(ValidationError):
            LocationMetadata(latitude=12.0, longitude=195.0)  # lon > 180

    def test_unsupported_unit_conversion_raises_error(self):
        with pytest.raises(ValueError, match="Unsupported unit"):
            convert_to_standard_unit(ObservedVariable.TEMPERATURE_2M, 100.0, "unknown_random_unit")

