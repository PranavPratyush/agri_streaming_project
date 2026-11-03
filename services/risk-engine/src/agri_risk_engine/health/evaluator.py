"""Deterministic Sensor Health Evaluator orchestrating multi-dimensional forensic detectors."""

from datetime import datetime, timezone
import math
from typing import Any
import uuid

from agri_contracts.enums import (
    HealthState,
    ObservedVariable,
    ProvenanceClass,
    SensorHealthFlag,
    StandardUnit,
)
from agri_contracts.models.sensor_health import SensorHealthResultEvent
from agri_risk_engine.health.detectors import (
    DropoutDetector,
    RangeAndSpikeDetector,
    SensorDriftDetector,
    SourceVsSensorOutageDetector,
    StalenessAndCadenceDetector,
    StuckValueDetector,
)
from agri_risk_engine.health.state import (
    ForensicReasonCode,
    HealthEvidence,
    is_measurement_usable_for_advisory,
)
from agri_risk_engine.health.thresholds import HealthThresholdsConfig


class DeterministicSensorHealthEvaluator:
    """Master evaluator combining temporal, electrical, boundary, variance, and spatial checks."""

    def __init__(self, thresholds: HealthThresholdsConfig | None = None) -> None:
        self.thresholds = thresholds or HealthThresholdsConfig()
        self.staleness_detector = StalenessAndCadenceDetector(self.thresholds)
        self.range_spike_detector = RangeAndSpikeDetector(self.thresholds)
        self.dropout_detector = DropoutDetector(self.thresholds)
        self.stuck_detector = StuckValueDetector(self.thresholds)
        self.drift_detector = SensorDriftDetector(self.thresholds)
        self.outage_detector = SourceVsSensorOutageDetector()

    def evaluate_observation(
        self,
        event_id: str,
        field_id: str,
        sensor_id: str,
        variable: ObservedVariable,
        value: float,
        unit: StandardUnit | str,
        event_time: datetime,
        now: datetime | None = None,
        previous_value: float | None = None,
        previous_event_time: datetime | None = None,
        history_values: list[float] | None = None,
        provenance_class: ProvenanceClass = ProvenanceClass.PHYSICAL_SENSOR,
        expected_cadence_sec: float = 300.0,
        seen_event_ids: set[str] | None = None,
        corroborating_neighbor_variance: float | None = None,
        corroborating_rain_detected: bool | None = None,
        corroborating_rain_mm: float | None = None,
        reference_mean: float | None = None,
        reference_std: float | None = None,
        reference_sample_count: int = 0,
    ) -> SensorHealthResultEvent:
        """Execute deterministic forensic evaluation pipeline and return canonical health event."""
        eval_now = now or datetime.now(timezone.utc)
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)
        if eval_now.tzinfo is None:
            eval_now = eval_now.replace(tzinfo=timezone.utc)

        all_evidence: list[HealthEvidence] = []
        delta_sec = None
        if previous_event_time is not None:
            delta_sec = (event_time - previous_event_time).total_seconds()

        # Step 1: Electrical Dropout & Sentinel Check
        d_state, d_flag, d_ev = self.dropout_detector.evaluate(
            variable=variable, value=value, previous_value=previous_value
        )
        all_evidence.append(d_ev)
        if d_state == HealthState.FAULTY:
            return self._build_health_event(
                field_id=field_id,
                sensor_id=sensor_id,
                variable=variable,
                health_state=d_state,
                health_flag=d_flag,
                primary_evidence=d_ev,
                event_time=event_time,
                history_values=history_values,
                provenance_class=provenance_class,
                confidence=1.0,
            )

        # Step 2: Plausibility Bounds & Abrupt Spikes
        r_state, r_flag, r_ev = self.range_spike_detector.evaluate(
            variable=variable,
            value=value,
            unit=unit,
            previous_value=previous_value,
            delta_seconds=delta_sec,
            corroborating_rain_mm=corroborating_rain_mm,
        )
        all_evidence.append(r_ev)
        if r_state == HealthState.FAULTY:
            return self._build_health_event(
                field_id=field_id,
                sensor_id=sensor_id,
                variable=variable,
                health_state=r_state,
                health_flag=r_flag,
                primary_evidence=r_ev,
                event_time=event_time,
                history_values=history_values,
                provenance_class=provenance_class,
                confidence=1.0,
            )

        # Step 3: Staleness, Clock Skew, Reversal, & Cadence
        s_state, s_flag, s_ev = self.staleness_detector.evaluate(
            event_time=event_time,
            now=eval_now,
            previous_event_time=previous_event_time,
            expected_cadence_sec=expected_cadence_sec,
            seen_event_ids=seen_event_ids,
            event_id=event_id,
        )
        all_evidence.append(s_ev)
        if s_state in (HealthState.FAULTY, HealthState.STALE):
            return self._build_health_event(
                field_id=field_id,
                sensor_id=sensor_id,
                variable=variable,
                health_state=s_state,
                health_flag=s_flag,
                primary_evidence=s_ev,
                event_time=event_time,
                history_values=history_values,
                provenance_class=provenance_class,
                confidence=0.95,
            )

        # Step 4: Stuck Value Check with Natural Flatline Differentiation
        stuck_state = HealthState.HEALTHY
        stuck_flag = SensorHealthFlag.HEALTHY
        stuck_ev = None
        if history_values is not None and len(history_values) > 0:
            stuck_state, stuck_flag, stuck_ev = self.stuck_detector.evaluate(
                variable=variable,
                history_values=history_values,
                provenance_class=provenance_class,
                corroborating_neighbor_variance=corroborating_neighbor_variance,
                corroborating_rain_detected=corroborating_rain_detected,
            )
            all_evidence.append(stuck_ev)
            if stuck_state == HealthState.FAULTY:
                return self._build_health_event(
                    field_id=field_id,
                    sensor_id=sensor_id,
                    variable=variable,
                    health_state=stuck_state,
                    health_flag=stuck_flag,
                    primary_evidence=stuck_ev,
                    event_time=event_time,
                    history_values=history_values,
                    provenance_class=provenance_class,
                    confidence=0.95,
                )

        # Step 5: Sensor Drift Check (if reference cluster available)
        drift_state = HealthState.HEALTHY
        drift_flag = SensorHealthFlag.HEALTHY
        drift_ev = None
        if reference_mean is not None:
            drift_state, drift_flag, drift_ev = self.drift_detector.evaluate(
                current_value=value,
                reference_mean=reference_mean,
                reference_std=reference_std,
                sample_count=reference_sample_count,
            )
            all_evidence.append(drift_ev)
            if drift_state == HealthState.FAULTY:
                return self._build_health_event(
                    field_id=field_id,
                    sensor_id=sensor_id,
                    variable=variable,
                    health_state=drift_state,
                    health_flag=drift_flag,
                    primary_evidence=drift_ev,
                    event_time=event_time,
                    history_values=history_values,
                    provenance_class=provenance_class,
                    confidence=0.90,
                )

        # Step 6: Determine Composite State for non-fault cases (Suspect / Unknown / Healthy)
        composite_state = HealthState.HEALTHY
        composite_flag = SensorHealthFlag.HEALTHY
        primary_ev = r_ev

        for ev_item, st, fl in [
            (s_ev, s_state, s_flag),
            (stuck_ev, stuck_state, stuck_flag),
            (drift_ev, drift_state, drift_flag),
        ]:
            if ev_item is not None:
                if st == HealthState.SUSPECT and composite_state != HealthState.FAULTY:
                    composite_state = HealthState.SUSPECT
                    composite_flag = fl
                    primary_ev = ev_item
                elif st == HealthState.UNKNOWN and composite_state == HealthState.HEALTHY:
                    composite_state = HealthState.UNKNOWN
                    composite_flag = fl
                    primary_ev = ev_item

        return self._build_health_event(
            field_id=field_id,
            sensor_id=sensor_id,
            variable=variable,
            health_state=composite_state,
            health_flag=composite_flag,
            primary_evidence=primary_ev,
            event_time=event_time,
            history_values=history_values,
            provenance_class=provenance_class,
            confidence=0.90 if composite_state == HealthState.HEALTHY else 0.70,
        )

    def _build_health_event(
        self,
        field_id: str,
        sensor_id: str,
        variable: ObservedVariable,
        health_state: HealthState,
        health_flag: SensorHealthFlag,
        primary_evidence: HealthEvidence,
        event_time: datetime,
        history_values: list[float] | None,
        provenance_class: ProvenanceClass,
        confidence: float,
    ) -> SensorHealthResultEvent:
        mean_val = None
        std_val = None
        if history_values and len(history_values) > 0:
            mean_val = round(sum(history_values) / len(history_values), 3)
            if len(history_values) > 1:
                var = sum((x - mean_val) ** 2 for x in history_values) / (len(history_values) - 1)
                std_val = round(math.sqrt(var), 3)
            else:
                std_val = 0.0

        is_suppressed = health_state in (HealthState.FAULTY, HealthState.STALE)
        usable_for_advisory = is_measurement_usable_for_advisory(health_state, is_suppressed)

        return SensorHealthResultEvent(
            event_id=str(uuid.uuid4()),
            schema_version="1.0.0",
            event_time=event_time,
            ingestion_time=datetime.now(timezone.utc),
            field_id=field_id,
            idempotency_key=f"health:{sensor_id}:{variable.value}:{int(event_time.timestamp())}",
            sensor_id=sensor_id,
            variable=variable,
            health_flag=health_flag,
            health_state=health_state,
            confidence_score=confidence,
            detected_anomaly_reason=primary_evidence.summary,
            reason_code=primary_evidence.reason_code.value,
            evidence=primary_evidence.to_dict(),
            observed_mean_window=mean_val,
            observed_std_window=std_val,
            is_suppressed=is_suppressed,
            is_usable_for_advisory=usable_for_advisory,
            provenance={
                "provenance_class": provenance_class,
                "dataset_origin": "DeterministicSensorHealthEvaluator",
                "is_synthetic": provenance_class == ProvenanceClass.INJECTED_SCENARIO,
            },
        )
