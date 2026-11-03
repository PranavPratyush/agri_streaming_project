"""AgriKafka-Agent - Demo Fault Injection Script.

Injects controlled test scenarios into Kafka topics to demonstrate Dead-Letter Queue (DLQ)
routing and sensor health anomaly detection during live demonstrations.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone

from confluent_kafka import Producer


def delivery_callback(err, msg):
    if err:
        print(f"[ERROR] Message delivery failed: {err}", file=sys.stderr)
    else:
        print(f"[SUCCESS] Injected record to {msg.topic()} [part {msg.partition()}] offset {msg.offset()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject controlled faults into AgriKafka topics.")
    parser.add_argument(
        "--bootstrap-server",
        default="127.0.0.1:9092",
        help="Kafka bootstrap server (default: 127.0.0.1:9092)",
    )
    parser.add_argument(
        "--scenario",
        choices=["corrupt_payload", "out_of_bounds_spike", "stuck_value"],
        default="corrupt_payload",
        help="Fault scenario to inject",
    )
    args = parser.parse_args()

    producer = Producer({"bootstrap.servers": args.bootstrap_server})
    now = datetime.now(timezone.utc).isoformat()

    if args.scenario == "corrupt_payload":
        # Missing numeric value and violation of canonical contract
        payload = {
            "event_id": str(uuid.uuid4()),
            "event_time": now,
            "field_id": "FIELD-KA-KOLAR-001",
            "sensor_id": "SENSOR-INJECTED-FAULT-001",
            "source_provider": "injected_test",
            "observed_variable": "ObservedVariable.TEMPERATURE_2M",
            "numeric_value": None,  # Intentionally null to trigger schema validation failure
            "unit": "StandardUnit.CELSIUS",
            "metadata": {"injected_fault": True, "reason": "professor_demo_dlq_test"},
        }
        topic = "agri.sensor-readings"
        key = "FIELD-KA-KOLAR-001:INJECTED"
        print(f"\n[DEMO] Injecting corrupt record into '{topic}' to demonstrate Dead-Letter Queue routing...")

    elif args.scenario == "out_of_bounds_spike":
        # Physical temperature spike impossible in Kolar (e.g. 85.0 Celsius)
        payload = {
            "event_id": str(uuid.uuid4()),
            "event_time": now,
            "ingestion_time": now,
            "field_id": "FIELD-KA-KOLAR-001",
            "sensor_id": "SENSOR-INJECTED-FAULT-002",
            "source_provider": "injected_test",
            "source_type": "physical_in_situ",
            "observed_variable": "ObservedVariable.TEMPERATURE_2M",
            "numeric_value": 85.0,  # Extreme spike violating physical agronomic bounds
            "unit": "StandardUnit.CELSIUS",
            "provenance": "synthetic_injected",
            "quality_flags": {"injected": True},
            "metadata": {"injected_fault": True, "reason": "spike_anomaly_test"},
        }
        topic = "agri.sensor-readings"
        key = "FIELD-KA-KOLAR-001:SPIKE"
        print(f"\n[DEMO] Injecting 85.0°C spike into '{topic}' to test sensor health anomaly detection...")

    elif args.scenario == "stuck_value":
        payload = {
            "event_id": str(uuid.uuid4()),
            "event_time": now,
            "ingestion_time": now,
            "field_id": "FIELD-KA-KOLAR-001",
            "sensor_id": "SENSOR-INJECTED-FAULT-003",
            "source_provider": "injected_test",
            "source_type": "physical_in_situ",
            "observed_variable": "ObservedVariable.RELATIVE_HUMIDITY_2M",
            "numeric_value": 100.0,
            "unit": "StandardUnit.PERCENT",
            "provenance": "synthetic_injected",
            "quality_flags": {"injected": True},
            "metadata": {"injected_fault": True, "reason": "stuck_value_test"},
        }
        topic = "agri.sensor-readings"
        key = "FIELD-KA-KOLAR-001:STUCK"
        print(f"\n[DEMO] Injecting flatline test record into '{topic}'...")

    producer.produce(
        topic=topic,
        key=key.encode("utf-8"),
        value=json.dumps(payload).encode("utf-8"),
        on_delivery=delivery_callback,
    )
    producer.flush(timeout=5)
    print("[DEMO] Fault injection complete. Check PySpark logs and DLQ topic.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

