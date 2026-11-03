"""Configuration management for AgriKafka-Agent PySpark Structured Streaming Processor."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path


@dataclass
class StreamProcessorConfig:
    """Configuration settings for PySpark Structured Streaming service."""

    # Kafka Connection
    kafka_bootstrap_servers: str = field(
        default_factory=lambda: os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092")
    )

    # Input Topics
    topic_sensor_readings: str = field(
        default_factory=lambda: os.getenv("KAFKA_TOPIC_SENSOR_READINGS", "agri.sensor-readings")
    )
    topic_weather_data: str = field(
        default_factory=lambda: os.getenv("KAFKA_TOPIC_WEATHER_DATA", "agri.weather-data")
    )

    # Output Topics
    topic_validated_observations: str = field(
        default_factory=lambda: os.getenv(
            "KAFKA_TOPIC_VALIDATED_OBSERVATIONS", "agri.validated-observations"
        )
    )
    topic_dead_letter_queue: str = field(
        default_factory=lambda: os.getenv(
            "KAFKA_TOPIC_DEAD_LETTER_QUEUE", "agri.dead-letter-queue"
        )
    )

    # Streaming Window & Watermark Parameters
    watermark_duration: str = field(
        default_factory=lambda: os.getenv("SPARK_WATERMARK_DURATION", "10 minutes")
    )
    tumbling_window_duration: str = field(
        default_factory=lambda: os.getenv("SPARK_TUMBLING_WINDOW", "5 minutes")
    )
    sliding_window_duration: str = field(
        default_factory=lambda: os.getenv("SPARK_SLIDING_WINDOW_DURATION", "30 minutes")
    )
    sliding_window_slide: str = field(
        default_factory=lambda: os.getenv("SPARK_SLIDING_WINDOW_SLIDE", "5 minutes")
    )
    weather_join_tolerance: str = field(
        default_factory=lambda: os.getenv("SPARK_WEATHER_JOIN_TOLERANCE", "15 minutes")
    )

    # Execution Parameters
    trigger_interval: str = field(
        default_factory=lambda: os.getenv("SPARK_TRIGGER_INTERVAL", "5 seconds")
    )
    starting_offsets: str = field(
        default_factory=lambda: os.getenv("SPARK_STARTING_OFFSETS", "latest")
    )
    fail_on_data_loss: bool = field(
        default_factory=lambda: os.getenv("SPARK_FAIL_ON_DATA_LOSS", "false").lower() == "true"
    )

    # Checkpointing & Durability
    checkpoint_dir: str = field(
        default_factory=lambda: os.getenv(
            "SPARK_CHECKPOINT_DIR", str(Path("infra/spark/checkpoints").resolve())
        )
    )

    # Spark Runtime
    spark_master: str = field(
        default_factory=lambda: os.getenv("SPARK_MASTER", "local[*]")
    )
    spark_app_name: str = field(
        default_factory=lambda: os.getenv("SPARK_APP_NAME", "AgriKafka-StreamProcessor")
    )
    enable_metrics_listener: bool = field(
        default_factory=lambda: os.getenv("SPARK_ENABLE_METRICS_LISTENER", "true").lower() == "true"
    )

    def get_query_checkpoint_path(self, query_name: str) -> str:
        """Return dedicated subfolder for a specific streaming query checkpoint."""
        # Convert Windows backslashes to forward slashes for Spark URI compatibility
        base = self.checkpoint_dir.replace("\\", "/")
        return f"{base}/{query_name}"

