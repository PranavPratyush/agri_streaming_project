"""Unit tests for deterministic sensor health and data quality forensic detectors."""

from datetime import datetime, timedelta, timezone
import pytest
import uuid

from agri_contracts.enums import (
    HealthState,
    ObservedVariable,
    ProvenanceClass,
    SensorHealthFlag,
    StandardUnit,
)
from agri_risk_engine.health import (
    DeterministicSensorHealthEvaluator,
    DropoutDetector,
    ForensicReasonCode,
    HealthEvidence,
    HealthThresholdsConfig,
    RangeAndSpikeDetector,
    SensorDriftDetector,
    SourceVsSensorOutageDetector,
    StalenessAndCadenceDetector,
    StuckValueDetector,
    is_measurement_usable_for_advisory,
)


# ===========================================================================
# 1. Staleness, Clock Skew, Reversal, & Cadence Tests
# ===========================================================================

class TestStalenessAndCadenceDetector:
    """Verify temporal freshness, out-of-order timestamps, and clock skew."""

    def setup_method(self) -> None:
        self.detector = StalenessAndCadenceDetector()
        self.now = datetime(2026, 11, 3, 10, 0, 0, tzinfo=timezone.utc)

    def test_fresh_observation_passes(self) -> None:
        event_time = self.now - timedelta(seconds=60)
        state, flag, ev = self.detector.evaluate(event_time=event_time, now=self.now)
        assert state == HealthState.HEALTHY
        assert flag == SensorHealthFlag.HEALTHY
        assert ev.reason_code == ForensicReasonCode.OK_HEALTHY

    def test_excessive_age_is_stale(self) -> None:
        # Age = 2 hours (> 1 hour max acceptable age)
        event_time = self.now - timedelta(hours=2)
        state, flag, ev = self.detector.evaluate(event_time=event_time, now=self.now)
        assert state == HealthState.STALE
        assert ev.reason_code == ForensicReasonCode.ERR_STALE_OBSERVATION

    def test_clock_skew_future_timestamp(self) -> None:
        # 5 minutes in the future (> 120s tolerance)
        future_time = self.now + timedelta(minutes=5)
        state, flag, ev = self.detector.evaluate(event_time=future_time, now=self.now)
        assert state == HealthState.FAULTY
        assert ev.reason_code == ForensicReasonCode.ERR_CLOCK_SKEW

    def test_timestamp_reversal(self) -> None:
        prev_time = self.now - timedelta(minutes=5)
        curr_time = self.now - timedelta(minutes=10)  # Reversal: curr is older than prev
        state, flag, ev = self.detector.evaluate(
            event_time=curr_time, previous_event_time=prev_time, now=self.now
        )
        assert state == HealthState.SUSPECT
        assert ev.reason_code == ForensicReasonCode.ERR_TIMESTAMP_REVERSAL

    def test_duplicate_event_id(self) -> None:
        seen = {"event-123", "event-456"}
        state, flag, ev = self.detector.evaluate(
            event_time=self.now, now=self.now, seen_event_ids=seen, event_id="event-123"
        )
        assert state == HealthState.FAULTY
        assert ev.reason_code == ForensicReasonCode.ERR_DUPLICATE_EVENT_ID

    def test_irregular_cadence_gap(self) -> None:
        # Cadence is 300s, gap is 1200s (4x expected cadence)
        prev_time = self.now - timedelta(seconds=1200)
        state, flag, ev = self.detector.evaluate(
            event_time=self.now,
            previous_event_time=prev_time,
            expected_cadence_sec=300.0,
            now=self.now,
        )
        assert state == HealthState.SUSPECT
        assert ev.reason_code == ForensicReasonCode.ERR_IRREGULAR_CADENCE


# ===========================================================================
# 2. Range & Abrupt Spike Tests
# ===========================================================================

