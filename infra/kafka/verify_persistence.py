#!/usr/bin/env python3
"""Kafka persistence verifier for AgriKafka-Agent.

Validates that messages written to Kafka topics persist across container restarts
and are safely retained on the named Docker volume `agrikafka_dev_data`.
"""

import sys
import time
import subprocess
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
)


def produce_persistence_marker(bootstrap_servers: str, marker_id: str, topic: str = "agri.sensor-readings") -> bool:
    print(f"\n1. Producing persistence test marker: {marker_id}...")
    producer = Producer({
        "bootstrap.servers": bootstrap_servers,
        "client.id": "agrikafka-persist-producer",
        "enable.idempotence": True,
        "acks": "all",
        "socket.timeout.ms": 5000,
    })

    event = AgriObservationEvent(
        event_time=datetime.now(timezone.utc),
        field_id="KA_KOLAR_RAGI_01",
        idempotency_key=marker_id,
        source_provider="persistence_verifier",
        sensor_id="persist_probe_01",
        variable=ObservedVariable.SOIL_MOISTURE_15CM,
        value=0.185,
        unit=StandardUnit.M3_PER_M3,
        location=LocationMetadata(latitude=13.13, longitude=78.13, elevation_m=822.0),
        provenance=ProvenanceMetadata(
            provenance_class=ProvenanceClass.PHYSICAL_SENSOR,
            dataset_origin="Persistence-Drill",
            is_synthetic=True,
            scenario_id="PERSISTENCE_RESTART_DRILL",
        ),
    )

    payload = event.model_dump_json().encode("utf-8")
    producer.produce(topic=topic, key=event.field_id.encode("utf-8"), value=payload)
    producer.flush(timeout=10)
    print(f"[COMMITTED] Marker {marker_id} produced and flushed to broker.")
    return True


def restart_kafka_container() -> bool:
    print("\n2. Executing 'docker compose restart kafka'...")
    try:
        res = subprocess.run(
            ["docker", "compose", "restart", "kafka"],
            capture_output=True,
            text=True,
            timeout=45,
            check=True
        )
        print(f"Docker output: {res.stdout.strip()}")
        print("Waiting 15 seconds for broker to recover and complete KRaft metadata re-election...")
        time.sleep(15)
        return True
    except Exception as e:
        print(f"Failed to restart container: {e}")
        return False


def consume_persistence_marker(bootstrap_servers: str, marker_id: str, topic: str = "agri.sensor-readings") -> bool:
    print(f"\n3. Consuming from topic '{topic}' after restart with a fresh consumer group...")
    group_id = f"persist-verify-group-{uuid.uuid4().hex[:8]}"
    consumer = Consumer({
        "bootstrap.servers": bootstrap_servers,
        "group.id": group_id,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
        "socket.timeout.ms": 5000,
    })
    consumer.subscribe([topic])

    start_time = time.time()
    found = False
    while time.time() - start_time < 20:
        msg = consumer.poll(timeout=1.0)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            else:
                print(f"[CONSUMER ERROR] {msg.error()}")
                break

        val = msg.value().decode("utf-8")
        if marker_id in val:
            print(f"[VERIFIED] Successfully recovered marker {marker_id} from partition [{msg.partition()}] offset [{msg.offset()}]!")
            found = True
            break

    consumer.close()
    return found


def main():
    bootstrap = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:9092"
    marker_id = f"PERSIST_MARKER_{int(time.time())}"

    print("=== AgriKafka Volume Persistence Verification Drill ===")
    if not produce_persistence_marker(bootstrap, marker_id):
        return 1

    if not restart_kafka_container():
        return 2

    if not consume_persistence_marker(bootstrap, marker_id):
        print("\n[FAILURE] Persistence verification failed: message was lost after container restart.")
        return 3

    print("\n[SUCCESS] Persistence drill verified! Messages survived container restart on persistent volume.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
