#!/usr/bin/env bash
# AgriKafka-Agent Local Kafka Infrastructure Management Script (POSIX / Bash)
set -eo pipefail

ACTION="${1:-status}"

echo "=========================================================="
echo " AgriKafka-Agent — Kafka Infrastructure Manager (Bash)"
echo "=========================================================="

case "$ACTION" in
    start)
        echo "[STARTING] Launching Kafka KRaft container..."
        docker compose up -d kafka
        echo "Waiting for Kafka broker to report healthy on port 9092..."
        sleep 10
        docker compose ps kafka
        echo -e "\nBroker is starting. To provision topics, run: ./infra/kafka/manage.sh topics-init"
        ;;
    status)
        echo "[STATUS] Inspecting Kafka container and health..."
        docker compose ps kafka
        ;;
    topics-init)
        echo "[TOPICS] Declaratively provisioning AgriKafka core topics..."
        uv run python infra/kafka/init_topics.py --bootstrap-server 127.0.0.1:9092
        ;;
    topics-list)
        echo "[INSPECT] Listing all topics, partitions, and replication..."
        uv run python infra/kafka/init_topics.py --bootstrap-server 127.0.0.1:9092 --inspect-only
        ;;
    smoke-test)
        echo "[SMOKE TEST] Running end-to-end producer-consumer verification..."
        uv run python infra/kafka/smoke_test.py 127.0.0.1:9092
        ;;
    persist-test)
        echo "[PERSISTENCE DRILL] Verifying volume persistence across container restart..."
        uv run python infra/kafka/verify_persistence.py 127.0.0.1:9092
        ;;
    stop)
        echo "[STOPPING] Gracefully stopping Kafka container (Volume retained)..."
        docker compose stop kafka
        echo "Kafka stopped. Data is preserved in volume 'agrikafka_dev_data'."
        ;;
    down)
        echo "[DOWN] Stopping and removing container (Volume retained)..."
        docker compose down
        echo "Container removed. Volume 'agrikafka_dev_data' was NOT deleted."
        ;;
    *)
        echo "Usage: $0 {start|status|topics-init|topics-list|smoke-test|persist-test|stop|down}"
        exit 1
        ;;
esac
