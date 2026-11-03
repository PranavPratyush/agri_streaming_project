"""Streaming pipeline assembly and query execution for AgriKafka-Agent."""

from __future__ import annotations

import logging
from typing import Any
from pyspark.sql import SparkSession
from pyspark.sql.streaming import StreamingQuery

from agri_stream_processor.config import StreamProcessorConfig
from agri_stream_processor.metrics import AgriStreamingMetricsListener
from agri_stream_processor.schemas import get_observation_schema, get_weather_schema
from agri_stream_processor.transformations import (
    extract_dead_letter_records,
    extract_validated_observations,
    format_kafka_dlq_output,
    format_kafka_observation_output,
    parse_kafka_stream,
)

logger = logging.getLogger("agri_stream_processor.pipeline")


def create_spark_session(config: StreamProcessorConfig) -> SparkSession:
    """Build and initialize SparkSession configured for Kafka Structured Streaming in UTC."""
    builder = (
        SparkSession.builder
        .appName(config.spark_app_name)
        .master(config.spark_master)
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.streaming.checkpointLocation", config.checkpoint_dir.replace("\\", "/"))
        .config("spark.sql.adaptive.enabled", "false")  # Structured Streaming requires streaming-specific execution
    )

    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    if config.enable_metrics_listener:
        listener = AgriStreamingMetricsListener()
        spark.streams.addListener(listener)
        logger.info("Registered AgriStreamingMetricsListener with Spark streams.")

    return spark


def build_streaming_pipeline(
    spark: SparkSession,
    config: StreamProcessorConfig,
    sink_type: str = "kafka",
) -> list[StreamingQuery]:
    """Assemble and start the PySpark Structured Streaming pipeline.
    
    Supports sink_type="kafka" (production/container) or "memory"/"console" (testing).
    """
    logger.info(f"Connecting to Kafka at {config.kafka_bootstrap_servers}...")

    # 1. Read Raw Sensor Readings Stream
    raw_obs_stream = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", config.kafka_bootstrap_servers)
        .option("subscribe", config.topic_sensor_readings)
        .option("startingOffsets", config.starting_offsets)
        .option("failOnDataLoss", str(config.fail_on_data_loss).lower())
        .load()
    )

    # 2. Parse Canonical Contracts
    obs_schema = get_observation_schema()
    parsed_obs = parse_kafka_stream(raw_obs_stream, obs_schema)

    # 3. Separate Valid Telemetry from DLQ Candidates
    valid_obs = extract_validated_observations(parsed_obs, config.watermark_duration)
    dlq_records = extract_dead_letter_records(parsed_obs, config.topic_sensor_readings)

    # 4. Format Sinks
    active_queries: list[StreamingQuery] = []

    if sink_type == "kafka":
        # Sink A: Validated Observations -> agri.validated-observations
        kafka_valid_payload = format_kafka_observation_output(valid_obs)
        valid_query = (
            kafka_valid_payload.writeStream
            .queryName("query_validated_observations")
            .format("kafka")
            .option("kafka.bootstrap.servers", config.kafka_bootstrap_servers)
            .option("topic", config.topic_validated_observations)
            .option("checkpointLocation", config.get_query_checkpoint_path("validated_observations"))
            .trigger(processingTime=config.trigger_interval)
            .outputMode("append")
            .start()
        )
        active_queries.append(valid_query)
        logger.info(f"Started query '{valid_query.name}' writing to '{config.topic_validated_observations}'")

        # Sink B: Dead-Letter Queue -> agri.dead-letter-queue
        kafka_dlq_payload = format_kafka_dlq_output(dlq_records)
        dlq_query = (
            kafka_dlq_payload.writeStream
            .queryName("query_dead_letter_queue")
            .format("kafka")
            .option("kafka.bootstrap.servers", config.kafka_bootstrap_servers)
            .option("topic", config.topic_dead_letter_queue)
            .option("checkpointLocation", config.get_query_checkpoint_path("dead_letter_queue"))
            .trigger(processingTime=config.trigger_interval)
            .outputMode("append")
            .start()
        )
        active_queries.append(dlq_query)
        logger.info(f"Started query '{dlq_query.name}' writing to '{config.topic_dead_letter_queue}'")

    elif sink_type == "console":
        valid_query = (
            valid_obs.writeStream
            .queryName("console_validated_observations")
            .format("console")
            .option("truncate", "false")
            .trigger(processingTime=config.trigger_interval)
            .outputMode("append")
            .start()
        )
        active_queries.append(valid_query)

    return active_queries

