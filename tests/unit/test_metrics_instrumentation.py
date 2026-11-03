"""Unit tests for AgriKafka-Agent centralized Prometheus metrics instrumentation."""

from __future__ import annotations

import pytest
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

from agri_shared.metrics import (
    INGESTION_RECORDS_TOTAL,
    INGESTION_REQUEST_DURATION_SECONDS,
    INGESTION_SOURCE_FRESHNESS_SECONDS,
    INGESTION_RATE_LIMIT_HITS_TOTAL,
    INGESTION_ADAPTER_STATUS,
    KAFKA_MESSAGES_PRODUCED_TOTAL,
    KAFKA_MESSAGES_CONSUMED_TOTAL,
    KAFKA_CONSUMER_LAG_RECORDS,
    KAFKA_DLQ_MESSAGES_TOTAL,
    KAFKA_BROKER_REACHABLE,
    SPARK_INPUT_ROWS_TOTAL,
    SPARK_PROCESSED_ROWS_TOTAL,
    SPARK_LATE_ROWS_DROPPED_TOTAL,
    SPARK_BATCH_DURATION_SECONDS,
    SPARK_WATERMARK_TIMESTAMP_SECONDS,
    SPARK_CHECKPOINT_COMMITS_TOTAL,
    SENSOR_HEALTH_EVALUATIONS_TOTAL,
    SENSOR_ACTIVE_HEALTH_STATE,
    SENSOR_FLATLINE_EXEMPTIONS_TOTAL,
    ADVISORY_SAFETY_GATE_BLOCKS_TOTAL,
    RISK_CANDIDATE_ALERTS_TOTAL,
    RISK_SUPPRESSED_ALERTS_TOTAL,
    RISK_COMPOSITE_STRESS_INDEX,
    RISK_EVALUATION_DURATION_SECONDS,
    INVESTIGATOR_INVOCATIONS_TOTAL,
    INVESTIGATOR_TOOL_CALLS_TOTAL,
    INVESTIGATOR_DURATION_SECONDS,
    INVESTIGATOR_TOKEN_USAGE_TOTAL,
    INVESTIGATOR_FALLBACK_RATE_TOTAL,
    DB_POOL_CONNECTIONS,
    DB_UPSERT_OPERATIONS_TOTAL,
    DB_QUERY_DURATION_SECONDS,
    DB_HEALTH,
    NOTIFICATION_ATTEMPTS_TOTAL,
    NOTIFICATION_DEDUPLICATIONS_TOTAL,
    HUMAN_FEEDBACK_TOTAL,
    get_metrics_payload,
    start_metrics_server_safe,
)

FORBIDDEN_CARDINALITY_LABELS = {
    "event_id",
    "idempotency_key",
    "alert_id",
    "record_id",
    "timestamp",
    "time",
    "uuid",
    "raw_payload",
    "hash",
}


def test_metric_instruments_no_high_cardinality_labels():
    """Verify all defined metric instruments strictly forbid high-cardinality label keys."""
    all_metrics = [
        INGESTION_RECORDS_TOTAL,
        INGESTION_REQUEST_DURATION_SECONDS,
        INGESTION_SOURCE_FRESHNESS_SECONDS,
        INGESTION_RATE_LIMIT_HITS_TOTAL,
        INGESTION_ADAPTER_STATUS,
        KAFKA_MESSAGES_PRODUCED_TOTAL,
        KAFKA_MESSAGES_CONSUMED_TOTAL,
        KAFKA_CONSUMER_LAG_RECORDS,
        KAFKA_DLQ_MESSAGES_TOTAL,
        KAFKA_BROKER_REACHABLE,
        SPARK_INPUT_ROWS_TOTAL,
        SPARK_PROCESSED_ROWS_TOTAL,
        SPARK_LATE_ROWS_DROPPED_TOTAL,
        SPARK_BATCH_DURATION_SECONDS,
        SPARK_WATERMARK_TIMESTAMP_SECONDS,
        SPARK_CHECKPOINT_COMMITS_TOTAL,
        SENSOR_HEALTH_EVALUATIONS_TOTAL,
        SENSOR_ACTIVE_HEALTH_STATE,
        SENSOR_FLATLINE_EXEMPTIONS_TOTAL,
        ADVISORY_SAFETY_GATE_BLOCKS_TOTAL,
        RISK_CANDIDATE_ALERTS_TOTAL,
        RISK_SUPPRESSED_ALERTS_TOTAL,
        RISK_COMPOSITE_STRESS_INDEX,
        RISK_EVALUATION_DURATION_SECONDS,
        INVESTIGATOR_INVOCATIONS_TOTAL,
        INVESTIGATOR_TOOL_CALLS_TOTAL,
        INVESTIGATOR_DURATION_SECONDS,
        INVESTIGATOR_TOKEN_USAGE_TOTAL,
        INVESTIGATOR_FALLBACK_RATE_TOTAL,
        DB_POOL_CONNECTIONS,
        DB_UPSERT_OPERATIONS_TOTAL,
        DB_QUERY_DURATION_SECONDS,
        DB_HEALTH,
        NOTIFICATION_ATTEMPTS_TOTAL,
        NOTIFICATION_DEDUPLICATIONS_TOTAL,
        HUMAN_FEEDBACK_TOTAL,
    ]

    for metric in all_metrics:
        labelnames = set(metric._labelnames)
        intersection = labelnames.intersection(FORBIDDEN_CARDINALITY_LABELS)
        assert not intersection, f"Metric {metric._name} contains forbidden high-cardinality labels: {intersection}"


