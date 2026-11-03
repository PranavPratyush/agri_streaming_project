"""CLI entrypoint to run the AgriKafka-Agent Kafka-to-TimescaleDB persistence sink."""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
from pathlib import Path

# Ensure local packages are importable
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "packages" / "database-client" / "src"))
sys.path.insert(0, str(REPO_ROOT / "packages" / "event-contracts" / "src"))

from agri_persistence.config import DatabaseConfig
from agri_persistence.pool import DatabasePoolManager
from agri_persistence.repository import PersistenceRepository
from agri_persistence.consumer import KafkaDatabaseConsumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("agri_persistence_sink")


def main() -> int:
    parser = argparse.ArgumentParser(description="AgriKafka-Agent Kafka-to-TimescaleDB Persistence Sink")
    parser.add_argument("--bootstrap-servers", default=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092"))
    parser.add_argument("--group-id", default=os.environ.get("KAFKA_CONSUMER_GROUP_PREFIX", "agri-timescale-sink-group"))
    parser.add_argument("--mock-mode", action="store_true", help="Run without live Kafka broker")
    parser.add_argument("--max-messages", type=int, default=None, help="Max messages to consume before exiting")

    args = parser.parse_args()

    db_config = DatabaseConfig()
    pool_mgr = DatabasePoolManager(db_config)
    repo = PersistenceRepository(pool_mgr)
    consumer = KafkaDatabaseConsumer(
        repository=repo,
        bootstrap_servers=args.bootstrap_servers,
        group_id=args.group_id,
        mock_mode=args.mock_mode,
    )

    def handle_signal(sig, frame):
        logger.info("Received shutdown signal %s. Stopping consumer gracefully...", sig)
        consumer.close()
        pool_mgr.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    logger.info("Starting persistence sink connecting to %s...", args.bootstrap_servers)
    try:
        consumer.run(max_messages=args.max_messages)
    except Exception as e:
        logger.error("Consumer terminated with error: %s", e)
        return 1
    finally:
        consumer.close()
        pool_mgr.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())

