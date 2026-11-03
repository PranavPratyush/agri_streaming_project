"""Deterministic sensor health forensic detectors for agricultural IoT telemetry."""

import math
from datetime import datetime, timezone
from typing import Any

from agri_contracts.enums import (
    HealthState,
    ObservedVariable,
    ProvenanceClass,
    SensorHealthFlag,
    StandardUnit,
)
from agri_contracts.validation import VARIABLE_BOUNDS
from agri_risk_engine.health.state import ForensicReasonCode, HealthEvidence
from agri_risk_engine.health.thresholds import HealthThresholdsConfig


class StalenessAndCadenceDetector:
    """Evaluates observation freshness, timestamp reversals, clock skew, and cadence regularity."""

    def __init__(self, thresholds: HealthThresholdsConfig | None = None) -> None:
        self.thresholds = thresholds or HealthThresholdsConfig()

    def evaluate(
        self,
        event_time: datetime,
        now: datetime | None = None,
        previous_event_time: datetime | None = None,
        expected_cadence_sec: float = 300.0,
        seen_event_ids: set[str] | None = None,
        event_id: str | None = None,
    ) -> tuple[HealthState, SensorHealthFlag, HealthEvidence]:
        """Detect staleness, timestamp reversals, clock skew, and cadence defects."""
        eval_now = now or datetime.now(timezone.utc)
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)
        if eval_now.tzinfo is None:
            eval_now = eval_now.replace(tzinfo=timezone.utc)

        # 1. Duplicate Event ID check
        if seen_event_ids is not None and event_id is not None and event_id in seen_event_ids:
            evidence = HealthEvidence(
                detector_name="StalenessAndCadenceDetector",
                reason_code=ForensicReasonCode.ERR_DUPLICATE_EVENT_ID,
                metrics={"duplicate_event_id": event_id},
                summary=f"Event ID '{event_id}' has already been processed in current session.",
            )
            return HealthState.FAULTY, SensorHealthFlag.UNKNOWN, evidence

        # 2. Clock Skew (future timestamps exceeding tolerance)
        clock_skew_sec = (event_time - eval_now).total_seconds()
        skew_tolerance = float(self.thresholds.clock_skew_tolerance_sec.value)
        if clock_skew_sec > skew_tolerance:
            evidence = HealthEvidence(
                detector_name="StalenessAndCadenceDetector",
                reason_code=ForensicReasonCode.ERR_CLOCK_SKEW,
                metrics={"clock_skew_sec": clock_skew_sec, "tolerance_sec": skew_tolerance},
                thresholds_applied={"clock_skew_tolerance_sec": skew_tolerance},
                summary=f"Event timestamp is {clock_skew_sec:.1f}s in the future (exceeds {skew_tolerance}s tolerance).",
            )
            return HealthState.FAULTY, SensorHealthFlag.UNKNOWN, evidence

        # 3. Timestamp Reversal (out-of-order sequence)
        if previous_event_time is not None:
            if previous_event_time.tzinfo is None:
                previous_event_time = previous_event_time.replace(tzinfo=timezone.utc)
            if event_time < previous_event_time:
                delta_reversal = (previous_event_time - event_time).total_seconds()
                evidence = HealthEvidence(
                    detector_name="StalenessAndCadenceDetector",
                    reason_code=ForensicReasonCode.ERR_TIMESTAMP_REVERSAL,
                    metrics={"reversal_seconds": delta_reversal},
                    summary=f"Timestamp reversal detected: current event is {delta_reversal:.1f}s older than previous reading.",
                )
                return HealthState.SUSPECT, SensorHealthFlag.UNKNOWN, evidence

        # 4. Excessive Age / Stale Observation
        age_sec = (eval_now - event_time).total_seconds()
        max_age = float(self.thresholds.max_acceptable_age_sec.value)
        cadence_mult = float(self.thresholds.cadence_multiplier.value)
        stale_threshold_sec = max(max_age, expected_cadence_sec * cadence_mult)

        if age_sec > stale_threshold_sec:
            evidence = HealthEvidence(
                detector_name="StalenessAndCadenceDetector",
                reason_code=ForensicReasonCode.ERR_STALE_OBSERVATION,
                metrics={"observation_age_sec": age_sec, "threshold_sec": stale_threshold_sec},
                thresholds_applied={"max_acceptable_age_sec": max_age, "cadence_multiplier": cadence_mult},
                summary=f"Observation is stale: age {age_sec:.1f}s exceeds threshold {stale_threshold_sec:.1f}s.",
            )
            return HealthState.STALE, SensorHealthFlag.UNKNOWN, evidence

        # 5. Irregular Cadence Jitter
        if previous_event_time is not None:
            inter_sample_sec = (event_time - previous_event_time).total_seconds()
            if inter_sample_sec > (expected_cadence_sec * cadence_mult):
                evidence = HealthEvidence(
                    detector_name="StalenessAndCadenceDetector",
                    reason_code=ForensicReasonCode.ERR_IRREGULAR_CADENCE,
                    metrics={"inter_sample_sec": inter_sample_sec, "expected_cadence_sec": expected_cadence_sec},
                    summary=f"Telemetry cadence gap of {inter_sample_sec:.1f}s exceeds {cadence_mult}x expected cadence.",
                )
                return HealthState.SUSPECT, SensorHealthFlag.UNKNOWN, evidence

        evidence = HealthEvidence(
            detector_name="StalenessAndCadenceDetector",
            reason_code=ForensicReasonCode.OK_HEALTHY,
            metrics={"observation_age_sec": max(0.0, age_sec)},
            summary="Observation timestamp and cadence are fresh and regular.",
        )
        return HealthState.HEALTHY, SensorHealthFlag.HEALTHY, evidence


