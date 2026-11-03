"""Integration tests for TimescaleDB / PostgreSQL persistence, idempotency, and query execution."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest

from agri_contracts.enums import (
    ObservedVariable,
    StandardUnit,
    ProvenanceClass,
    HealthState,
    SensorHealthFlag,
    CropRiskLevel,
)
from agri_contracts.models.base import ProvenanceMetadata
from agri_contracts.models.observation import AgriObservationEvent
from agri_contracts.models.sensor_health import SensorHealthResultEvent
from agri_contracts.models.crop_risk import CropRiskCandidateAlertEvent
from agri_persistence.config import DatabaseConfig, ReadOnlyDatabaseConfig
from agri_persistence.pool import DatabasePoolManager
from agri_persistence.repository import PersistenceRepository
from agri_persistence.consumer import KafkaDatabaseConsumer


def test_database_config_conninfo():
    """Asserts that DatabaseConfig and ReadOnlyDatabaseConfig format valid connection URLs."""
    cfg = DatabaseConfig(
        host="127.0.0.1",
        port=5432,
        dbname="agrikafka",
        user="agri_admin",
        password="test_password",
    )
    assert cfg.conninfo == "postgresql://agri_admin:test_password@127.0.0.1:5432/agrikafka"

    ro_cfg = ReadOnlyDatabaseConfig(
        host="127.0.0.1",
        port=5432,
        dbname="agrikafka",
        user="agri_readonly",
        password="ro_password",
    )
    assert ro_cfg.conninfo == "postgresql://agri_readonly:ro_password@127.0.0.1:5432/agrikafka"


class MockCursor:
    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.rowcount = 0
        self._cur = db.cursor()

    def execute(self, sql_query: str, params: dict | tuple = None):
        # Convert PostgreSQL %(name)s syntax and ON CONFLICT to SQLite compatibility
        q = sql_query.replace("%(", ":").replace(")s", "")
        q = q.replace("now()", "CURRENT_TIMESTAMP")
        q = q.replace("::jsonb", "")
        # Strip Timescale-specific INTERVAL arithmetic if present in simple tests
        try:
            if params is None:
                self._cur.execute(q)
            else:
                # Convert any Jsonb or dicts to strings for SQLite
                clean_params = {}
                for k, v in params.items():
                    if isinstance(v, (dict, list)):
                        clean_params[k] = json.dumps(v)
                    elif hasattr(v, "obj"):
                        clean_params[k] = json.dumps(v.obj)
                    elif hasattr(v, "adapted"):
                        clean_params[k] = json.dumps(v.adapted)
                    elif str(type(v)).find("Jsonb") != -1:
                        # Fallback for psycopg Jsonb
                        clean_params[k] = json.dumps(getattr(v, "obj", {}))
                    elif isinstance(v, datetime):
                        clean_params[k] = v.isoformat()
                    else:
                        clean_params[k] = v
                self._cur.execute(q, clean_params)
            self.rowcount = self._cur.rowcount
        except sqlite3.IntegrityError:
            # Emulates ON CONFLICT DO NOTHING
            self.rowcount = 0

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class MockConnection:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def cursor(self):
        return MockCursor(self.db)

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def sqlite_repo():
    """Sets up an in-memory SQLite schema emulating PostgreSQL tables for unit testing idempotency."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE field_profiles (
        field_id TEXT PRIMARY KEY,
        name TEXT, latitude REAL, longitude REAL, elevation_m REAL,
        crop_name TEXT, variety TEXT, sowing_date TEXT, expected_harvest_date TEXT,
        current_growth_stage TEXT, soil_type TEXT, soil_texture TEXT,
        field_capacity REAL, wilting_point REAL, root_zone_depth_m REAL,
        irrigation_type TEXT, is_active INTEGER, metadata TEXT,
        created_at TEXT, updated_at TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE sensor_metadata (
        sensor_id TEXT PRIMARY KEY, field_id TEXT, sensor_model TEXT,
        manufacturer TEXT, measured_variable TEXT, unit TEXT,
        installation_date TEXT, depth_m REAL, sampling_interval_seconds INTEGER,
        provenance_type TEXT, is_active INTEGER, metadata TEXT,
        created_at TEXT, updated_at TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE observations (
        idempotency_key TEXT, event_id TEXT, event_time TEXT, ingestion_time TEXT,
        field_id TEXT, sensor_id TEXT, source_provider TEXT, source_type TEXT,
        observed_variable TEXT, numeric_value REAL, unit TEXT,
        latitude REAL, longitude REAL, elevation REAL, sensor_depth_m REAL,
        provenance TEXT, quality_flags TEXT, metadata TEXT, created_at TEXT,
        PRIMARY KEY (idempotency_key, event_time)
    );
    """)

    cur.execute("""
    CREATE TABLE sensor_health_events (
        idempotency_key TEXT, event_id TEXT, sensor_id TEXT, field_id TEXT,
        event_time TEXT, ingestion_time TEXT, health_state TEXT,
        reason_code TEXT, reason_description TEXT, is_usable_for_advisory INTEGER,
        metrics TEXT, evidence TEXT, created_at TEXT,
        PRIMARY KEY (idempotency_key, event_time)
    );
    """)

    cur.execute("""
    CREATE TABLE crop_candidate_alerts (
        alert_id TEXT, field_id TEXT, event_time TEXT, ingestion_time TEXT,
        alert_type TEXT, severity TEXT, status TEXT, composite_stress_index REAL,
        fao56_depletion_fraction REAL, blast_risk_score REAL, thermal_stress_score REAL,
        sensor_health_state TEXT, uncertainty_score REAL, contributing_features TEXT,
        evidence TEXT, suppression_reason TEXT, created_at TEXT,
        PRIMARY KEY (alert_id, event_time)
    );
    """)

    conn.commit()

    mock_pool = MagicMock()
    mock_pool.connection.return_value = MockConnection(conn)

    repo = PersistenceRepository(mock_pool)
    return repo, conn


def test_idempotent_observation_writes_prevent_duplicates(sqlite_repo):
    """Asserts that duplicate observation events with identical idempotency_key are safely ignored."""
    repo, conn = sqlite_repo

    event_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc)
    obs = AgriObservationEvent(
        event_id=event_id,
        event_time=now_iso,
        field_id="field-kolar-ragi-01",
        idempotency_key=f"obs-{event_id}",
        sensor_id="osm-sarvamangalam-temp",
        source_provider="openSenseMap",
        variable=ObservedVariable.TEMPERATURE_2M,
        value=27.4,
        unit=StandardUnit.CELSIUS,
        provenance=ProvenanceMetadata(
            provenance_class=ProvenanceClass.PHYSICAL_SENSOR,
            dataset_origin="openSenseMap",
            is_synthetic=False,
        ),
    )

    # 1. First write must succeed (insert 1 row)
    first_result = repo.upsert_observation(obs)
    assert first_result is True

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM observations;")
    assert cur.fetchone()[0] == 1

    # 2. Second write with identical event must trigger ON CONFLICT DO NOTHING (return False, 0 rows added)
    second_result = repo.upsert_observation(obs)
    assert second_result is False

    cur.execute("SELECT COUNT(*) FROM observations;")
    assert cur.fetchone()[0] == 1, "Duplicate observation was erroneously inserted!"


def test_consumer_prevents_duplicate_persisted_records(sqlite_repo):
    """Tests that KafkaDatabaseConsumer properly tracks duplicates_prevented and persists effectively-once."""
    repo, conn = sqlite_repo
    consumer = KafkaDatabaseConsumer(repository=repo, mock_mode=True)

    event_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    obs_payload = json.dumps({
        "event_id": event_id,
        "event_time": now_iso,
        "ingestion_time": now_iso,
        "idempotency_key": f"obs-{event_id}",
        "field_id": "field-kolar-ragi-01",
        "sensor_id": "probe-soil-01",
        "source_provider": "FarmerEdgeMock",
        "variable": "soil_moisture_0_to_7cm",
        "value": 0.145,
        "unit": "m3_per_m3",
        "provenance": {
            "provenance_class": "physical_sensor",
            "dataset_origin": "FarmerEdgeMock",
            "is_synthetic": False,
        },
    })

    # Message 1
    res1 = consumer.process_message_payload("agri.validated-observations", obs_payload)
    assert res1 is True
    assert consumer.messages_persisted == 1
    assert consumer.duplicates_prevented == 0

    # Message 2 (exact duplicate redelivery)
    res2 = consumer.process_message_payload("agri.validated-observations", obs_payload)
    assert res2 is False
    assert consumer.messages_persisted == 1
    assert consumer.duplicates_prevented == 1

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM observations;")
    assert cur.fetchone()[0] == 1


def test_idempotent_sensor_health_writes(sqlite_repo):
    """Asserts that duplicate sensor health result events are safely deduplicated."""
    repo, conn = sqlite_repo

    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    health_evt = SensorHealthResultEvent(
        event_id=event_id,
        idempotency_key=f"sh-{event_id}",
        sensor_id="osm-sarvamangalam-rain",
        field_id="field-kolar-ragi-01",
        event_time=now,
        variable=ObservedVariable.PRECIPITATION,
        health_flag=SensorHealthFlag.HEALTHY,
        health_state=HealthState.HEALTHY,
        reason_code="NOMINAL",
        confidence_score=1.0,
        is_usable_for_advisory=True,
        provenance=ProvenanceMetadata(
            provenance_class=ProvenanceClass.PHYSICAL_SENSOR,
            dataset_origin="openSenseMap",
            is_synthetic=False,
        ),
    )

    assert repo.upsert_sensor_health_event(health_evt) is True
    assert repo.upsert_sensor_health_event(health_evt) is False

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM sensor_health_events;")
    assert cur.fetchone()[0] == 1


def test_idempotent_crop_candidate_alert_writes(sqlite_repo):
    """Asserts that duplicate candidate alert events are handled safely."""
    repo, conn = sqlite_repo

    alert_id = str(uuid.uuid4())
    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    alert_evt = CropRiskCandidateAlertEvent(
        event_id=event_id,
        idempotency_key=f"alert-{alert_id}",
        alert_id=alert_id,
        field_id="field-kolar-ragi-01",
        event_time=now,
        growth_stage="flowering",
        risk_type="SOIL_MOISTURE_DEFICIT",
        risk_level=CropRiskLevel.HIGH,
        composite_stress_index=0.78,
        sensor_health_status="HEALTHY",
        uncertainty_score=0.15,
        triggered_threshold="RAW_EXCEEDED",
        evidence_summary="Depletion fraction p=0.55 exceeds critical limit p=0.45",
        provenance=ProvenanceMetadata(
            provenance_class=ProvenanceClass.DERIVED,
            dataset_origin="AgriRiskEngine",
            is_synthetic=False,
        ),
    )

    # First write
    assert repo.upsert_crop_candidate_alert(alert_evt) is True

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM crop_candidate_alerts;")
    assert cur.fetchone()[0] == 1

    # Second write with identical (alert_id, event_time) updates composite_stress_index in place
    alert_evt_updated = alert_evt.model_copy(update={"composite_stress_index": 0.85})
    assert repo.upsert_crop_candidate_alert(alert_evt_updated) is True

    cur.execute("SELECT COUNT(*), composite_stress_index FROM crop_candidate_alerts;")
    row = cur.fetchone()
    assert row[0] == 1, "Duplicate alert row was created instead of updating existing row"
    assert abs(row[1] - 0.85) < 1e-4