def test_metrics_instrumentation_updates():
    """Verify that metric instruments can be recorded without exception."""
    # Ingestion
    INGESTION_RECORDS_TOTAL.labels(adapter="open_meteo", source_type="external_station", status="success").inc()
    INGESTION_SOURCE_FRESHNESS_SECONDS.labels(adapter="open_meteo", station_id="kolar_central").set(42.5)

    # Kafka
    KAFKA_MESSAGES_PRODUCED_TOTAL.labels(topic="agri.raw.telemetry", status="success").inc()
    KAFKA_CONSUMER_LAG_RECORDS.labels(topic="agri.raw.telemetry", consumer_group="spark-processor", partition="0").set(15)

    # Spark
    SPARK_INPUT_ROWS_TOTAL.labels(query_name="canonical_cleaner", topic="agri.raw.telemetry").inc(10)
    SPARK_BATCH_DURATION_SECONDS.labels(query_name="canonical_cleaner").observe(0.45)

    # Sensor health
    SENSOR_HEALTH_EVALUATIONS_TOTAL.labels(health_state="HEALTHY", reason_code="NOMINAL").inc()
    SENSOR_FLATLINE_EXEMPTIONS_TOTAL.labels(exemption_type="rain_zero_sequence").inc()

    # Risk
    RISK_CANDIDATE_ALERTS_TOTAL.labels(risk_type="moisture_stress", severity="high", growth_stage="flowering").inc()
    RISK_COMPOSITE_STRESS_INDEX.labels(field_id="kolar_field_001").set(0.65)

    # Database
    DB_POOL_CONNECTIONS.labels(state="active").set(3)
    DB_UPSERT_OPERATIONS_TOTAL.labels(table="observations", operation="inserted").inc(5)

    # Payload generation
    payload = get_metrics_payload()
    assert isinstance(payload, bytes)
    assert len(payload) > 0
    text_content = payload.decode("utf-8")
    assert "agri_ingestion_records_total" in text_content
    assert "agri_spark_batch_duration_seconds" in text_content
    assert "agri_risk_composite_stress_index" in text_content


def test_custom_registry_isolation():
    """Verify that custom registries can be passed to payload functions."""
    reg = CollectorRegistry()
    custom_c = Counter("custom_test_counter", "Custom test counter", registry=reg)
    custom_c.inc(3)

    payload = get_metrics_payload(registry=reg)
    text = payload.decode("utf-8")
    assert "custom_test_counter_total 3.0" in text


def test_start_metrics_server_safe(monkeypatch):
    """Verify safe metrics server startup catches errors properly."""
    # When start_http_server raises an OSError (e.g. port bound)
    def mock_start_error(port, addr, registry):
        raise OSError(f"Port {port} in use")

    monkeypatch.setattr("agri_shared.metrics.start_http_server", mock_start_error)
    success = start_metrics_server_safe(port=9999, addr="127.0.0.1")
    assert success is False
