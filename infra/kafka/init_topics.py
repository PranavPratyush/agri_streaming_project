#!/usr/bin/env python3
"""Declarative topic provisioner for AgriKafka-Agent.

Provisions all canonical Kafka topics with explicit partitions, retention,
cleanup policies, and replication factors as code.
"""

import sys
import argparse
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import KafkaException

CORE_TOPICS = {
    "agri.sensor-readings": {
        "num_partitions": 3,
        "replication_factor": 1,
        "config": {
            "retention.ms": "604800000",  # 7 days
            "cleanup.policy": "delete",
        },
        "description": "Raw in-situ sensor telemetry and external station observations (Key: field_id)",
    },
    "agri.weather-data": {
        "num_partitions": 3,
        "replication_factor": 1,
        "config": {
            "retention.ms": "604800000",  # 7 days
            "cleanup.policy": "delete",
        },
        "description": "Gridded weather context and numerical forecasts (Key: field_id)",
    },
    "agri.validated-observations": {
        "num_partitions": 3,
        "replication_factor": 1,
        "config": {
            "retention.ms": "1209600000",  # 14 days
            "cleanup.policy": "delete",
        },
        "description": "PySpark streaming windowed, calibrated, and deduplicated observations (Key: field_id)",
    },
    "agri.sensor-health-events": {
        "num_partitions": 3,
        "replication_factor": 1,
        "config": {
            "retention.ms": "1209600000",  # 14 days
            "cleanup.policy": "compact,delete",
        },
        "description": "Sensor forensic diagnostics: stuck, spike, drift, dropout (Key: sensor_id)",
    },
    "agri.candidate-alerts": {
        "num_partitions": 3,
        "replication_factor": 1,
        "config": {
            "retention.ms": "2592000000",  # 30 days
            "cleanup.policy": "delete",
        },
        "description": "Deterministic numerical crop risk candidate alerts (Key: field_id)",
    },
    "agri.investigation-results": {
        "num_partitions": 3,
        "replication_factor": 1,
        "config": {
            "retention.ms": "2592000000",  # 30 days
            "cleanup.policy": "delete",
        },
        "description": "Bounded agent triage decisions, Kannada advisories, and approval tokens (Key: field_id)",
    },
    "agri.human-feedback": {
        "num_partitions": 3,
        "replication_factor": 1,
        "config": {
            "retention.ms": "7776000000",  # 90 days
            "cleanup.policy": "delete",
        },
        "description": "Farmer PWA approvals, overrides, and feedback (Key: field_id)",
    },
    "agri.dead-letter-queue": {
        "num_partitions": 3,
        "replication_factor": 1,
        "config": {
            "retention.ms": "2592000000",  # 30 days
            "cleanup.policy": "delete",
        },
        "description": "Malformed, unparseable, or out-of-range payloads isolated for forensics (Key: failed_topic)",
    },
    "agri.operational-metrics": {
        "num_partitions": 1,
        "replication_factor": 1,
        "config": {
            "retention.ms": "259200000",  # 3 days
            "cleanup.policy": "delete",
        },
        "description": "Streaming latency, consumer lag, and health heartbeats (Key: component_id)",
    },
}


def get_admin_client(bootstrap_servers: str) -> AdminClient:
    return AdminClient({
        "bootstrap.servers": bootstrap_servers,
        "client.id": "agrikafka-admin-init",
        "socket.timeout.ms": 5000,
    })


def inspect_topics(admin: AdminClient) -> None:
    print("\n--- Inspecting Kafka Cluster Topics ---")
    cluster_metadata = admin.list_topics(timeout=10)
    print(f"Brokers: {list(cluster_metadata.brokers.keys())}")
    print(f"Total topics present: {len(cluster_metadata.topics)}")
    
    for topic_name, topic_meta in cluster_metadata.topics.items():
        if topic_name.startswith("__"):
            continue  # Skip internal consumer offsets
        parts = topic_meta.partitions
        print(f"\nTopic: {topic_name}")
        print(f"  Partitions count: {len(parts)}")
        for pid, pmeta in parts.items():
            print(f"    Partition {pid}: Leader={pmeta.leader}, Replicas={pmeta.replicas}, ISR={pmeta.isrs}")


def provision_topics(admin: AdminClient) -> bool:
    print("--- Declaratively Provisioning AgriKafka Core Topics ---")
    cluster_metadata = admin.list_topics(timeout=10)
    existing_topics = set(cluster_metadata.topics.keys())
    
    new_topics = []
    for name, spec in CORE_TOPICS.items():
        if name in existing_topics:
            print(f"[EXISTS] Topic '{name}' already present ({len(cluster_metadata.topics[name].partitions)} partitions)")
        else:
            new_topics.append(
                NewTopic(
                    topic=name,
                    num_partitions=spec["num_partitions"],
                    replication_factor=spec["replication_factor"],
                    config=spec["config"],
                )
            )

    if not new_topics:
        print("\nAll canonical topics are already provisioned. Zero additions needed.")
        return True

    print(f"\nCreating {len(new_topics)} new topic(s)...")
    futures = admin.create_topics(new_topics)
    all_success = True
    for topic, f in futures.items():
        try:
            f.result()  # Blocks until topic is created
            print(f"[CREATED] '{topic}' successfully provisioned.")
        except KafkaException as e:
            print(f"[ERROR] Failed to create topic '{topic}': {e}")
            all_success = False

    return all_success


def main():
    parser = argparse.ArgumentParser(description="AgriKafka Declarative Topic Provisioner")
    parser.add_argument("--bootstrap-server", default="127.0.0.1:9092", help="Bootstrap broker address")
    parser.add_argument("--inspect-only", action="store_true", help="Inspect existing topics without creating")
    args = parser.parse_args()

    print(f"Connecting to Kafka AdminClient at {args.bootstrap_server}...")
    try:
        admin = get_admin_client(args.bootstrap_server)
        if args.inspect_only:
            inspect_topics(admin)
            return 0

        success = provision_topics(admin)
        inspect_topics(admin)
        return 0 if success else 1
    except Exception as e:
        print(f"Failed to connect to Kafka broker: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