class RangeAndSpikeDetector:
    """Evaluates terrestrial plausibility bounds and abrupt rate-of-change spikes."""

    def __init__(self, thresholds: HealthThresholdsConfig | None = None) -> None:
        self.thresholds = thresholds or HealthThresholdsConfig()

    def evaluate(
        self,
        variable: ObservedVariable,
        value: float,
        unit: StandardUnit | str,
        previous_value: float | None = None,
        delta_seconds: float | None = None,
        corroborating_rain_mm: float | None = None,
    ) -> tuple[HealthState, SensorHealthFlag, HealthEvidence]:
        """Assert plausible range and physically possible rate of change."""
        # 1. Non-finite check
        if math.isnan(value) or math.isinf(value):
            evidence = HealthEvidence(
                detector_name="RangeAndSpikeDetector",
                reason_code=ForensicReasonCode.ERR_IMPLAUSIBLE_RANGE,
                metrics={"value": str(value)},
                summary="Value is NaN or infinite.",
            )
            return HealthState.FAULTY, SensorHealthFlag.OUT_OF_BOUNDS, evidence

        # 2. Terrestrial Plausibility Boundaries
        try:
            unit_enum = StandardUnit(unit) if isinstance(unit, str) else unit
        except ValueError:
            evidence = HealthEvidence(
                detector_name="RangeAndSpikeDetector",
                reason_code=ForensicReasonCode.ERR_IMPLAUSIBLE_RANGE,
                metrics={"unit": str(unit)},
                summary=f"Unrecognized or unsupported measurement unit '{unit}'.",
            )
            return HealthState.FAULTY, SensorHealthFlag.OUT_OF_BOUNDS, evidence
        if variable in VARIABLE_BOUNDS:
            min_v, max_v, expected_unit = VARIABLE_BOUNDS[variable]
            if unit_enum != expected_unit:
                evidence = HealthEvidence(
                    detector_name="RangeAndSpikeDetector",
                    reason_code=ForensicReasonCode.ERR_IMPLAUSIBLE_RANGE,
                    metrics={"unit": str(unit_enum), "expected_unit": str(expected_unit)},
                    summary=f"Unit mismatch: variable '{variable.value}' requires '{expected_unit.value}', got '{unit_enum.value}'.",
                )
                return HealthState.FAULTY, SensorHealthFlag.OUT_OF_BOUNDS, evidence

            if value < min_v or value > max_v:
                evidence = HealthEvidence(
                    detector_name="RangeAndSpikeDetector",
                    reason_code=ForensicReasonCode.ERR_IMPLAUSIBLE_RANGE,
                    metrics={"value": value, "min": min_v, "max": max_v},
                    thresholds_applied={"min": min_v, "max": max_v},
                    summary=f"Value {value} is outside terrestrial physical bounds [{min_v}, {max_v}] for '{variable.value}'.",
                )
                return HealthState.FAULTY, SensorHealthFlag.OUT_OF_BOUNDS, evidence

        # 3. Abrupt Spike / Rate of Change
        if previous_value is not None and delta_seconds is not None and delta_seconds > 0:
            delta_val = abs(value - previous_value)
            rate_per_min = delta_val / (delta_seconds / 60.0)
            max_rate = self.thresholds.get_max_rate_for_variable(variable)

            if rate_per_min > max_rate:
                # Soil moisture spike exception: Rapid wetting is physically valid IF heavy rain occurred
                if variable == ObservedVariable.SOIL_MOISTURE_0_TO_7CM and value > previous_value:
                    if corroborating_rain_mm is not None and corroborating_rain_mm >= 2.0:
                        evidence = HealthEvidence(
                            detector_name="RangeAndSpikeDetector",
                            reason_code=ForensicReasonCode.OK_HEALTHY,
                            metrics={
                                "rate_per_min": rate_per_min,
                                "corroborating_rain_mm": corroborating_rain_mm,
                            },
                            summary=f"Rapid soil wetting of {rate_per_min:.3f} m³/m³/min corroborated by {corroborating_rain_mm:.1f}mm rainfall.",
                        )
                        return HealthState.HEALTHY, SensorHealthFlag.HEALTHY, evidence

                evidence = HealthEvidence(
                    detector_name="RangeAndSpikeDetector",
                    reason_code=ForensicReasonCode.ERR_ABRUPT_SPIKE,
                    metrics={
                        "delta_value": delta_val,
                        "delta_seconds": delta_seconds,
                        "rate_per_minute": rate_per_min,
                        "max_rate_per_minute": max_rate,
                    },
                    thresholds_applied={"max_rate_per_minute": max_rate},
                    summary=f"Abrupt spike: rate {rate_per_min:.2f}/min exceeds physical threshold {max_rate:.2f}/min.",
                )
                return HealthState.FAULTY, SensorHealthFlag.SPIKE_ANOMALY, evidence

        evidence = HealthEvidence(
            detector_name="RangeAndSpikeDetector",
            reason_code=ForensicReasonCode.OK_HEALTHY,
            metrics={"value": value},
            summary="Value is within plausible physical range and respects rate-of-change boundaries.",
        )
        return HealthState.HEALTHY, SensorHealthFlag.HEALTHY, evidence


