"""Kafka streaming health monitor consuming observations and publishing forensic health states."""

from collections import defaultdict, deque
from datetime import datetime, timezone
import json
import logging
from typing import Any

from agri_contracts.enums import (
    HealthState,
    ObservedVariable,
    ProvenanceClass,
    StandardUnit,
)
from agri_contracts.models.observation import AgriObservationEvent
from agri_contracts.models.sensor_health import SensorHealthResultEvent
from agri_risk_engine.health.evaluator import DeterministicSensorHealthEvaluator
from agri_risk_engine.health.thresholds import HealthThresholdsConfig

logger = logging.getLogger("agri_risk_engine.health.kafka_service")


class SensorStateTracker:
    """Maintains lightweight in-memory sliding windows per (field, sensor, variable)."""

    def __init__(self, max_history: int = 36) -> None:
        self.max_history = max_history
        self.last_value: float | None = None
        self.last_event_time: datetime | None = None
        self.history: deque[float] = deque(maxlen=max_history)
        self.seen_event_ids: set[str] = set()

    def update(self, event_id: str, event_time: datetime, value: float) -> None:
        self.last_value = value
        self.last_event_time = event_time
        self.history.append(value)
        self.seen_event_ids.add(event_id)
        if len(self.seen_event_ids) > 1000:
            # Prevent unbounded memory growth by resetting older IDs
            self.seen_event_ids.clear()
            self.seen_event_ids.add(event_id)


class SensorHealthKafkaService:
    """Service consuming raw observations, executing forensics, and publishing to agri.sensor-health-events."""

    def __init__(
        self,
        bootstrap_servers: str = "127.0.0.1:9092",
        input_topic: str = "agri.sensor-readings",
        output_topic: str = "agri.sensor-health-events",
        thresholds: HealthThresholdsConfig | None = None,
    ) -> None:
        self.bootstrap_servers = bootstrap_servers
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.evaluator = DeterministicSensorHealthEvaluator(thresholds)
        self.trackers: dict[str, SensorStateTracker] = defaultdict(SensorStateTracker)
        self.running: bool = False

    def process_observation(
        self,
        obs: AgriObservationEvent,
        now: datetime | None = None,
        corroborating_rain_mm: float | None = None,
    ) -> SensorHealthResultEvent:
        """Process a single canonical observation and return the forensic evaluation result."""
        sensor_id = obs.sensor_id or obs.station_id or f"virtual_{obs.variable.value}"
        tracker_key = f"{obs.field_id}:{sensor_id}:{obs.variable.value}"
        tracker = self.trackers[tracker_key]

        eval_now = now or datetime.now(timezone.utc)
        history_list = list(tracker.history)

        result = self.evaluator.evaluate_observation(
            event_id=obs.event_id,
            field_id=obs.field_id,
            sensor_id=sensor_id,
            variable=obs.variable,
            value=obs.value,
            unit=obs.unit,
            event_time=obs.event_time,
            now=eval_now,
            previous_value=tracker.last_value,
            previous_event_time=tracker.last_event_time,
            history_values=history_list,
            provenance_class=obs.provenance.provenance_class,
            seen_event_ids=tracker.seen_event_ids,
            corroborating_rain_mm=corroborating_rain_mm,
        )

        # Update tracker with current valid observation
        tracker.update(obs.event_id, obs.event_time, obs.value)

        if not result.is_usable_for_advisory:
            logger.warning(
                f"[SAFETY GATE ENGAGED] Sensor '{sensor_id}' variable '{obs.variable.value}' "
                f"flagged {result.health_state.value} ({result.reason_code}). "
                f"Advisory recommendations will be blocked."
            )

        return result