class TestRangeAndSpikeDetector:
    """Verify physical terrestrial plausibility bounds and abrupt rate-of-change spikes."""

    def setup_method(self) -> None:
        self.detector = RangeAndSpikeDetector()

    def test_valid_reading_passes(self) -> None:
        state, flag, ev = self.detector.evaluate(
            variable=ObservedVariable.TEMPERATURE_2M,
            value=28.5,
            unit=StandardUnit.CELSIUS,
        )
        assert state == HealthState.HEALTHY
        assert flag == SensorHealthFlag.HEALTHY

    def test_out_of_bounds_temperature(self) -> None:
        state, flag, ev = self.detector.evaluate(
            variable=ObservedVariable.TEMPERATURE_2M,
            value=75.0,  # exceeds 55°C limit
            unit=StandardUnit.CELSIUS,
        )
        assert state == HealthState.FAULTY
        assert flag == SensorHealthFlag.OUT_OF_BOUNDS
        assert ev.reason_code == ForensicReasonCode.ERR_IMPLAUSIBLE_RANGE

    def test_non_finite_value(self) -> None:
        state, flag, ev = self.detector.evaluate(
            variable=ObservedVariable.SOIL_MOISTURE_0_TO_7CM,
            value=float("nan"),
            unit=StandardUnit.M3_PER_M3,
        )
        assert state == HealthState.FAULTY
        assert flag == SensorHealthFlag.OUT_OF_BOUNDS

    def test_unit_mismatch(self) -> None:
        state, flag, ev = self.detector.evaluate(
            variable=ObservedVariable.TEMPERATURE_2M,
            value=30.0,
            unit="fahrenheit",  # Expected CELSIUS
        )
        assert state == HealthState.FAULTY
        assert flag == SensorHealthFlag.OUT_OF_BOUNDS

    def test_abrupt_temperature_spike(self) -> None:
        # Jump of 15°C in 60 seconds (15°C/min exceeds 5°C/min limit)
        state, flag, ev = self.detector.evaluate(
            variable=ObservedVariable.TEMPERATURE_2M,
            value=45.0,
            unit=StandardUnit.CELSIUS,
            previous_value=30.0,
            delta_seconds=60.0,
        )
        assert state == HealthState.FAULTY
        assert flag == SensorHealthFlag.SPIKE_ANOMALY
        assert ev.reason_code == ForensicReasonCode.ERR_ABRUPT_SPIKE

    def test_rapid_soil_wetting_corroborated_by_rain_is_healthy(self) -> None:
        # Jump of 0.15 m³/m³ in 60s, but corroborated by 12mm rain
        state, flag, ev = self.detector.evaluate(
            variable=ObservedVariable.SOIL_MOISTURE_0_TO_7CM,
            value=0.35,
            unit=StandardUnit.M3_PER_M3,
            previous_value=0.20,
            delta_seconds=60.0,
            corroborating_rain_mm=12.0,
        )
        assert state == HealthState.HEALTHY
        assert flag == SensorHealthFlag.HEALTHY
        assert ev.reason_code == ForensicReasonCode.OK_HEALTHY


# ===========================================================================
# 3. Dropout & Hardware Sentinel Tests
# ===========================================================================

class TestDropoutDetector:
    """Verify detection of ADC saturation, disconnect sentinels, and abnormal drops."""

    def setup_method(self) -> None:
        self.detector = DropoutDetector()

    def test_hardware_sentinel_match(self) -> None:
        for sentinel in [-999.0, 1023.0, 4095.0]:
            state, flag, ev = self.detector.evaluate(
                variable=ObservedVariable.TEMPERATURE_2M, value=sentinel
            )
            assert state == HealthState.FAULTY
            assert flag == SensorHealthFlag.DROPOUT
            assert ev.reason_code == ForensicReasonCode.ERR_MISSING_DROPOUT

    def test_barometric_pressure_zero_is_dropout(self) -> None:
        state, flag, ev = self.detector.evaluate(
            variable=ObservedVariable.BAROMETRIC_PRESSURE, value=0.0
        )
        assert state == HealthState.FAULTY
        assert flag == SensorHealthFlag.DROPOUT

    def test_abrupt_relative_humidity_drop_to_zero(self) -> None:
        # Dropped from 85% to 0.0%
        state, flag, ev = self.detector.evaluate(
            variable=ObservedVariable.RELATIVE_HUMIDITY_2M,
            value=0.0,
            previous_value=85.0,
        )
        assert state == HealthState.FAULTY
        assert flag == SensorHealthFlag.DROPOUT