class DropoutDetector:
    """Detects electrical disconnects, pull-up resistor saturation, and hardware crash sentinels."""

    def __init__(self, thresholds: HealthThresholdsConfig | None = None) -> None:
        self.thresholds = thresholds or HealthThresholdsConfig()

    def evaluate(
        self,
        variable: ObservedVariable,
        value: float,
        previous_value: float | None = None,
    ) -> tuple[HealthState, SensorHealthFlag, HealthEvidence]:
        """Detect electrical dropouts and sentinel crash codes."""
        sentinels: set[float] = self.thresholds.dropout_sentinels.value

        # 1. Direct hardware sentinel match
        if value in sentinels:
            evidence = HealthEvidence(
                detector_name="DropoutDetector",
                reason_code=ForensicReasonCode.ERR_MISSING_DROPOUT,
                metrics={"value": value},
                thresholds_applied={"sentinels": list(sentinels)},
                summary=f"Value {value} matches known hardware ADC saturation / dropout sentinel code.",
            )
            return HealthState.FAULTY, SensorHealthFlag.DROPOUT, evidence

        # 2. Sudden drop to 0.0 for variables where true 0.0 is physically impossible or abnormal
        zero_impossible_vars = {
            ObservedVariable.BAROMETRIC_PRESSURE,  # Barometric pressure in hPa (~900 hPa in Kolar)
        }
        if variable in zero_impossible_vars and value == 0.0:
            evidence = HealthEvidence(
                detector_name="DropoutDetector",
                reason_code=ForensicReasonCode.ERR_MISSING_DROPOUT,
                metrics={"value": value, "variable": variable.value},
                summary=f"Variable '{variable.value}' dropped to 0.0, indicating complete electrical signal loss.",
            )
            return HealthState.FAULTY, SensorHealthFlag.DROPOUT, evidence

        # 3. Sudden plunge from high value to 0.0 for relative humidity
        if variable == ObservedVariable.RELATIVE_HUMIDITY_2M and value == 0.0:
            if previous_value is not None and previous_value > 20.0:
                evidence = HealthEvidence(
                    detector_name="DropoutDetector",
                    reason_code=ForensicReasonCode.ERR_MISSING_DROPOUT,
                    metrics={"value": value, "previous_value": previous_value},
                    summary=f"Relative humidity abruptly dropped from {previous_value:.1f}% to 0.0% (signal disconnect).",
                )
                return HealthState.FAULTY, SensorHealthFlag.DROPOUT, evidence

        evidence = HealthEvidence(
            detector_name="DropoutDetector",
            reason_code=ForensicReasonCode.OK_HEALTHY,
            metrics={"value": value},
            summary="No hardware dropout or sentinel saturation detected.",
        )
        return HealthState.HEALTHY, SensorHealthFlag.HEALTHY, evidence


