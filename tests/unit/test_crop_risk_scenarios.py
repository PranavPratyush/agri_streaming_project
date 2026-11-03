"""Scenario tests for deterministic crop risk engine covering heat, dry-down, rainfall, faults, and abstentions."""

from datetime import datetime, timezone
import pytest

from agri_contracts.enums import CropRiskLevel, ProvenanceClass
from agri_risk_engine.risk import (
    DeterministicCropRiskEngine,
    FieldProfile,
    get_verified_kolar_ragi_profile,
)


class TestCropRiskScenarios:
    """End-to-end scenario evaluations asserting safety guardrails and risk triggers."""

    def setup_method(self) -> None:
        self.engine = DeterministicCropRiskEngine()
        self.profile = get_verified_kolar_ragi_profile(growth_stage="flowering_heading")
        self.now = datetime(2026, 11, 3, 12, 0, 0, tzinfo=timezone.utc)

    # -----------------------------------------------------------------------
    # Scenario 1: Acute Heat Stress During Flowering
    # -----------------------------------------------------------------------
    def test_heat_stress_scenario(self) -> None:
        """High temperature (35.5°C >= 34°C critical) triggers floret sterility risk alert."""
        alert = self.engine.evaluate_field_risk(
            field_profile=self.profile,
            event_time=self.now,
            temperature_c=35.5,
            relative_humidity_pct=35.0,
            soil_moisture_m3_m3=0.20,
            soil_moisture_provenance=ProvenanceClass.PHYSICAL_SENSOR,
        )
        assert alert.risk_type == "HEAT_STRESS"
        assert alert.risk_level in (CropRiskLevel.HIGH, CropRiskLevel.CRITICAL)
        assert alert.is_suppressed is False
        assert "floret sterility" in alert.evidence_summary.lower()
        assert "RISK_FLORET_HEAT_STERILITY" in alert.reason_codes

    # -----------------------------------------------------------------------
    # Scenario 2: Soil Moisture Dry-Down Deficit
    # -----------------------------------------------------------------------
    def test_soil_dry_down_deficit_scenario(self) -> None:
        """Soil moisture (0.13 m³/m³) depleting below RAW threshold (0.166) triggers moisture alert."""
        alert = self.engine.evaluate_field_risk(
            field_profile=self.profile,
            event_time=self.now,
            temperature_c=28.0,
            relative_humidity_pct=50.0,
            soil_moisture_m3_m3=0.130,  # Below 0.166 threshold
            soil_moisture_provenance=ProvenanceClass.PHYSICAL_SENSOR,
        )
        assert alert.risk_type == "SOIL_MOISTURE_DEFICIT"
        assert alert.risk_level in (CropRiskLevel.HIGH, CropRiskLevel.CRITICAL)
        assert alert.is_suppressed is False
        assert alert.soil_depletion_fraction is not None
        assert alert.soil_depletion_fraction > 0.45
        assert "RISK_ROOT_ZONE_MOISTURE_DEFICIT" in alert.reason_codes

    # -----------------------------------------------------------------------
    # Scenario 3: Rainfall & Moisture Recovery
    # -----------------------------------------------------------------------
    def test_rainfall_recovery_scenario(self) -> None:
        """Recent rainfall and moisture replenishment above RAW threshold returns optimal conditions."""
        alert = self.engine.evaluate_field_risk(
            field_profile=self.profile,
            event_time=self.now,
            temperature_c=25.0,
            relative_humidity_pct=75.0,
            soil_moisture_m3_m3=0.210,  # Replenished near FC (0.22)
            soil_moisture_provenance=ProvenanceClass.PHYSICAL_SENSOR,
            precipitation_mm=25.0,
        )
        assert alert.risk_type == "NO_ACUTE_STRESS"
        assert alert.risk_level == CropRiskLevel.NONE
        assert alert.is_suppressed is True  # Suppressed from disturbing farmer
        assert "optimal" in alert.evidence_summary.lower()

    # -----------------------------------------------------------------------
    # Scenario 4: Conflicting Signals (Rain vs Drought Drop)
    # -----------------------------------------------------------------------
    def test_conflicting_signals_abstention_scenario(self) -> None:
        """High precipitation (15mm) coupled with dropping soil moisture (<0.12) forces abstention."""
        alert = self.engine.evaluate_field_risk(
            field_profile=self.profile,
            event_time=self.now,
            temperature_c=26.0,
            relative_humidity_pct=80.0,
            soil_moisture_m3_m3=0.105,  # Low SM contradicts 15mm rain!
            precipitation_mm=15.0,
        )
        assert alert.risk_type == "ABSTENTION_CONFLICTING_SIGNALS"
        assert alert.is_suppressed is True
        assert "contradicts" in alert.evidence_summary.lower()
        assert "ABSTAIN_CONFLICTING_SIGNALS" in alert.reason_codes
        assert alert.uncertainty_score >= 0.80

    # -----------------------------------------------------------------------
    # Scenario 5: Faulty Sensor Telemetry
    # -----------------------------------------------------------------------
    def test_faulty_sensor_suppression_scenario(self) -> None:
        """Underlying sensor diagnosed as FAULTY must suppress advisory recommendations."""
        alert = self.engine.evaluate_field_risk(
            field_profile=self.profile,
            event_time=self.now,
            temperature_c=36.0,
            relative_humidity_pct=30.0,
            soil_moisture_m3_m3=0.11,
            sensor_health_status="FAULTY",
            is_sensor_suppressed=True,
        )
        assert alert.risk_type == "SUPPRESSED_UNRELIABLE_SENSOR_DATA"
        assert alert.is_suppressed is True
        assert "SUPPRESSED" in alert.suppression_reason
        assert "SUPPRESSED_SENSOR_FAULT" in alert.reason_codes
        assert alert.uncertainty_score == 1.0

    # -----------------------------------------------------------------------
    # Scenario 6: Stale Telemetry
    # -----------------------------------------------------------------------
    def test_stale_telemetry_suppression_scenario(self) -> None:
        """Telemetry flagged as STALE must suppress advisory recommendations."""
        alert = self.engine.evaluate_field_risk(
            field_profile=self.profile,
            event_time=self.now,
            temperature_c=35.0,
            relative_humidity_pct=40.0,
            sensor_health_status="STALE",
            is_sensor_suppressed=True,
        )
        assert alert.risk_type == "SUPPRESSED_UNRELIABLE_SENSOR_DATA"
        assert alert.is_suppressed is True
        assert alert.uncertainty_score == 1.0

    # -----------------------------------------------------------------------
    # Scenario 7: Missing or Incomplete Field Profile
    # -----------------------------------------------------------------------
    def test_missing_field_profile_abstention_scenario(self) -> None:
        """When field profile is None, engine must abstain rather than fabricating defaults."""
        alert = self.engine.evaluate_field_risk(
            field_profile=None,
            event_time=self.now,
            temperature_c=32.0,
            relative_humidity_pct=50.0,
        )
        assert alert.risk_type == "ABSTENTION_MISSING_CROP_PROFILE"
        assert alert.is_suppressed is True
        assert alert.uncertainty_score == 1.0
        assert "ABSTAIN_MISSING_PROFILE" in alert.reason_codes

    def test_incomplete_field_profile_abstention_scenario(self) -> None:
        """When profile lacks growth stage, engine abstains."""
        sparse_profile = FieldProfile(
            field_id="field_kolar_sparse",
            crop_name="Finger Millet (Ragi)",
            growth_stage=None,  # Missing!
            soil_profile=None,  # Missing!
            stage_parameters=None,
        )
        alert = self.engine.evaluate_field_risk(
            field_profile=sparse_profile,
            event_time=self.now,
            temperature_c=32.0,
            relative_humidity_pct=50.0,
        )
        assert alert.risk_type == "ABSTENTION_INCOMPLETE_CROP_PROFILE"
        assert alert.is_suppressed is True
        assert "ABSTAIN_INCOMPLETE_PROFILE" in alert.reason_codes

    # -----------------------------------------------------------------------
    # Scenario 8: Provenance Awareness (Physical vs Modelled Soil Moisture)
    # -----------------------------------------------------------------------
    def test_modelled_reanalysis_soil_moisture_provenance_tracking(self) -> None:
        """Modelled reanalysis soil moisture increases uncertainty and preserves provenance lineage."""
        alert_modelled = self.engine.evaluate_field_risk(
            field_profile=self.profile,
            event_time=self.now,
            temperature_c=28.0,
            relative_humidity_pct=50.0,
            soil_moisture_m3_m3=0.14,
            soil_moisture_provenance=ProvenanceClass.MODELLED_REANALYSIS,
        )
        assert alert_modelled.input_provenance["soil_moisture"] == "modelled_reanalysis"
        assert alert_modelled.uncertainty_score > 0.30  # Higher uncertainty for modelled data

