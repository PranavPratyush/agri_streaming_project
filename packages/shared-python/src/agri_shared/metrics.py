"""Standardized Prometheus metrics instruments and registry for AgriKafka-Agent.

Provides centralized Prometheus counters, gauges, histograms, and server utilities
covering ingestion, Kafka streaming, Spark processing, sensor health, crop risk,
agent investigation, database persistence, and human notifications.

Enforces strict low-cardinality labeling (no raw event IDs or timestamps).
"""

from __future__ import annotations

import logging
from typing import Optional

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    REGISTRY,
    generate_latest,
    start_http_server,
)

logger = logging.getLogger(__name__)

# =============================================================================
# 1. Ingestion Layer Metrics
# =============================================================================

INGESTION_RECORDS_TOTAL = Counter(
    "agri_ingestion_records_total",
    "Total number of observation records processed by ingestion adapters",
    ["adapter", "source_type", "status"],
)

INGESTION_REQUEST_DURATION_SECONDS = Histogram(
    "agri_ingestion_request_duration_seconds",
    "Latency of external telemetry polling requests in seconds",
    ["adapter", "endpoint"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

INGESTION_SOURCE_FRESHNESS_SECONDS = Gauge(
    "agri_ingestion_source_freshness_seconds",
    "Time delta in seconds between telemetry observation timestamp and platform ingestion",
    ["adapter", "station_id"],
)

INGESTION_RATE_LIMIT_HITS_TOTAL = Counter(
    "agri_ingestion_rate_limit_hits_total",
    "Total number of HTTP 429 rate limit responses encountered by ingestion adapters",
    ["adapter"],
)

INGESTION_ADAPTER_STATUS = Gauge(
    "agri_ingestion_adapter_status",
    "Operational state of the ingestion adapter (1=running, 0=stopped/failed)",
    ["adapter"],
)

# =============================================================================
# 2. Kafka Broker & Streaming Transport Metrics
# =============================================================================

KAFKA_MESSAGES_PRODUCED_TOTAL = Counter(
    "agri_kafka_messages_produced_total",
    "Total messages dispatched to Kafka topics by producer services",
    ["topic", "status"],
)

KAFKA_MESSAGES_CONSUMED_TOTAL = Counter(
    "agri_kafka_messages_consumed_total",
    "Total messages consumed from Kafka topics by consumer groups",
    ["topic", "consumer_group"],
)

KAFKA_CONSUMER_LAG_RECORDS = Gauge(
    "agri_kafka_consumer_lag_records",
    "Estimated consumer group offset lag across topic partitions",
    ["topic", "consumer_group", "partition"],
)

KAFKA_DLQ_MESSAGES_TOTAL = Counter(
    "agri_kafka_dlq_messages_total",
    "Total unparseable, malformed, or poisoned messages routed to Dead-Letter Queue",
    ["reason_code", "original_topic"],
)

KAFKA_BROKER_REACHABLE = Gauge(
    "agri_kafka_broker_reachable",
    "Health status of the Kafka KRaft broker (1=healthy, 0=unreachable)",
    ["broker_id"],
)

# =============================================================================
# 3. PySpark Structured Streaming Metrics
# =============================================================================

SPARK_INPUT_ROWS_TOTAL = Counter(
    "agri_spark_input_rows_total",
    "Total raw rows received by Spark Structured Streaming micro-batches",
    ["query_name", "topic"],
)

SPARK_PROCESSED_ROWS_TOTAL = Counter(
    "agri_spark_processed_rows_total",
    "Total validated rows successfully emitted from Spark transformations",
    ["query_name"],
)

SPARK_LATE_ROWS_DROPPED_TOTAL = Counter(
    "agri_spark_late_rows_dropped_total",
    "Total out-of-order events discarded by the Spark 10-minute watermark",
    ["query_name"],
)

SPARK_BATCH_DURATION_SECONDS = Histogram(
    "agri_spark_batch_duration_seconds",
    "Execution duration of PySpark micro-batches in seconds",
    ["query_name"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

SPARK_WATERMARK_TIMESTAMP_SECONDS = Gauge(
    "agri_spark_watermark_timestamp_seconds",
    "Current event-time watermark timestamp in seconds since epoch",
    ["query_name"],
)

SPARK_CHECKPOINT_COMMITS_TOTAL = Counter(
    "agri_spark_checkpoint_commits_total",
    "Total checkpoint commits recorded by Spark Structured Streaming",
    ["query_name", "status"],
)

# =============================================================================
# 4. Sensor Health & Data Quality Metrics
# =============================================================================

SENSOR_HEALTH_EVALUATIONS_TOTAL = Counter(
    "agri_sensor_health_evaluations_total",
    "Total forensic sensor health evaluations performed by deterministic engine",
    ["health_state", "reason_code"],
)

SENSOR_ACTIVE_HEALTH_STATE = Gauge(
    "agri_sensor_active_health_state",
    "Current health status code of active sensors (0=healthy, 1=stale, 2=suspect, 3=faulty, 4=unknown)",
    ["sensor_id", "variable"],
)

SENSOR_FLATLINE_EXEMPTIONS_TOTAL = Counter(
    "agri_sensor_flatline_exemptions_total",
    "Total natural flatline patterns correctly exempted from sensor fault alerts",
    ["exemption_type"],  # e.g., rain_zero_sequence, residual_soil_plateau, reanalysis_bypass
)

ADVISORY_SAFETY_GATE_BLOCKS_TOTAL = Counter(
    "agri_advisory_safety_gate_blocks_total",
    "Total times the agronomic safety gate blocked automated recommendation due to suspect/faulty sensors",
    ["reason_code"],
)

# =============================================================================
# 5. Crop Risk Modeling Engine Metrics
# =============================================================================

RISK_CANDIDATE_ALERTS_TOTAL = Counter(
    "agri_risk_candidate_alerts_total",
    "Total candidate crop risk alerts generated by the deterministic engine",
    ["risk_type", "severity", "growth_stage"],
)

RISK_SUPPRESSED_ALERTS_TOTAL = Counter(
    "agri_risk_suppressed_alerts_total",
    "Total candidate risk alerts suppressed due to sensor faults or incomplete crop profiles",
    ["risk_type", "suppression_reason"],
)

RISK_COMPOSITE_STRESS_INDEX = Gauge(
    "agri_risk_composite_stress_index",
    "Current Composite Crop Stress Index (CSI) for field parcels (0.0 to 1.0)",
    ["field_id"],
)

RISK_EVALUATION_DURATION_SECONDS = Histogram(
    "agri_risk_evaluation_duration_seconds",
    "Duration of deterministic crop risk calculations in seconds",
    ["rule_type"],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05),
)

# =============================================================================
# 6. Bounded Investigator Agent Metrics
# =============================================================================

INVESTIGATOR_INVOCATIONS_TOTAL = Counter(
    "agri_investigator_invocations_total",
    "Total alert investigation sessions initiated by the bounded agent",
    ["status", "model"],
)

INVESTIGATOR_TOOL_CALLS_TOTAL = Counter(
    "agri_investigator_tool_calls_total",
    "Total read-only tool calls executed by the bounded investigator",
    ["tool_name", "status"],
)

INVESTIGATOR_DURATION_SECONDS = Histogram(
    "agri_investigator_duration_seconds",
    "Total investigation turnaround time in seconds",
    ["model"],
    buckets=(0.5, 1.0, 2.0, 4.0, 8.0, 15.0),
)

INVESTIGATOR_TOKEN_USAGE_TOTAL = Counter(
    "agri_investigator_token_usage_total",
    "Total LLM tokens consumed during alert investigations",
    ["token_type", "model"],  # token_type: prompt, completion
)

INVESTIGATOR_FALLBACK_RATE_TOTAL = Counter(
    "agri_investigator_fallback_rate_total",
    "Total times the agent fell back to deterministic rule engine",
    ["fallback_reason"],
)

# =============================================================================
# 7. Database & Persistence Layer Metrics
# =============================================================================

DB_POOL_CONNECTIONS = Gauge(
    "agri_db_pool_connections",
    "TimescaleDB connection pool status",
    ["state"],  # active, idle, waiting
)

DB_UPSERT_OPERATIONS_TOTAL = Counter(
    "agri_db_upsert_operations_total",
    "Total database persistence operations categorized by table and resolution",
    ["table", "operation"],  # operation: inserted, duplicate_skipped, updated
)

DB_QUERY_DURATION_SECONDS = Histogram(
    "agri_db_query_duration_seconds",
    "Execution duration of database analytical queries in seconds",
    ["query_name"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.5, 1.0),
)

DB_HEALTH = Gauge(
    "agri_db_health",
    "Health status of the TimescaleDB / PostgreSQL database (1=healthy, 0=unhealthy)",
    ["database"],
)

# =============================================================================
# 8. Notification & Human Feedback Metrics
# =============================================================================

NOTIFICATION_ATTEMPTS_TOTAL = Counter(
    "agri_notification_attempts_total",
    "Total outbound advisory notification attempts",
    ["channel", "status"],  # channel: telegram, in_app, sms
)

NOTIFICATION_DEDUPLICATIONS_TOTAL = Counter(
    "agri_notification_deduplications_total",
    "Total duplicate notifications suppressed within cooldown window",
    ["channel"],
)

HUMAN_FEEDBACK_TOTAL = Counter(
    "agri_human_feedback_total",
    "Total farmer / agronomist decision responses recorded",
    ["action_taken", "rating"],
)


# =============================================================================
# Exporter HTTP Server Utility
# =============================================================================

def start_metrics_server_safe(port: int, addr: str = "0.0.0.0", registry: CollectorRegistry = REGISTRY) -> bool:
    """Safely starts a Prometheus metrics HTTP server on the specified port.

    Returns True if successfully started, False if port is already in use or error occurs.
    """
    try:
        start_http_server(port, addr=addr, registry=registry)
        logger.info("Prometheus metrics server successfully started on %s:%s/metrics", addr, port)
        return True
    except OSError as err:
        logger.warning("Could not bind metrics server to %s:%s (might already be running): %s", addr, port, err)
        return False
    except Exception as err:
        logger.error("Failed to start metrics server on port %s: %s", port, err)
        return False


def get_metrics_payload(registry: CollectorRegistry = REGISTRY) -> bytes:
    """Returns the current Prometheus metrics payload as bytes in exposition text format."""
    return generate_latest(registry)

