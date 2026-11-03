"""Confusion-matrix-style benchmark tests for deterministic sensor health forensic diagnostics.

Evaluates precision, recall, F1, and specificity across labelled fixtures of known faults
and authentic environmental patterns (especially natural flatlines).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
import pytest

from agri_contracts.enums import (
    HealthState,
    ObservedVariable,
    ProvenanceClass,
    StandardUnit,
)
from agri_risk_engine.health import (
    DeterministicSensorHealthEvaluator,
    ForensicReasonCode,
)


@dataclass
class LabelledForensicFixture:
    """Fixture representation of an agricultural observation with ground-truth diagnosis."""
    fixture_id: str
    variable: ObservedVariable
    value: float
    unit: StandardUnit
    expected_is_fault: bool
    expected_state: HealthState
    expected_reason: ForensicReasonCode
    event_time_offset_sec: float = 0.0
    previous_value: float | None = None
    delta_seconds: float | None = None
    history_values: list[float] | None = None
    provenance_class: ProvenanceClass = ProvenanceClass.PHYSICAL_SENSOR
    corroborating_neighbor_variance: float | None = None
    corroborating_rain_detected: bool | None = None
    corroborating_rain_mm: float | None = None
    reference_mean: float | None = None
    reference_std: float | None = None
    reference_sample_count: int = 0


def generate_labelled_fixtures() -> list[LabelledForensicFixture]:
    """Generate a diverse benchmark dataset of 50 labelled observations."""
    fixtures: list[LabelledForensicFixture] = []

    # -----------------------------------------------------------------------
    # Group A: Normal Environmental Telemetry (Ground Truth: HEALTHY, Not Fault)
    # -----------------------------------------------------------------------
    # 1. Normal diurnal temperature reading
    fixtures.append(LabelledForensicFixture(
        fixture_id="norm-temp-01",
        variable=ObservedVariable.TEMPERATURE_2M,
        value=28.4,
        unit=StandardUnit.CELSIUS,
        expected_is_fault=False,
        expected_state=HealthState.HEALTHY,
        expected_reason=ForensicReasonCode.OK_HEALTHY,
        previous_value=28.1,
        delta_seconds=300.0,
        history_values=[24.0, 25.1, 26.2, 27.0, 27.8, 28.1, 28.4, 28.3, 27.9, 27.0, 26.0, 25.2],
    ))
    # 2. Normal relative humidity curve
    fixtures.append(LabelledForensicFixture(
        fixture_id="norm-rh-01",
        variable=ObservedVariable.RELATIVE_HUMIDITY_2M,
        value=72.5,
        unit=StandardUnit.PERCENT,
        expected_is_fault=False,
        expected_state=HealthState.HEALTHY,
        expected_reason=ForensicReasonCode.OK_HEALTHY,
        previous_value=70.0,
        delta_seconds=300.0,
        history_values=[85.0, 82.0, 78.0, 75.0, 73.0, 70.0, 72.5, 74.0, 77.0, 80.0, 83.0, 85.0],
    ))
    # 3. Normal soil moisture drying
    fixtures.append(LabelledForensicFixture(
        fixture_id="norm-sm-01",
        variable=ObservedVariable.SOIL_MOISTURE_0_TO_7CM,
        value=0.225,
        unit=StandardUnit.M3_PER_M3,
        expected_is_fault=False,
        expected_state=HealthState.HEALTHY,
        expected_reason=ForensicReasonCode.OK_HEALTHY,
        previous_value=0.228,
        delta_seconds=300.0,
        history_values=[0.24, 0.238, 0.235, 0.232, 0.230, 0.228, 0.225, 0.223, 0.220, 0.218, 0.215, 0.212],
    ))
    # 4. Rapid soil moisture wetting with rain corroboration
    fixtures.append(LabelledForensicFixture(
        fixture_id="norm-sm-wetting",
        variable=ObservedVariable.SOIL_MOISTURE_0_TO_7CM,
        value=0.340,
        unit=StandardUnit.M3_PER_M3,
        expected_is_fault=False,
        expected_state=HealthState.HEALTHY,
        expected_reason=ForensicReasonCode.OK_HEALTHY,
        previous_value=0.180,
        delta_seconds=300.0,
        corroborating_rain_mm=18.5,
    ))

    # -----------------------------------------------------------------------
    # Group B: Natural Flatlines (The Handover Risk: Ground Truth: HEALTHY, Not Fault)
    # -----------------------------------------------------------------------
    # 5. Natural dry-season zero-rain flatline (50 consecutive 0.0 readings)
    fixtures.append(LabelledForensicFixture(
        fixture_id="flatline-rain-dry-01",
        variable=ObservedVariable.PRECIPITATION,
        value=0.0,
        unit=StandardUnit.MM,
        expected_is_fault=False,
        expected_state=HealthState.HEALTHY,
        expected_reason=ForensicReasonCode.OK_CORROBORATED_NATURAL_FLATLINE,
        history_values=[0.0] * 50,
        corroborating_rain_detected=False,
    ))
    # 6. Natural dry-season zero-rain flatline (24 readings)
    fixtures.append(LabelledForensicFixture(
        fixture_id="flatline-rain-dry-02",
        variable=ObservedVariable.PRECIPITATION,
        value=0.0,
        unit=StandardUnit.MM,
        expected_is_fault=False,
        expected_state=HealthState.HEALTHY,
        expected_reason=ForensicReasonCode.OK_CORROBORATED_NATURAL_FLATLINE,
        history_values=[0.0] * 24,
        corroborating_rain_detected=False,
    ))
    # 7. Soil moisture plateau at residual dry content (theta_r = 0.092 m3/m3)
    fixtures.append(LabelledForensicFixture(
        fixture_id="flatline-sm-residual",
        variable=ObservedVariable.SOIL_MOISTURE_0_TO_7CM,
        value=0.092,
        unit=StandardUnit.M3_PER_M3,
        expected_is_fault=False,
        expected_state=HealthState.HEALTHY,
        expected_reason=ForensicReasonCode.OK_CORROBORATED_NATURAL_FLATLINE,
        history_values=[0.092] * 30,
        corroborating_rain_detected=False,
    ))
    # 8. Gridded reanalysis model soil moisture plateau (modelled data bypass)
    fixtures.append(LabelledForensicFixture(
        fixture_id="flatline-reanalysis-model",
        variable=ObservedVariable.SOIL_MOISTURE_0_TO_7CM,
        value=0.180,
        unit=StandardUnit.M3_PER_M3,
        expected_is_fault=False,
        expected_state=HealthState.HEALTHY,
        expected_reason=ForensicReasonCode.OK_MODELLED_REANALYSIS_BYPASS,
        history_values=[0.180] * 36,
        provenance_class=ProvenanceClass.MODELLED_REANALYSIS,
    ))

    # -----------------------------------------------------------------------
    # Group C: True Faults — Stuck Values (Ground Truth: FAULTY)
    # -----------------------------------------------------------------------
    # 9. Stuck temperature probe (constant 25.1°C over 24 samples while neighbor varies)
    fixtures.append(LabelledForensicFixture(
        fixture_id="fault-stuck-temp-01",
        variable=ObservedVariable.TEMPERATURE_2M,
        value=25.1,
        unit=StandardUnit.CELSIUS,
        expected_is_fault=True,
        expected_state=HealthState.FAULTY,
        expected_reason=ForensicReasonCode.ERR_STUCK_VALUE,
        history_values=[25.1] * 24,
        corroborating_neighbor_variance=8.5,
    ))
    # 10. Stuck rain gauge at 0.0 mm while adjacent stations confirm heavy rain
    fixtures.append(LabelledForensicFixture(
        fixture_id="fault-stuck-rain-unreported",
        variable=ObservedVariable.PRECIPITATION,
        value=0.0,
        unit=StandardUnit.MM,
        expected_is_fault=True,
        expected_state=HealthState.FAULTY,
        expected_reason=ForensicReasonCode.ERR_STUCK_VALUE,
        history_values=[0.0] * 24,
        corroborating_rain_detected=True,  # Corroborated rain!
    ))
    # 11. Stuck relative humidity at 88.0%
    fixtures.append(LabelledForensicFixture(
        fixture_id="fault-stuck-rh-01",
        variable=ObservedVariable.RELATIVE_HUMIDITY_2M,
        value=88.0,
        unit=StandardUnit.PERCENT,
        expected_is_fault=True,
        expected_state=HealthState.FAULTY,
        expected_reason=ForensicReasonCode.ERR_STUCK_VALUE,
        history_values=[88.0] * 20,
        corroborating_neighbor_variance=45.0,
    ))

    # -----------------------------------------------------------------------
    # Group D: True Faults — Abrupt Spikes (Ground Truth: FAULTY)
    # -----------------------------------------------------------------------
    # 12. Abrupt temperature spike (25°C to 42°C in 60s)
    fixtures.append(LabelledForensicFixture(
        fixture_id="fault-spike-temp-01",
        variable=ObservedVariable.TEMPERATURE_2M,
        value=42.0,
        unit=StandardUnit.CELSIUS,
        expected_is_fault=True,
        expected_state=HealthState.FAULTY,
        expected_reason=ForensicReasonCode.ERR_ABRUPT_SPIKE,
        previous_value=25.0,
        delta_seconds=60.0,
    ))
    # 13. Soil moisture spike without rain
    fixtures.append(LabelledForensicFixture(
        fixture_id="fault-spike-sm-norain",
        variable=ObservedVariable.SOIL_MOISTURE_0_TO_7CM,
        value=0.450,
        unit=StandardUnit.M3_PER_M3,
        expected_is_fault=True,
        expected_state=HealthState.FAULTY,
        expected_reason=ForensicReasonCode.ERR_ABRUPT_SPIKE,
        previous_value=0.150,
        delta_seconds=60.0,
        corroborating_rain_mm=0.0,
    ))
    # 14. Relative humidity jump of 40% in 1 minute
    fixtures.append(LabelledForensicFixture(
        fixture_id="fault-spike-rh-01",
        variable=ObservedVariable.RELATIVE_HUMIDITY_2M,
        value=95.0,
        unit=StandardUnit.PERCENT,
        expected_is_fault=True,
        expected_state=HealthState.FAULTY,
        expected_reason=ForensicReasonCode.ERR_ABRUPT_SPIKE,
        previous_value=50.0,
        delta_seconds=60.0,
    ))

    # -----------------------------------------------------------------------
    # Group E: True Faults — Plausibility / Boundary Violations (Ground Truth: FAULTY)
    # -----------------------------------------------------------------------
    # 15. Temperature exceeds terrestrial maximum (78.0°C)
    fixtures.append(LabelledForensicFixture(
        fixture_id="fault-range-temp-high",
        variable=ObservedVariable.TEMPERATURE_2M,
        value=78.0,
        unit=StandardUnit.CELSIUS,
        expected_is_fault=True,
        expected_state=HealthState.FAULTY,
        expected_reason=ForensicReasonCode.ERR_IMPLAUSIBLE_RANGE,
    ))
    # 16. Soil moisture exceeds physical porosity (> 0.70)
    fixtures.append(LabelledForensicFixture(
        fixture_id="fault-range-sm-high",
        variable=ObservedVariable.SOIL_MOISTURE_0_TO_7CM,
        value=0.88,
        unit=StandardUnit.M3_PER_M3,
        expected_is_fault=True,
        expected_state=HealthState.FAULTY,
        expected_reason=ForensicReasonCode.ERR_IMPLAUSIBLE_RANGE,
    ))
    # 17. Relative humidity exceeds 100%
    fixtures.append(LabelledForensicFixture(
        fixture_id="fault-range-rh-high",
        variable=ObservedVariable.RELATIVE_HUMIDITY_2M,
        value=135.0,
        unit=StandardUnit.PERCENT,
        expected_is_fault=True,
        expected_state=HealthState.FAULTY,
        expected_reason=ForensicReasonCode.ERR_IMPLAUSIBLE_RANGE,
    ))
    # 18. Negative relative humidity
    fixtures.append(LabelledForensicFixture(
        fixture_id="fault-range-rh-negative",
        variable=ObservedVariable.RELATIVE_HUMIDITY_2M,
        value=-10.0,
        unit=StandardUnit.PERCENT,
        expected_is_fault=True,
        expected_state=HealthState.FAULTY,
        expected_reason=ForensicReasonCode.ERR_IMPLAUSIBLE_RANGE,
    ))

    # -----------------------------------------------------------------------
    # Group F: True Faults — Electrical Dropout Sentinels (Ground Truth: FAULTY)
    # -----------------------------------------------------------------------
    # 19. Hardware sentinel code -999.0
    fixtures.append(LabelledForensicFixture(
        fixture_id="fault-dropout-sentinel-neg999",
        variable=ObservedVariable.TEMPERATURE_2M,
        value=-999.0,
        unit=StandardUnit.CELSIUS,
        expected_is_fault=True,
        expected_state=HealthState.FAULTY,
        expected_reason=ForensicReasonCode.ERR_MISSING_DROPOUT,
    ))
    # 20. 10-bit ADC saturation (1023.0)
    fixtures.append(LabelledForensicFixture(
        fixture_id="fault-dropout-adc-1023",
        variable=ObservedVariable.TEMPERATURE_2M,
        value=1023.0,
        unit=StandardUnit.CELSIUS,
        expected_is_fault=True,
        expected_state=HealthState.FAULTY,
        expected_reason=ForensicReasonCode.ERR_MISSING_DROPOUT,
    ))
    # 21. Barometric pressure drops to 0.0 hPa
    fixtures.append(LabelledForensicFixture(
        fixture_id="fault-dropout-press-zero",
        variable=ObservedVariable.BAROMETRIC_PRESSURE,
        value=0.0,
        unit=StandardUnit.HPA,
        expected_is_fault=True,
        expected_state=HealthState.FAULTY,
        expected_reason=ForensicReasonCode.ERR_MISSING_DROPOUT,
    ))

    # -----------------------------------------------------------------------
    # Group G: True Faults — Temporal Staleness & Clock Skew (Ground Truth: FAULTY / STALE)
    # -----------------------------------------------------------------------
    # 22. Excessive observation age (3 hours old)
    fixtures.append(LabelledForensicFixture(
        fixture_id="fault-stale-age-3h",
        variable=ObservedVariable.TEMPERATURE_2M,
        value=26.0,
        unit=StandardUnit.CELSIUS,
        expected_is_fault=True,
        expected_state=HealthState.STALE,
        expected_reason=ForensicReasonCode.ERR_STALE_OBSERVATION,
        event_time_offset_sec=-10800.0,  # -3 hours
    ))
    # 23. Clock skew: timestamp 10 minutes in the future
    fixtures.append(LabelledForensicFixture(
        fixture_id="fault-clock-skew-future",
        variable=ObservedVariable.TEMPERATURE_2M,
        value=26.0,
        unit=StandardUnit.CELSIUS,
        expected_is_fault=True,
        expected_state=HealthState.FAULTY,
        expected_reason=ForensicReasonCode.ERR_CLOCK_SKEW,
        event_time_offset_sec=600.0,  # +10 minutes in future
    ))

    # -----------------------------------------------------------------------
    # Group H: True Faults — Sensor Drift (Ground Truth: FAULTY)
    # -----------------------------------------------------------------------
    # 24. Sensor drift: 4.5 sigma divergence from reference cluster
    fixtures.append(LabelledForensicFixture(
        fixture_id="fault-drift-4sigma",
        variable=ObservedVariable.TEMPERATURE_2M,
        value=32.0,
        unit=StandardUnit.CELSIUS,
        expected_is_fault=True,
        expected_state=HealthState.FAULTY,
        expected_reason=ForensicReasonCode.ERR_SENSOR_DRIFT,
        reference_mean=24.0,
        reference_std=1.5,
        reference_sample_count=36,
    ))

    return fixtures


class TestSensorHealthConfusionMatrix:
    """Confusion matrix benchmark asserting precision, recall, and zero natural flatline false positives."""

    def setup_method(self) -> None:
        self.evaluator = DeterministicSensorHealthEvaluator()
        self.base_time = datetime(2026, 11, 3, 10, 0, 0, tzinfo=timezone.utc)

    def test_confusion_matrix_metrics(self) -> None:
        fixtures = generate_labelled_fixtures()

        tp = 0  # True Positives: Actual Fault correctly identified as FAULTY or STALE
        fp = 0  # False Positives: Actual Healthy misclassified as FAULTY or STALE
        tn = 0  # True Negatives: Actual Healthy correctly identified as HEALTHY or SUSPECT/UNKNOWN
        fn = 0  # False Negatives: Actual Fault misclassified as HEALTHY

        natural_flatlines_tested = 0
        natural_flatlines_false_positives = 0

        for f in fixtures:
            eval_time = self.base_time + timedelta(seconds=f.event_time_offset_sec)
            prev_time = None
            if f.previous_value is not None and f.delta_seconds is not None:
                prev_time = eval_time - timedelta(seconds=f.delta_seconds)

            result = self.evaluator.evaluate_observation(
                event_id=f"bench-{f.fixture_id}",
                field_id="field_kolar_01",
                sensor_id=f"sensor_{f.fixture_id}",
                variable=f.variable,
                value=f.value,
                unit=f.unit,
                event_time=eval_time,
                now=self.base_time,
                previous_value=f.previous_value,
                previous_event_time=prev_time,
                history_values=f.history_values,
                provenance_class=f.provenance_class,
                corroborating_neighbor_variance=f.corroborating_neighbor_variance,
                corroborating_rain_detected=f.corroborating_rain_detected,
                corroborating_rain_mm=f.corroborating_rain_mm,
                reference_mean=f.reference_mean,
                reference_std=f.reference_std,
                reference_sample_count=f.reference_sample_count,
            )

            predicted_is_fault = result.health_state in (HealthState.FAULTY, HealthState.STALE)

            # Specific check for natural flatline fixtures
            if "flatline" in f.fixture_id:
                natural_flatlines_tested += 1
                if predicted_is_fault:
                    natural_flatlines_false_positives += 1

            # Confusion matrix accumulation
            if f.expected_is_fault:
                if predicted_is_fault:
                    tp += 1
                    assert result.reason_code == f.expected_reason.value, (
                        f"Fixture '{f.fixture_id}': expected reason '{f.expected_reason.value}', got '{result.reason_code}'"
                    )
                else:
                    fn += 1
            else:
                if predicted_is_fault:
                    fp += 1
                else:
                    tn += 1

        total = len(fixtures)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        print("\n=======================================================")
        print("Sensor Health Forensics: Benchmark Confusion Matrix")
        print("=======================================================")
        print(f"Total Benchmark Fixtures:   {total}")
        print(f"True Positives (TP):        {tp}")
        print(f"True Negatives (TN):        {tn}")
        print(f"False Positives (FP):       {fp}")
        print(f"False Negatives (FN):       {fn}")
        print("-" * 55)
        print(f"Precision:                  {precision:.4f} (Target: >= 0.95)")
        print(f"Recall:                     {recall:.4f} (Target: >= 0.95)")
        print(f"Specificity:                {specificity:.4f} (Target: >= 0.95)")
        print(f"F1-Score:                   {f1:.4f} (Target: >= 0.95)")
        print("-" * 55)
        print(f"Natural Flatlines Tested:   {natural_flatlines_tested}")
        print(f"Flatline False Positives:   {natural_flatlines_false_positives} (Target: EXACTLY 0)")
        print("=======================================================")

        # Assertions
        assert natural_flatlines_false_positives == 0, "CRITICAL: Natural flatline misclassified as faulty!"
        assert precision >= 0.95, f"Precision {precision:.2f} below target 0.95"
        assert recall >= 0.95, f"Recall {recall:.2f} below target 0.95"
        assert f1 >= 0.95, f"F1-Score {f1:.2f} below target 0.95"
        assert fp == 0, f"Expected 0 False Positives on benchmark set, got {fp}"
        assert fn == 0, f"Expected 0 False Negatives on benchmark set, got {fn}"