# ===========================================================================
# 4. Stuck Value & Natural Flatline Tests (Handover Risk Focus)
# ===========================================================================

class TestStuckValueDetector:
    """Verify stuck value detection and mandatory natural flatline differentiation."""

    def setup_method(self) -> None:
        self.detector = StuckValueDetector()

    def test_precipitation_zero_flatline_is_healthy_without_corroboration(self) -> None:
        """CRITICAL: Natural zero-rain sequences (Phase 1 handover risk) must NOT be labelled faulty."""
        zero_history = [0.0] * 36  # 36 hours of 0.0 mm rainfall
        state, flag, ev = self.detector.evaluate(
            variable=ObservedVariable.PRECIPITATION,
            history_values=zero_history,
            corroborating_rain_detected=False,
        )
        assert state == HealthState.HEALTHY
        assert flag == SensorHealthFlag.HEALTHY
        assert ev.reason_code == ForensicReasonCode.OK_CORROBORATED_NATURAL_FLATLINE

    def test_precipitation_zero_with_confirmed_rain_is_faulty(self) -> None:
        """When adjacent stations confirm heavy rain, a 0.0 reading is a stuck rain gauge."""
        zero_history = [0.0] * 24
        state, flag, ev = self.detector.evaluate(
            variable=ObservedVariable.PRECIPITATION,
            history_values=zero_history,
            corroborating_rain_detected=True,  # Neighbors confirm rain!
        )
        assert state == HealthState.FAULTY
        assert flag == SensorHealthFlag.STUCK_VALUE
        assert ev.reason_code == ForensicReasonCode.ERR_STUCK_VALUE

    def test_modelled_reanalysis_flatline_is_bypassed(self) -> None:
        """CRITICAL: Gridded weather model flatlines must NEVER be marked as a hardware stuck sensor."""
        flat_history = [0.15] * 24
        state, flag, ev = self.detector.evaluate(
            variable=ObservedVariable.SOIL_MOISTURE_0_TO_7CM,
            history_values=flat_history,
            provenance_class=ProvenanceClass.MODELLED_REANALYSIS,
        )
        assert state == HealthState.HEALTHY
        assert ev.reason_code == ForensicReasonCode.OK_MODELLED_REANALYSIS_BYPASS

    def test_soil_moisture_residual_dry_plateau_is_healthy(self) -> None:
        """Karnataka red sandy loam residual water content theta_r (0.08 - 0.12) naturally flatlines during drought."""
        residual_dry_history = [0.095] * 24
        state, flag, ev = self.detector.evaluate(
            variable=ObservedVariable.SOIL_MOISTURE_0_TO_7CM,
            history_values=residual_dry_history,
            corroborating_rain_detected=False,
        )
        assert state == HealthState.HEALTHY
        assert flag == SensorHealthFlag.HEALTHY
        assert ev.reason_code == ForensicReasonCode.OK_CORROBORATED_NATURAL_FLATLINE

    def test_dynamic_temperature_stuck_value_is_faulty(self) -> None:
        """Ambient air temperature must exhibit diurnal variation over daytime hours; constant value is faulty."""
        stuck_temp = [26.4] * 20  # Constant to 0.000 variance over 20 readings
        state, flag, ev = self.detector.evaluate(
            variable=ObservedVariable.TEMPERATURE_2M,
            history_values=stuck_temp,
            corroborating_neighbor_variance=12.5,  # Neighbor exhibits normal diurnal swing
        )
        assert state == HealthState.FAULTY
        assert flag == SensorHealthFlag.STUCK_VALUE
        assert ev.reason_code == ForensicReasonCode.ERR_STUCK_VALUE

    def test_insufficient_history_returns_unknown(self) -> None:
        """Fewer than 12 samples must return UNKNOWN, not a premature FAULTY."""
        short_history = [25.0, 25.0, 25.0]
        state, flag, ev = self.detector.evaluate(
            variable=ObservedVariable.TEMPERATURE_2M,
            history_values=short_history,
        )
        assert state == HealthState.UNKNOWN
        assert ev.reason_code == ForensicReasonCode.UNKNOWN_INSUFFICIENT_HISTORY


