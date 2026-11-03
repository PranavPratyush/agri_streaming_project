"""Idempotent Kafka Producer client for AgriKafka-Agent ingestion layer."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from agri_contracts import (
    AgriObservationEvent,
    DeadLetterRecordEvent,
    WeatherContextEvent,
    wrap_in_dead_letter,
)
from agri_ingestion.config import IngestionConfig
from agri_ingestion.metrics import METRICS

logger = logging.getLogger("agri_ingestion.producer")


class AgriKafkaProducer:
    """Enterprise-grade idempotent Kafka producer with DLQ fallback."""

    def __init__(self, config: Optional[IngestionConfig] = None, dry_run: bool = False) -> None:
        self.config = config or IngestionConfig()
        self.dry_run = dry_run
        self._producer: Any = None
        self._published_history: List[Dict[str, Any]] = []

        if not self.dry_run:
            self._init_kafka_producer()

    def _init_kafka_producer(self) -> None:
        try:
            import confluent_kafka

            producer_conf = {
                "bootstrap.servers": self.config.bootstrap_servers,
                "acks": self.config.producer_acks,
                "enable.idempotence": self.config.producer_enable_idempotence,
                "retries": self.config.producer_retries,
                "max.in.flight.requests.per.connection": self.config.producer_max_in_flight,
                "linger.ms": self.config.producer_linger_ms,
                "client.id": "agrikafka-ingestion-producer",
            }
            self._producer = confluent_kafka.Producer(producer_conf)
            logger.info("Initialized idempotent Kafka Producer on %s", self.config.bootstrap_servers)
        except Exception as exc:
            logger.warning(
                "Failed to initialize confluent_kafka Producer (%s). Operating in dry-run/mock mode.",
                exc,
            )
            self.dry_run = True

    def _delivery_callback(self, err: Any, msg: Any) -> None:
        if err is not None:
            logger.error("Kafka message delivery failed: %s", err)
            METRICS.record_failure("kafka_producer", "delivery_error")
        else:
            METRICS.record_ingested(msg.topic())

    def publish_observation(
        self,
        event: AgriObservationEvent,
        topic: Optional[str] = None,
        callback: Optional[Callable[[Any, Any], None]] = None,
    ) -> bool:
        """Publishes an AgriObservationEvent partitioned by field_id."""
        target_topic = topic or self.config.topic_raw_observations
        key_bytes = event.field_id.encode("utf-8")
        headers = [
            ("event_id", event.event_id.encode("utf-8")),
            ("schema_version", event.schema_version.encode("utf-8")),
            ("idempotency_key", event.idempotency_key.encode("utf-8")),
            ("source_provider", event.source_provider.encode("utf-8")),
        ]

        try:
            value_bytes = event.model_dump_json().encode("utf-8")
        except Exception as exc:
            logger.error("Failed to serialize AgriObservationEvent %s: %s", event.event_id, exc)
            self.publish_dlq(wrap_in_dead_letter(str(event), target_topic, exc))
            return False

        if self.dry_run or self._producer is None:
            self._published_history.append(
                {"topic": target_topic, "key": event.field_id, "event_id": event.event_id, "data": event}
            )
            METRICS.record_ingested(target_topic)
            logger.debug("[DRY-RUN] Emitted observation %s to topic %s", event.event_id, target_topic)
            return True

        try:
            self._producer.produce(
                topic=target_topic,
                key=key_bytes,
                value=value_bytes,
                headers=headers,
                on_delivery=callback or self._delivery_callback,
            )
            self._producer.poll(0)
            return True
        except Exception as exc:
            logger.error("Exception producing observation %s to Kafka: %s", event.event_id, exc)
            METRICS.record_failure("kafka_producer", "produce_exception")
            self.publish_dlq(wrap_in_dead_letter(value_bytes, target_topic, exc))
            return False

    def publish_weather_context(
        self,
        event: WeatherContextEvent,
        topic: Optional[str] = None,
        callback: Optional[Callable[[Any, Any], None]] = None,
    ) -> bool:
        """Publishes a WeatherContextEvent partitioned by field_id."""
        target_topic = topic or self.config.topic_weather_data
        key_bytes = event.field_id.encode("utf-8")
        headers = [
            ("event_id", event.event_id.encode("utf-8")),
            ("schema_version", event.schema_version.encode("utf-8")),
            ("idempotency_key", event.idempotency_key.encode("utf-8")),
            ("source_provider", event.source_provider.encode("utf-8")),
        ]

        try:
            value_bytes = event.model_dump_json().encode("utf-8")
        except Exception as exc:
            logger.error("Failed to serialize WeatherContextEvent %s: %s", event.event_id, exc)
            self.publish_dlq(wrap_in_dead_letter(str(event), target_topic, exc))
            return False

        if self.dry_run or self._producer is None:
            self._published_history.append(
                {"topic": target_topic, "key": event.field_id, "event_id": event.event_id, "data": event}
            )
            METRICS.record_ingested(target_topic)
            logger.debug("[DRY-RUN] Emitted weather context %s to topic %s", event.event_id, target_topic)
            return True

        try:
            self._producer.produce(
                topic=target_topic,
                key=key_bytes,
                value=value_bytes,
                headers=headers,
                on_delivery=callback or self._delivery_callback,
            )
            self._producer.poll(0)
            return True
        except Exception as exc:
            logger.error("Exception producing weather context %s to Kafka: %s", event.event_id, exc)
            METRICS.record_failure("kafka_producer", "produce_exception")
            self.publish_dlq(wrap_in_dead_letter(value_bytes, target_topic, exc))
            return False

    def publish_dlq(self, dlq_event: DeadLetterRecordEvent) -> bool:
        """Publishes an unrecoverable or malformed record to the dead-letter queue."""
        target_topic = self.config.topic_dead_letter
        key_bytes = dlq_event.dlq_id.encode("utf-8")

        try:
            value_bytes = dlq_event.model_dump_json().encode("utf-8")
        except Exception as exc:
            logger.critical("Fatal: Cannot serialize DeadLetterRecordEvent %s: %s", dlq_event.dlq_id, exc)
            return False

        if self.dry_run or self._producer is None:
            self._published_history.append(
                {"topic": target_topic, "key": dlq_event.dlq_id, "dlq_id": dlq_event.dlq_id, "data": dlq_event}
            )
            METRICS.record_failure("dlq", "routed_to_dlq")
            logger.warning("[DRY-RUN] Routed message to DLQ: %s", dlq_event.error_reason)
            return True

        try:
            self._producer.produce(
                topic=target_topic,
                key=key_bytes,
                value=value_bytes,
                on_delivery=self._delivery_callback,
            )
            self._producer.poll(0)
            return True
        except Exception as exc:
            logger.critical("Catastrophic error writing to DLQ topic %s: %s", target_topic, exc)
            return False

    def flush(self, timeout: float = 5.0) -> int:
        if self._producer is not None:
            return self._producer.flush(timeout)
        return 0

    def get_published_history(self) -> List[Dict[str, Any]]:
        """Returns in-memory history of published events (useful for unit tests & dry runs)."""
        return list(self._published_history)

    def clear_history(self) -> None:
        self._published_history.clear()

