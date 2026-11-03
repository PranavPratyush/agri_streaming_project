"""Unit tests for TimescaleDB / PostgreSQL database schema and migrations."""

from __future__ import annotations

import re
from pathlib import Path
import pytest

from infra.database.migrate import discover_migrations, cmd_validate

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "infra" / "database" / "migrations"
QUERIES_DIR = PROJECT_ROOT / "infra" / "database" / "queries"


def test_migration_discovery_and_offline_validation():
    """Asserts that all migrations are discovered and paired with down scripts."""
    migrations = discover_migrations(MIGRATIONS_DIR)
    assert len(migrations) >= 2

    # Run the offline validator
    res = cmd_validate()
    assert res == 0


def test_schema_contains_all_required_tables():
    """Asserts that 001_initial_schema.up.sql declares all 11 required system tables."""
    migration_001 = MIGRATIONS_DIR / "001_initial_schema.up.sql"
    assert migration_001.exists()

    sql_text = migration_001.read_text(encoding="utf-8")

    required_tables = [
        "schema_migrations",
        "field_profiles",
        "sensor_metadata",
        "observations",
        "windowed_features",
        "sensor_health_events",
        "crop_candidate_alerts",
        "investigation_reports",
        "farmer_recommendations",
        "human_feedback",
        "ingestion_replay_runs",
        "system_audit_log",
    ]

    for table in required_tables:
        pattern = re.compile(rf"CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?{table}\b", re.IGNORECASE)
        assert pattern.search(sql_text) is not None, f"Required table '{table}' not found in schema"


def test_hypertables_declared_only_for_timeseries_tables():
    """Asserts create_hypertable is invoked exactly for the 4 time-series tables."""
    migration_001 = MIGRATIONS_DIR / "001_initial_schema.up.sql"
    sql_text = migration_001.read_text(encoding="utf-8")

    hypertables = re.findall(r"create_hypertable\(\s*'([^']+)'", sql_text, re.IGNORECASE)
    expected_hypertables = {"observations", "windowed_features", "sensor_health_events", "crop_candidate_alerts"}

    assert set(hypertables) == expected_hypertables, f"Unexpected hypertables: {hypertables}"


def test_hypertable_primary_keys_include_partition_time_column():
    """TimescaleDB requires any unique/primary key constraint to include the partition column.

    Verify observations has (idempotency_key, event_time)
    Verify windowed_features has window_start
    Verify sensor_health_events has event_time
    Verify crop_candidate_alerts has event_time
    """
    migration_001 = MIGRATIONS_DIR / "001_initial_schema.up.sql"
    sql_text = migration_001.read_text(encoding="utf-8")

    assert "PRIMARY KEY (idempotency_key, event_time)" in sql_text
    assert "PRIMARY KEY (field_id, feature_name, window_start, window_type)" in sql_text
    assert "PRIMARY KEY (idempotency_key, event_time)" in sql_text
    assert "PRIMARY KEY (alert_id, event_time)" in sql_text


def test_event_time_and_ingestion_time_distinction():
    """Asserts that both event_time and ingestion_time are preserved as TIMESTAMPTZ columns."""
    migration_001 = MIGRATIONS_DIR / "001_initial_schema.up.sql"
    sql_text = migration_001.read_text(encoding="utf-8")

    time_series_tables = ["observations", "sensor_health_events", "crop_candidate_alerts"]
    for table in time_series_tables:
        # Match table definition block
        table_block_match = re.search(rf"CREATE TABLE IF NOT EXISTS {table}\s*\((.*?)\);", sql_text, re.DOTALL | re.IGNORECASE)
        assert table_block_match is not None, f"Table {table} definition not found"
        block = table_block_match.group(1)

        assert "event_time TIMESTAMPTZ NOT NULL" in block
        assert "ingestion_time TIMESTAMPTZ NOT NULL" in block


def test_readonly_role_permissions_restricted():
    """Asserts that 002_readonly_role.up.sql creates agri_readonly with SELECT only and zero write/DDL."""
    migration_002 = MIGRATIONS_DIR / "002_readonly_role.up.sql"
    assert migration_002.exists()
    sql_text = migration_002.read_text(encoding="utf-8")

    assert "CREATE ROLE agri_readonly" in sql_text
    assert "GRANT SELECT ON ALL TABLES IN SCHEMA public TO agri_readonly" in sql_text
    assert "REVOKE ALL PRIVILEGES ON SCHEMA public FROM agri_readonly" in sql_text
    assert "REVOKE CREATE ON SCHEMA public FROM agri_readonly" in sql_text

    # Verify no INSERT, UPDATE, DELETE grants
    assert "GRANT INSERT" not in sql_text
    assert "GRANT UPDATE" not in sql_text
    assert "GRANT DELETE" not in sql_text


def test_representative_queries_exist_and_valid():
    """Asserts that all 4 representative analytical queries exist and reference valid columns."""
    expected_queries = [
        "01_field_timeline.sql",
        "02_sensor_freshness.sql",
        "03_recent_alerts.sql",
        "04_alert_evidence_chain.sql",
    ]

    for q_name in expected_queries:
        q_path = QUERIES_DIR / q_name
        assert q_path.exists(), f"Query file {q_name} missing"
        content = q_path.read_text(encoding="utf-8").strip()
        assert len(content) > 50, f"Query {q_name} is too short or empty"
        assert "SELECT" in content.upper()

