"""Kafka-to-TimescaleDB Persistence Consumer.

Consumes validated observations, sensor health results, and candidate alerts from Kafka,
and persists them to TimescaleDB / PostgreSQL using idempotent upserts.

Delivery Semantics:
- Transport: At-Least-Once (manual offset commit strictly after database transaction commit).
- State: Effectively-Once (enforced by DB unique constraints and ON CONFLICT DO NOTHING/UPDATE).
"""

from __future__ import annotations

import json
import logging
import signal
import sys
import time
from typing import Any, Callable, Dict, List, Optional

try:
    from confluent_kafka import Consumer, KafkaError, KafkaException, Message
except ImportError:
    Consumer = None  # type: ignore
    KafkaError = None  # type: ignore
    KafkaException = None  # type: ignore
    Message = None  # type: ignore

from agri_contracts.models.observation import AgriObservationEvent
from agri_contracts.models.sensor_health import SensorHealthResultEvent
from agri_contracts.models.crop_risk import CropRiskCandidateAlertEvent
from agri_persistence.repository import PersistenceRepository

logger = logging.getLogger(__name__)


class KafkaDatabaseConsumer:
    """Consumes Kafka events and persists them idempotently to TimescaleDB."""

    def __init__(
        self,
        repository: PersistenceRepository,
        bootstrap_servers: str = "127.0.0.1:9092",
        group_id: str = "agri-timescale-sink-group",
        topics: Optional[List[str]] = None,
        mock_mode: bool = False,
    ) -> None:
        self.repository = repository
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.topics = topics or [
            "agri.sensor-readings",
            "agri.validated-observations",
            "agri.sensor-health-events",
            "agri.candidate-alerts",
        ]
        self.mock_mode = mock_mode
        self._running = False
        self._consumer: Optional[Consumer] = None
        self.messages_persisted = 0
        self.duplicates_prevented = 0
        self.errors_count = 0

    def init_consumer(self) -> None:
        """Initializes confluent-kafka Consumer with manual offset commit."""
        if self.mock_mode:
            logger.info("KafkaDatabaseConsumer running in mock_mode (no live broker needed).")
            return

        if Consumer is None:
            raise RuntimeError("confluent-kafka must be installed to run KafkaDatabaseConsumer.")

        conf = {
            "bootstrap.servers": self.bootstrap_servers,
            "group.id": self.group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,  # Manual commit ensures at-least-once delivery
            "session.timeout.ms": 30000,
            "max.poll.interval.ms": 300000,
        }
        self._consumer = Consumer(conf)
        self._consumer.subscribe(self.topics)
        logger.info("Kafka consumer subscribed to topics: %s", self.topics)

    def process_message_payload(self, topic: str, payload_str: str) -> bool:
        """Processes and routes a single message string payload to the appropriate repository method.

        Returns True if a new row was inserted, False if skipped due to idempotency conflict.
        """
        try:
            data = json.loads(payload_str)
        except json.JSONDecodeError as err:
            logger.error("Failed to decode message JSON: %s. Raw: %s", err, payload_str[:100])
            self.errors_count += 1
            return False

        try:
            if topic in ("agri.validated-observations", "agri.sensor-readings") or "observed_variable" in data:
                # Differentiate between windowed feature rollup and single observation
                if "feature_name" in data and "window_start" in data:
                    inserted = self.repository.upsert_windowed_feature(data)
                else:
                    event = AgriObservationEvent.model_validate(data)
                    inserted = self.repository.upsert_observation(event)

            elif topic == "agri.sensor-health-events" or "health_state" in data:
                event = SensorHealthResultEvent.model_validate(data)
                inserted = self.repository.upsert_sensor_health_event(event)

            elif topic == "agri.candidate-alerts" or "composite_stress_index" in data:
                event = CropRiskCandidateAlertEvent.model_validate(data)
                inserted = self.repository.upsert_crop_candidate_alert(event)

            else:
                logger.warning("Unknown message structure on topic %s: %s", topic, list(data.keys()))
                return False

            if inserted:
                self.messages_persisted += 1
                return True
            else:
                self.duplicates_prevented += 1
                return False

        except Exception as err:
            logger.error("Error processing event on %s: %s", topic, err, exc_info=True)
            self.errors_count += 1
            raise

    def run(self, max_messages: Optional[int] = None) -> None:
        """Starts the consumption loop.

        Guarantees that consumer.commit() is ONLY invoked after the database
        transaction has committed successfully.
        """
        if self._consumer is None and not self.mock_mode:
            self.init_consumer()

        self._running = True
        logger.info("Kafka database persistence sink started.")
        processed = 0

        try:
            while self._running:
                if max_messages is not None and processed >= max_messages:
                    break

                if self.mock_mode:
                    break

                assert self._consumer is not None
                msg = self._consumer.poll(timeout=1.0)
                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error("Kafka consumer error: %s", msg.error())
                        continue

                topic = msg.topic()
                payload_str = msg.value().decode("utf-8")

                try:
                    # 1. Database upsert
                    self.process_message_payload(topic, payload_str)

                    # 2. Synchronous manual commit only after successful DB persistence
                    self._consumer.commit(message=msg, asynchronous=False)
                    processed += 1

                except Exception as db_err:
                    logger.error("Persistence failed for offset %s on topic %s: %s. Offset NOT committed.",
                                 msg.offset(), topic, db_err)
                    # Bounded backoff before next poll attempt
                    time.sleep(1.0)

        finally:
            self.close()

    def close(self) -> None:
        """Gracefully closes the consumer."""
        self._running = False
        if self._consumer is not None:
            logger.info("Closing Kafka consumer.")
            try:
                self._consumer.close()
            except Exception as e:
                logger.warning("Error closing Kafka consumer: %s", e)
            self._consumer = None