class StuckValueDetector:
    """Evaluates rolling variance and consecutive identical values.
    
    Includes mandatory natural flatline differentiation for precipitation,
    dry-season soil moisture residual plateaus, and gridded reanalysis models.
    """

    def __init__(self, thresholds: HealthThresholdsConfig | None = None) -> None:
        self.thresholds = thresholds or HealthThresholdsConfig()

    def evaluate(
        self,
        variable: ObservedVariable,
        history_values: list[float],
        provenance_class: ProvenanceClass = ProvenanceClass.PHYSICAL_SENSOR,
        corroborating_neighbor_variance: float | None = None,
        corroborating_rain_detected: bool | None = None,
    ) -> tuple[HealthState, SensorHealthFlag, HealthEvidence]:
        """Assess if a sequence of readings is truly stuck or a natural environmental flatline."""
        # Rule 1: Modelled / Reanalysis data is NEVER flagged as a physical sensor fault
        if provenance_class in (ProvenanceClass.MODELLED_REANALYSIS, ProvenanceClass.FORECAST):
            evidence = HealthEvidence(
                detector_name="StuckValueDetector",
                reason_code=ForensicReasonCode.OK_MODELLED_REANALYSIS_BYPASS,
                metrics={"provenance_class": provenance_class.value},
                summary="Gridded model reanalysis is explicitly excluded from hardware stuck-value checks.",
            )
            return HealthState.HEALTHY, SensorHealthFlag.HEALTHY, evidence

        # Rule 2: Minimum sample requirement
        min_samples = int(self.thresholds.stuck_min_consecutive_identical.value)
        if len(history_values) < min_samples:
            evidence = HealthEvidence(
                detector_name="StuckValueDetector",
                reason_code=ForensicReasonCode.UNKNOWN_INSUFFICIENT_HISTORY,
                metrics={"sample_count": len(history_values), "required": min_samples},
                summary=f"Insufficient history ({len(history_values)} samples < {min_samples}) to evaluate stuck status.",
            )
            return HealthState.UNKNOWN, SensorHealthFlag.UNKNOWN, evidence

        # Calculate sample variance on the most recent sliding window of size min_samples
        eval_slice = history_values[-min_samples:]
        n = len(eval_slice)
        mean_val = sum(eval_slice) / n
        variance = sum((x - mean_val) ** 2 for x in eval_slice) / max(1, n - 1)
        var_eps = float(self.thresholds.stuck_variance_epsilon.value)

        # If variance is healthy (> epsilon), sensor is actively varying
        if variance >= var_eps:
            evidence = HealthEvidence(
                detector_name="StuckValueDetector",
                reason_code=ForensicReasonCode.OK_HEALTHY,
                metrics={"variance": variance, "mean": mean_val, "sample_count": n},
                summary="Sensor exhibits natural dynamic variance above noise floor.",
            )
            return HealthState.HEALTHY, SensorHealthFlag.HEALTHY, evidence

        # -------------------------------------------------------------------
        # Natural Flatline Differentiation
        # -------------------------------------------------------------------

        # Rule 3: Precipitation Natural Zero Sequence
        if variable in (ObservedVariable.PRECIPITATION, ObservedVariable.PRECIPITATION_RATE) and mean_val == 0.0:
            # Zero rain is completely normal in semi-arid drylands unless heavy rain is confirmed nearby
            if corroborating_rain_detected is True:
                # Neighbors report rain but this gauge remains at 0.0
                evidence = HealthEvidence(
                    detector_name="StuckValueDetector",
                    reason_code=ForensicReasonCode.ERR_STUCK_VALUE,
                    metrics={"mean": mean_val, "corroborating_rain_detected": True},
                    summary="Rain gauge stuck at 0.0 mm while adjacent sensors and radar confirm active precipitation.",
                )
                return HealthState.FAULTY, SensorHealthFlag.STUCK_VALUE, evidence

            # Without active rain corroboration, a zero sequence is normal
            evidence = HealthEvidence(
                detector_name="StuckValueDetector",
                reason_code=ForensicReasonCode.OK_CORROBORATED_NATURAL_FLATLINE,
                metrics={"mean": mean_val, "samples": n},
                summary="Natural precipitation zero sequence in dry conditions; not a sensor fault.",
            )
            return HealthState.HEALTHY, SensorHealthFlag.HEALTHY, evidence

        # Rule 4: Soil Moisture Residual Moisture Plateau
        # Red sandy loam soils in Karnataka have residual water content theta_r approx 0.08 - 0.12 m3/m3
        if variable in (
            ObservedVariable.SOIL_MOISTURE_0_TO_7CM,
            ObservedVariable.SOIL_MOISTURE_15CM,
            ObservedVariable.SOIL_MOISTURE_30CM,
        ):
            if 0.06 <= mean_val <= 0.14:
                # Soil moisture is at residual capacity and dry; flatline is expected
                if corroborating_rain_detected is not True:
                    evidence = HealthEvidence(
                        detector_name="StuckValueDetector",
                        reason_code=ForensicReasonCode.OK_CORROBORATED_NATURAL_FLATLINE,
                        metrics={"mean_sm": mean_val, "variance": variance},
                        summary=f"Soil moisture plateau at residual dry content ({mean_val:.3f} m³/m³); natural dry-down.",
                    )
                    return HealthState.HEALTHY, SensorHealthFlag.HEALTHY, evidence

        # Rule 5: Dynamic Environmental Variables (Temperature, Humidity, Solar)
        # These MUST exhibit diurnal variance over 12 daytime hours
        if variable in (
            ObservedVariable.TEMPERATURE_2M,
            ObservedVariable.RELATIVE_HUMIDITY_2M,
            ObservedVariable.SOLAR_RADIATION,
        ):
            # Check if neighbors are also completely flat or if there is insufficient corroboration
            if corroborating_neighbor_variance is not None and corroborating_neighbor_variance < var_eps:
                # Both this sensor and neighbor are flat -> unusual microclimate or suspect
                evidence = HealthEvidence(
                    detector_name="StuckValueDetector",
                    reason_code=ForensicReasonCode.SUSPECT_UNVERIFIED_FLATLINE,
                    metrics={"variance": variance, "neighbor_variance": corroborating_neighbor_variance},
                    summary="Zero variance observed, but neighbor also exhibits near-zero variance; marked suspect.",
                )
                return HealthState.SUSPECT, SensorHealthFlag.UNKNOWN, evidence

            evidence = HealthEvidence(
                detector_name="StuckValueDetector",
                reason_code=ForensicReasonCode.ERR_STUCK_VALUE,
                metrics={"variance": variance, "identical_value": mean_val, "samples": n},
                thresholds_applied={"variance_epsilon": var_eps},
                summary=f"Sensor is stuck: constant value {mean_val:.2f} across {n} consecutive cycles with variance < {var_eps}.",
            )
            return HealthState.FAULTY, SensorHealthFlag.STUCK_VALUE, evidence

        # Fallback for other variables with insufficient context
        evidence = HealthEvidence(
            detector_name="StuckValueDetector",
            reason_code=ForensicReasonCode.SUSPECT_UNVERIFIED_FLATLINE,
            metrics={"variance": variance, "mean": mean_val},
            summary="Zero variance detected with insufficient corroboration; marked suspect.",
        )
        return HealthState.SUSPECT, SensorHealthFlag.UNKNOWN, evidence


