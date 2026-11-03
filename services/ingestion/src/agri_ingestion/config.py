"""Configuration settings for the AgriKafka-Agent Ingestion Service."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class IngestionConfig:
    """Runtime configuration for ingestion adapters and Kafka publisher."""

    # Kafka Broker Configuration
    bootstrap_servers: str = field(
        default_factory=lambda: os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092")
    )

    # Canonical Topic Names (adheres to Stage 8 agri.<domain-slug> standard)
    topic_raw_observations: str = field(
        default_factory=lambda: os.getenv("KAFKA_TOPIC_RAW_OBSERVATIONS", "agri.sensor-readings")
    )
    topic_weather_data: str = field(
        default_factory=lambda: os.getenv("KAFKA_TOPIC_WEATHER_DATA", "agri.weather-data")
    )
    topic_dead_letter: str = field(
        default_factory=lambda: os.getenv("KAFKA_TOPIC_DEAD_LETTER", "agri.dead-letter-queue")
    )
    topic_operational_metrics: str = field(
        default_factory=lambda: os.getenv("KAFKA_TOPIC_OPERATIONAL_METRICS", "agri.operational-metrics")
    )

    # openSenseMap Live Station Settings
    osm_base_url: str = "https://api.opensensemap.org"
    osm_primary_station_id: str = field(
        default_factory=lambda: os.getenv("OPENSENSEMAP_STATION_ID", "689b2bdc569c2d0007586ae9")
    )
    osm_fallback_station_id: str = "68a93536e035980007f6036b"
    osm_poll_interval_sec: float = 30.0
    osm_request_timeout_sec: float = 5.0
    osm_max_retries: int = 3
    osm_backoff_base_sec: float = 1.0
    osm_backoff_max_sec: float = 30.0

    # Open-Meteo Weather Context Settings
    openmeteo_api_url: str = "https://api.open-meteo.com/v1/forecast"
    openmeteo_poll_interval_sec: float = 900.0  # 15 minutes
    openmeteo_request_timeout_sec: float = 8.0
    openmeteo_kolar_lat: float = 13.137
    openmeteo_kolar_lon: float = 78.129
    openmeteo_elevation_m: float = 822.0
    default_field_id: str = "FIELD-KA-KOLAR-001"

    # Historical Replay Settings
    historical_csv_path: str = "data/open_meteo_karnataka_2024-10-05_to_2026-10-04.csv"
    default_replay_speed_multiplier: float = 3600.0  # 1 hr simulated per second by default

    # Idempotent Kafka Producer Settings
    producer_acks: str = "all"
    producer_enable_idempotence: bool = True
    producer_retries: int = 5
    producer_max_in_flight: int = 5
    producer_linger_ms: int = 10

