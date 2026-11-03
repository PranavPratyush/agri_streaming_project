"""Integration test for CropRiskKafkaService streaming risk evaluation and Kafka alert emission."""

from datetime import datetime, timezone
import pytest

from agri_contracts.enums import CropRiskLevel, ProvenanceClass
from agri_risk_engine.risk.kafka_service import CropRiskKafkaService


class TestCropRiskKafkaServiceIntegration:
    """Verify streaming field evaluation, alert emission, and suppression tracking."""

    def setup_method(self) -> None:
        self.service = CropRiskKafkaService()
        self.now = datetime(2026, 11, 3, 14, 0, 0, tzinfo=timezone.utc)

    def test_flowering_heat_alert_emission(self) -> None:
        """Floret heat stress emits a high-priority candidate alert to candidate-alerts topic."""
        alert = self.service.process_field_telemetry(
            field_id="field_kolar_ragi_01",
            event_time=self.now,
            temperature_c=36.2,
            relative_humidity_pct=40.0,
            soil_moisture_m3_m3=0.18,
        )
        assert alert.risk_type == "HEAT_STRESS"
        assert alert.risk_level in (CropRiskLevel.HIGH, CropRiskLevel.CRITICAL)
        assert alert.is_suppressed is False
        assert alert.field_id == "field_kolar_ragi_01"
        assert alert.alert_id is not None
        assert alert.rule_version == "1.0.0"

    def test_faulty_sensor_blocks_candidate_alert(self) -> None:
        """Unreliable sensor telemetry suppresses candidate alert emission."""
        alert = self.service.process_field_telemetry(
            field_id="field_kolar_ragi_01",
            event_time=self.now,
            temperature_c=38.0,
            relative_humidity_pct=30.0,
            sensor_health_status="FAULTY",
            is_sensor_suppressed=True,
        )
        assert alert.is_suppressed is True
        assert "SUPPRESSED" in alert.suppression_reason
        assert alert.uncertainty_score == 1.0

    def test_unknown_field_triggers_profile_abstention(self) -> None:
        """Unregistered field without crop profile triggers explicit abstention."""
        alert = self.service.process_field_telemetry(
            field_id="field_unregistered_99",
            event_time=self.now,
            temperature_c=32.0,
            relative_humidity_pct=50.0,
        )
        assert alert.is_suppressed is True
        assert "ABSTAIN_MISSING_PROFILE" in alert.reason_codes

