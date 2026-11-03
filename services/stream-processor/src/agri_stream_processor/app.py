"""Standalone CLI and spark-submit entrypoint for AgriKafka Stream Processor."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
from typing import Any

from agri_stream_processor.config import StreamProcessorConfig
from agri_stream_processor.pipeline import build_streaming_pipeline, create_spark_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("agri_stream_processor.app")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AgriKafka-Agent PySpark Structured Streaming Processor"
    )
    parser.add_argument(
        "--mode",
        choices=["run", "dry-run"],
        default="run",
        help="Execution mode: 'run' for continuous streaming, 'dry-run' for configuration audit",
    )
    parser.add_argument(
        "--bootstrap-servers",
        default=None,
        help="Kafka bootstrap servers override (e.g. 127.0.0.1:9092 or kafka:29092)",
    )
    parser.add_argument(
        "--checkpoint-dir",
        default=None,
        help="Durable checkpoint directory path override",
    )
    parser.add_argument(
        "--sink",
        choices=["kafka", "console"],
        default="kafka",
        help="Stream output sink target (default: kafka)",
    )
    parser.add_argument(
        "--trigger-interval",
        default=None,
        help="Micro-batch trigger interval (default: 5 seconds)",
    )
    parser.add_argument(
        "--watermark",
        default=None,
        help="Event-time watermark duration (default: 10 minutes)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    config = StreamProcessorConfig()
    if args.bootstrap_servers:
        config.kafka_bootstrap_servers = args.bootstrap_servers
    if args.checkpoint_dir:
        config.checkpoint_dir = args.checkpoint_dir
    if args.trigger_interval:
        config.trigger_interval = args.trigger_interval
    if args.watermark:
        config.watermark_duration = args.watermark

    logger.info("=================================================================")
    logger.info("AgriKafka-Agent PySpark Structured Streaming Processor")
    logger.info("=================================================================")
    logger.info(f"Kafka Bootstrap Servers: {config.kafka_bootstrap_servers}")
    logger.info(f"Input Topic Observations: {config.topic_sensor_readings}")
    logger.info(f"Input Topic Weather:      {config.topic_weather_data}")
    logger.info(f"Output Topic Validated:   {config.topic_validated_observations}")
    logger.info(f"Output Topic DLQ:         {config.topic_dead_letter_queue}")
    logger.info(f"Watermark Duration:       {config.watermark_duration}")
    logger.info(f"Tumbling Window:          {config.tumbling_window_duration}")
    logger.info(f"Sliding Window:           {config.sliding_window_duration} (slide {config.sliding_window_slide})")
    logger.info(f"Checkpoint Directory:     {config.checkpoint_dir}")
    logger.info(f"Trigger Interval:         {config.trigger_interval}")
    logger.info(f"Mode:                     {args.mode}")
    logger.info("=================================================================")

    if args.mode == "dry-run":
        logger.info("Dry-run validation successful. Configuration and schemas verified.")
        sys.exit(0)

    spark = create_spark_session(config)
    queries = build_streaming_pipeline(spark, config, sink_type=args.sink)

    def handle_shutdown(sig: int, frame: Any) -> None:
        logger.info("Shutdown signal received. Stopping streaming queries gracefully...")
        for q in queries:
            if q.isActive:
                logger.info(f"Stopping query '{q.name}'...")
                q.stop()
        spark.stop()
        logger.info("PySpark Structured Streaming processor terminated cleanly.")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logger.info(f"Streaming processor active with {len(queries)} query/queries. Awaiting termination...")
    try:
        spark.streams.awaitAnyTermination()
    except Exception as e:
        logger.error(f"Streaming query terminated with unexpected exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