class SensorDriftDetector:
    """Evaluates persistent deviation from reference baselines or neighboring field sensors."""

    def __init__(self, thresholds: HealthThresholdsConfig | None = None) -> None:
        self.thresholds = thresholds or HealthThresholdsConfig()

    def evaluate(
        self,
        current_value: float,
        reference_mean: float | None = None,
        reference_std: float | None = None,
        sample_count: int = 0,
    ) -> tuple[HealthState, SensorHealthFlag, HealthEvidence]:
        """Detect sensor drift using 3-sigma divergence from reference cluster."""
        min_samples = int(self.thresholds.drift_min_history_samples.value)
        if reference_mean is None or reference_std is None or sample_count < min_samples:
            evidence = HealthEvidence(
                detector_name="SensorDriftDetector",
                reason_code=ForensicReasonCode.UNKNOWN_INSUFFICIENT_HISTORY,
                metrics={"sample_count": sample_count, "required": min_samples},
                summary="Insufficient spatial/historical reference data to establish drift.",
            )
            return HealthState.UNKNOWN, SensorHealthFlag.UNKNOWN, evidence

        std_dev = max(0.1, reference_std)
        z_score = abs(current_value - reference_mean) / std_dev
        sigma_thresh = float(self.thresholds.drift_sigma_threshold.value)

        if z_score > sigma_thresh:
            evidence = HealthEvidence(
                detector_name="SensorDriftDetector",
                reason_code=ForensicReasonCode.ERR_SENSOR_DRIFT,
                metrics={
                    "current_value": current_value,
                    "reference_mean": reference_mean,
                    "reference_std": reference_std,
                    "z_score": round(z_score, 2),
                },
                thresholds_applied={"sigma_threshold": sigma_thresh},
                summary=f"Sensor drift detected: divergence of {z_score:.2f} sigma exceeds threshold of {sigma_thresh:.1f}.",
            )
            return HealthState.FAULTY, SensorHealthFlag.DRIFT_ANOMALY, evidence

        evidence = HealthEvidence(
            detector_name="SensorDriftDetector",
            reason_code=ForensicReasonCode.OK_HEALTHY,
            metrics={"z_score": round(z_score, 2)},
            summary="Sensor measurement aligns with reference cluster within 3 sigma.",
        )
        return HealthState.HEALTHY, SensorHealthFlag.HEALTHY, evidence