# ===========================================================================
# 5. Drift & Outage Scope Tests
# ===========================================================================

class TestDriftAndOutageDetectors:
    """Verify sensor drift and source vs sensor outage differentiation."""

    def test_sensor_drift_above_three_sigma(self) -> None:
        detector = SensorDriftDetector()
        # Reference mean = 24.0, std = 1.0; Sensor reads 28.5 (Z = 4.5 sigma)
        state, flag, ev = detector.evaluate(
            current_value=28.5,
            reference_mean=24.0,
            reference_std=1.0,
            sample_count=30,
        )
        assert state == HealthState.FAULTY
        assert flag == SensorHealthFlag.DRIFT_ANOMALY
        assert ev.reason_code == ForensicReasonCode.ERR_SENSOR_DRIFT

    def test_insufficient_samples_for_drift_returns_unknown(self) -> None:
        detector = SensorDriftDetector()
        state, flag, ev = detector.evaluate(
            current_value=28.5,
            reference_mean=24.0,
            reference_std=1.0,
            sample_count=10,  # < 24 samples
        )
        assert state == HealthState.UNKNOWN
        assert ev.reason_code == ForensicReasonCode.UNKNOWN_INSUFFICIENT_HISTORY

    def test_source_outage_vs_sensor_outage(self) -> None:
        outage_det = SourceVsSensorOutageDetector()

        # All 5 sensors are missing -> Source outage (gateway / network loss)
        st_source, code_source, desc_source = outage_det.evaluate(
            target_sensor_id="probe_temp",
            active_sensor_ids_in_provider=[],
            all_expected_sensor_ids_in_provider=["probe_temp", "probe_rh", "probe_sm", "probe_press", "probe_rain"],
        )
        assert st_source == HealthState.FAULTY
        assert code_source == ForensicReasonCode.ERR_SOURCE_OUTAGE

        # 4 sensors active, only soil moisture probe missing -> Sensor outage (probe fault)
        st_sensor, code_sensor, desc_sensor = outage_det.evaluate(
            target_sensor_id="probe_sm",
            active_sensor_ids_in_provider=["probe_temp", "probe_rh", "probe_press", "probe_rain"],
            all_expected_sensor_ids_in_provider=["probe_temp", "probe_rh", "probe_sm", "probe_press", "probe_rain"],
        )
        assert st_sensor == HealthState.FAULTY
        assert code_sensor == ForensicReasonCode.ERR_SENSOR_OUTAGE


# ===========================================================================
# 6. Advisory Gating Safety Rule Tests
# ===========================================================================

class TestAdvisoryGating:
    """Verify safety rule: faulty/stale measurements must block crop recommendations."""

    def test_advisory_gating_truth_table(self) -> None:
        # FAULTY blocks advisory
        assert is_measurement_usable_for_advisory(HealthState.FAULTY) is False

        # STALE blocks advisory
        assert is_measurement_usable_for_advisory(HealthState.STALE) is False

        # Suppressed blocks advisory even if state is HEALTHY
        assert is_measurement_usable_for_advisory(HealthState.HEALTHY, is_suppressed=True) is False

        # HEALTHY is usable
        assert is_measurement_usable_for_advisory(HealthState.HEALTHY) is True

        # UNKNOWN is usable by default (with non-fault flag)
        assert is_measurement_usable_for_advisory(HealthState.UNKNOWN) is True

        # SUSPECT blocks by default unless explicitly allowed
        assert is_measurement_usable_for_advisory(HealthState.SUSPECT, allow_suspect=False) is False
        assert is_measurement_usable_for_advisory(HealthState.SUSPECT, allow_suspect=True) is True

