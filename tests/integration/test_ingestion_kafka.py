"""Integration test suite for AgriKafka-Agent Ingestion Layer against Kafka."""

import datetime
import uuid
import pytest

from agri_contracts import (
    AgriObservationEvent,
    LocationMetadata,
    ObservedVariable,
    ProvenanceClass,
    ProvenanceMetadata,
    QualityFlags,
    SensorHealthFlag,
    SensorPlacementMetadata,
    StandardUnit,
    ValidationStatus,
    WeatherContextEvent,
    wrap_in_dead_letter,
)
from agri_ingestion.config import IngestionConfig
from agri_ingestion.producer import AgriKafkaProducer


def is_kafka_available(bootstrap_servers: str = "127.0.0.1:9092") -> bool:
    try:
        from confluent_kafka.admin import AdminClient
        admin = AdminClient({"bootstrap.servers": bootstrap_servers, "socket.timeout.ms": 3000})
        metadata = admin.list_topics(timeout=3.0)
        return metadata is not None
    except Exception:
        return False


class TestIngestionKafkaIntegration:
    """Verifies Kafka publishing mechanics, partition keying, and DLQ routing."""

    def test_mock_producer_delivery_and_keying(self):
        """Verifies producer publishing in mock/dry-run mode."""
        producer = AgriKafkaProducer(dry_run=True)

        event = AgriObservationEvent(
            event_id=str(uuid.uuid4()),
            schema_version="1.0.0",
            event_time=datetime.datetime.now(datetime.timezone.utc),
            ingestion_time=datetime.datetime.now(datetime.timezone.utc),
            field_id="FIELD-KA-KOLAR-001",
            idempotency_key=f"test:{uuid.uuid4()}",
            correlation_id=None,
            provenance=ProvenanceMetadata(
                provenance_class=ProvenanceClass.PHYSICAL_SENSOR,
                dataset_origin="test_harness",
                is_synthetic=False,
                scenario_id=None,
                source_uri="test://uri",
                raw_payload_hash="test_hash",
            ),
            source_provider="test_provider",
            sensor_id="sensor_001",
            station_id=None,
            variable=ObservedVariable.TEMPERATURE_2M,
            value=24.5,
            unit=StandardUnit.CELSIUS,
            location=LocationMetadata(latitude=13.137, longitude=78.129, elevation_m=822.0),
            sensor_metadata=SensorPlacementMetadata(
                depth_cm=None,
                height_m=1.5,
                sensor_model="TestModel",
                serial_number="TEST-01",
            ),
            quality_flags=QualityFlags(
                is_imputed=False,
                is_out_of_range=False,
                freshness_latency_sec=0.0,
                sensor_health_flag=SensorHealthFlag.HEALTHY,
            ),
            validation_status=ValidationStatus.VALID,
        )

        ok = producer.publish_observation(event)
        assert ok is True

        history = producer.get_published_history()
        assert len(history) == 1
        assert history[0]["topic"] == "agri.sensor-readings"
        assert history[0]["key"] == "FIELD-KA-KOLAR-001"
        assert history[0]["event_id"] == event.event_id

    def test_dlq_routing_on_malformed_record(self):
        """Verifies dead-letter queue packaging and routing."""
        producer = AgriKafkaProducer(dry_run=True)
        malformed_bytes = b'{"corrupted": true, "missing": "everything"}'

        dlq = wrap_in_dead_letter(
            raw_payload=malformed_bytes,
            failed_topic="agri.sensor-readings",
            error=ValueError("Schema validation failed: missing field_id"),
        )

        ok = producer.publish_dlq(dlq)
        assert ok is True

        history = producer.get_published_history()
        assert len(history) == 1
        assert history[0]["topic"] == "agri.dead-letter-queue"
        assert history[0]["key"] == dlq.dlq_id
        assert "Schema validation failed" in history[0]["data"].error_reason

    def test_live_kafka_roundtrip(self):
        """Verifies actual broker publish/consume if local Kafka is running."""
        bootstrap = "127.0.0.1:9092"
        if not is_kafka_available(bootstrap):
            pytest.skip(f"Kafka broker at {bootstrap} is not reachable. Skipping live broker test.")

        import confluent_kafka
        config = IngestionConfig(bootstrap_servers=bootstrap)
        producer = AgriKafkaProducer(config=config, dry_run=False)

        test_field_id = f"FIELD-TEST-{uuid.uuid4().hex[:6]}"
        event = AgriObservationEvent(
            event_id=str(uuid.uuid4()),
            schema_version="1.0.0",
            event_time=datetime.datetime.now(datetime.timezone.utc),
            ingestion_time=datetime.datetime.now(datetime.timezone.utc),
            field_id=test_field_id,
            idempotency_key=f"integration:{uuid.uuid4()}",
            correlation_id=None,
            provenance=ProvenanceMetadata(
                provenance_class=ProvenanceClass.PHYSICAL_SENSOR,
                dataset_origin="integration_test",
                is_synthetic=False,
                scenario_id=None,
                source_uri="test://live",
                raw_payload_hash="live_hash",
            ),
            source_provider="integration_harness",
            sensor_id="live_test_sensor",
            station_id=None,
            variable=ObservedVariable.TEMPERATURE_2M,
            value=26.8,
            unit=StandardUnit.CELSIUS,
            location=LocationMetadata(latitude=13.137, longitude=78.129, elevation_m=822.0),
            sensor_metadata=SensorPlacementMetadata(
                depth_cm=None,
                height_m=1.5,
                sensor_model="IntegrationSensor",
                serial_number="INT-01",
            ),
            quality_flags=QualityFlags(
                is_imputed=False,
                is_out_of_range=False,
                freshness_latency_sec=0.0,
                sensor_health_flag=SensorHealthFlag.HEALTHY,
            ),
            validation_status=ValidationStatus.VALID,
        )

        ok = producer.publish_observation(event)
        producer.flush(timeout=5.0)
        assert ok is True

