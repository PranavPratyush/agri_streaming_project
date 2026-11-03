#!/usr/bin/env python3
"""Kafka producer-consumer smoke test for AgriKafka-Agent.

Validates end-to-end publishing and consumption using authentic AgriObservationEvent
and idempotent producer semantics against local broker.
"""

import sys
import json
import time
from datetime import datetime, timezone
import uuid
from confluent_kafka import Producer, Consumer, KafkaError

from agri_contracts import (
    AgriObservationEvent,
    ObservedVariable,
    StandardUnit,
    ProvenanceClass,
    ProvenanceMetadata,
    LocationMetadata,
    QualityFlags,
    SensorHealthFlag,
    ValidationStatus,
)


def delivery_report(err, msg):
    if err is not None:
        print(f"[PRODUCER ERROR] Delivery failed: {err}")
    else:
        print(f"[PRODUCED] Topic={msg.topic()} Partition=[{msg.partition()}] Offset={msg.offset()} Key={msg.key().decode('utf-8')}")


def run_smoke_test(bootstrap_servers: str = "127.0.0.1:9092", target_topic: str = "agri.sensor-readings") -> bool:
    print(f"=== Starting AgriKafka Smoke Test against {bootstrap_servers} ===")
    
    # 1. Create Idempotent Producer
    producer_conf = {
        "bootstrap.servers": bootstrap_servers,
        "client.id": "agrikafka-smoke-producer",
        "enable.idempotence": True,
        "acks": "all",
        "retries": 5,
        "socket.timeout.ms": 5000,
    }
    producer = Producer(producer_conf)

    # 2. Build Authentic Observation Event (Stage 6 verified station)
    unique_key = f"smoke_test_kolar_{int(time.time())}"
    test_event = AgriObservationEvent(
        event_time=datetime.now(timezone.utc),
        field_id="KA_KOLAR_RAGI_01",
        idempotency_key=unique_key,
        source_provider="openSenseMap",
        sensor_id="smoke_probe_01",
        station_id="689b2bdc569c2d0007586ae9",
        variable=ObservedVariable.TEMPERATURE_2M,
        value=26.42,
        unit=StandardUnit.CELSIUS,
        location=LocationMetadata(latitude=13.13, longitude=78.13, elevation_m=822.0),
        quality_flags=QualityFlags(sensor_health_flag=SensorHealthFlag.HEALTHY),
        validation_status=ValidationStatus.VALID,
        provenance=ProvenanceMetadata(
            provenance_class=ProvenanceClass.PHYSICAL_SENSOR,
            dataset_origin="Smoke-Test-Harness",
            is_synthetic=True,
            scenario_id="SMOKE_TEST_BOOTSTRAP",
        ),
    )

    payload_json = test_event.model_dump_json()
    message_key = test_event.field_id.encode("utf-8")

    print(f"Producing message to topic '{target_topic}'...")
    producer.produce(
        topic=target_topic,
        key=message_key,
        value=payload_json.encode("utf-8"),
        callback=delivery_report,
    )
    # Flush ensures message is committed
    producer.flush(timeout=10)

    # 3. Create Consumer to verify message receipt
    group_id = f"smoke-test-group-{uuid.uuid4().hex[:8]}"
    consumer_conf = {
        "bootstrap.servers": bootstrap_servers,
        "group.id": group_id,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
        "socket.timeout.ms": 5000,
    }
    consumer = Consumer(consumer_conf)
    consumer.subscribe([target_topic])

    print(f"Polling topic '{target_topic}' with consumer group '{group_id}'...")
    found = False
    start_time = time.time()
    while time.time() - start_time < 15:
        msg = consumer.poll(timeout=1.0)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            else:
                print(f"[CONSUMER ERROR] {msg.error()}")
                break

        consumed_key = msg.key().decode("utf-8") if msg.key() else None
        consumed_val = msg.value().decode("utf-8")
        
        # Check if this is our produced smoke test event
        if test_event.idempotency_key in consumed_val:
            print(f"[CONSUMED] Topic={msg.topic()} Partition=[{msg.partition()}] Offset={msg.offset()}")
            print(f"  Key verified: {consumed_key}")
            
            # Validate schema contract
            restored = AgriObservationEvent.model_validate_json(consumed_val)
            print(f"  Contract parsed successfully: EventID={restored.event_id}, Value={restored.value} {restored.unit}")
            assert restored.idempotency_key == test_event.idempotency_key
            assert restored.field_id == test_event.field_id
            found = True
            break

    consumer.close()

    if found:
        print("\n[SUCCESS] End-to-end producer-consumer smoke test passed!")
        return True
    else:
        print("\n[FAILURE] Timed out waiting for smoke test message.")
        return False


if __name__ == "__main__":
    bootstrap = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:9092"
    success = run_smoke_test(bootstrap_servers=bootstrap)
    sys.exit(0 if success else 1)