class SourceVsSensorOutageDetector:
    """Distinguishes between a comprehensive data provider outage vs an isolated probe failure."""

    def evaluate(
        self,
        target_sensor_id: str,
        active_sensor_ids_in_provider: list[str],
        all_expected_sensor_ids_in_provider: list[str],
    ) -> tuple[HealthState, ForensicReasonCode, str]:
        """Evaluate outage scope based on cluster availability."""
        total_expected = len(all_expected_sensor_ids_in_provider)
        total_active = len(active_sensor_ids_in_provider)

        if total_expected == 0:
            return HealthState.UNKNOWN, ForensicReasonCode.UNKNOWN_INSUFFICIENT_HISTORY, "No expected sensors configured for provider."

        # Case 1: Entire station/provider has 0 active sensors
        if total_active == 0:
            return (
                HealthState.FAULTY,
                ForensicReasonCode.ERR_SOURCE_OUTAGE,
                f"Source/Provider Outage: 0 of {total_expected} expected sensors are communicating. Gateway/API failure.",
            )

        # Case 2: Most sensors are communicating normally, but target probe is absent
        if target_sensor_id not in active_sensor_ids_in_provider:
            return (
                HealthState.FAULTY,
                ForensicReasonCode.ERR_SENSOR_OUTAGE,
                f"Isolated Sensor Outage: Probe '{target_sensor_id}' is down, but {total_active}/{total_expected} companion sensors are healthy.",
            )

        return (
            HealthState.HEALTHY,
            ForensicReasonCode.OK_HEALTHY,
            f"Sensor '{target_sensor_id}' and provider are active ({total_active}/{total_expected} communicating).",
        )
