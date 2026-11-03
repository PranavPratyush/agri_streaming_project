-- AgriKafka-Agent Migration 001: Initial Schema & Hypertables
-- Compatible with PostgreSQL 16 + TimescaleDB 2.16+
-- Reference: docs/decisions/ADR-0004-persistence-and-timeseries-storage.md

-- Extensions
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Schema migration tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- 1. Relational Entities: Field Profiles & Sensor Metadata
-- ============================================================================

CREATE TABLE IF NOT EXISTS field_profiles (
    field_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    elevation_m DOUBLE PRECISION,
    crop_name TEXT NOT NULL,
    variety TEXT NOT NULL,
    sowing_date DATE NOT NULL,
    expected_harvest_date DATE,
    current_growth_stage TEXT NOT NULL,
    soil_type TEXT NOT NULL,
    soil_texture TEXT,
    field_capacity DOUBLE PRECISION NOT NULL,
    wilting_point DOUBLE PRECISION NOT NULL,
    root_zone_depth_m DOUBLE PRECISION NOT NULL,
    irrigation_type TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sensor_metadata (
    sensor_id TEXT PRIMARY KEY,
    field_id TEXT NOT NULL REFERENCES field_profiles(field_id) ON DELETE CASCADE,
    sensor_model TEXT NOT NULL,
    manufacturer TEXT,
    measured_variable TEXT NOT NULL,
    unit TEXT NOT NULL,
    installation_date DATE,
    depth_m DOUBLE PRECISION,
    sampling_interval_seconds INTEGER NOT NULL DEFAULT 300,
    provenance_type TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sensor_metadata_field_id ON sensor_metadata (field_id);

-- ============================================================================
-- 2. Time-Series Hypertables (Partitioned by Event Time)
-- ============================================================================

-- Raw & Validated Observations (7-day chunks)
CREATE TABLE IF NOT EXISTS observations (
    idempotency_key TEXT NOT NULL,
    event_id UUID NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    ingestion_time TIMESTAMPTZ NOT NULL,
    field_id TEXT NOT NULL,
    sensor_id TEXT NOT NULL,
    source_provider TEXT NOT NULL,
    source_type TEXT NOT NULL,
    observed_variable TEXT NOT NULL,
    numeric_value DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    elevation DOUBLE PRECISION,
    sensor_depth_m DOUBLE PRECISION,
    provenance TEXT NOT NULL,
    quality_flags JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_observations PRIMARY KEY (idempotency_key, event_time)
);
SELECT create_hypertable('observations', 'event_time', if_not_exists => TRUE, chunk_time_interval => INTERVAL '7 days');

CREATE INDEX IF NOT EXISTS idx_observations_field_var_time ON observations (field_id, observed_variable, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_observations_sensor_time ON observations (sensor_id, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_observations_event_id ON observations (event_id, event_time);
CREATE INDEX IF NOT EXISTS idx_observations_quality_gin ON observations USING GIN (quality_flags);

-- Windowed Aggregate Features (7-day chunks)
CREATE TABLE IF NOT EXISTS windowed_features (
    feature_id UUID NOT NULL,
    field_id TEXT NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    window_type TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    feature_value DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL,
    sample_count INTEGER NOT NULL DEFAULT 1,
    min_value DOUBLE PRECISION,
    max_value DOUBLE PRECISION,
    std_dev DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_windowed_features PRIMARY KEY (field_id, feature_name, window_start, window_type)
);
SELECT create_hypertable('windowed_features', 'window_start', if_not_exists => TRUE, chunk_time_interval => INTERVAL '7 days');

CREATE INDEX IF NOT EXISTS idx_windowed_features_field_time ON windowed_features (field_id, window_start DESC);
CREATE INDEX IF NOT EXISTS idx_windowed_features_name_time ON windowed_features (feature_name, window_start DESC);

-- Sensor Health Forensic Events (7-day chunks)
CREATE TABLE IF NOT EXISTS sensor_health_events (
    idempotency_key TEXT NOT NULL,
    event_id UUID NOT NULL,
    sensor_id TEXT NOT NULL,
    field_id TEXT NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    ingestion_time TIMESTAMPTZ NOT NULL,
    health_state TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    reason_description TEXT,
    is_usable_for_advisory BOOLEAN NOT NULL DEFAULT true,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_sensor_health_events PRIMARY KEY (idempotency_key, event_time)
);
SELECT create_hypertable('sensor_health_events', 'event_time', if_not_exists => TRUE, chunk_time_interval => INTERVAL '7 days');

CREATE INDEX IF NOT EXISTS idx_sensor_health_sensor_time ON sensor_health_events (sensor_id, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_sensor_health_state_time ON sensor_health_events (health_state, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_sensor_health_field_time ON sensor_health_events (field_id, event_time DESC);

-- Candidate Crop Risk Alerts (14-day chunks)
CREATE TABLE IF NOT EXISTS crop_candidate_alerts (
    alert_id UUID NOT NULL,
    field_id TEXT NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    ingestion_time TIMESTAMPTZ NOT NULL,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING_TRIAGE',
    composite_stress_index DOUBLE PRECISION NOT NULL,
    fao56_depletion_fraction DOUBLE PRECISION,
    blast_risk_score DOUBLE PRECISION,
    thermal_stress_score DOUBLE PRECISION,
    sensor_health_state TEXT NOT NULL,
    uncertainty_score DOUBLE PRECISION NOT NULL,
    contributing_features JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    suppression_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_crop_candidate_alerts PRIMARY KEY (alert_id, event_time)
);
SELECT create_hypertable('crop_candidate_alerts', 'event_time', if_not_exists => TRUE, chunk_time_interval => INTERVAL '14 days');

CREATE INDEX IF NOT EXISTS idx_alerts_field_status_time ON crop_candidate_alerts (field_id, status, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_severity_time ON crop_candidate_alerts (severity, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_alert_id ON crop_candidate_alerts (alert_id);

-- ============================================================================
-- 3. Investigation, Recommendation, Feedback, and Audit Tables (Relational)
-- ============================================================================

CREATE TABLE IF NOT EXISTS investigation_reports (
    investigation_id UUID PRIMARY KEY,
    alert_id UUID NOT NULL,
    field_id TEXT NOT NULL REFERENCES field_profiles(field_id),
    agent_model TEXT NOT NULL,
    investigation_summary TEXT NOT NULL,
    corroborating_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    conflicting_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommendation_text TEXT NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_investigations_alert_id ON investigation_reports (alert_id);
CREATE INDEX IF NOT EXISTS idx_investigations_field_id ON investigation_reports (field_id);

CREATE TABLE IF NOT EXISTS farmer_recommendations (
    recommendation_id UUID PRIMARY KEY,
    alert_id UUID NOT NULL,
    field_id TEXT NOT NULL REFERENCES field_profiles(field_id),
    investigation_id UUID REFERENCES investigation_reports(investigation_id),
    approval_status TEXT NOT NULL DEFAULT 'PROPOSED' CHECK (approval_status IN ('PROPOSED', 'APPROVED', 'REJECTED', 'SUPERSEDED')),
    action_category TEXT NOT NULL,
    action_title TEXT NOT NULL,
    action_body TEXT NOT NULL,
    urgency TEXT NOT NULL,
    expiry_time TIMESTAMPTZ,
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_recommendations_field_status ON farmer_recommendations (field_id, approval_status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recommendations_alert_id ON farmer_recommendations (alert_id);

CREATE TABLE IF NOT EXISTS human_feedback (
    feedback_id UUID PRIMARY KEY,
    recommendation_id UUID NOT NULL REFERENCES farmer_recommendations(recommendation_id),
    field_id TEXT NOT NULL REFERENCES field_profiles(field_id),
    farmer_id TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    action_taken BOOLEAN NOT NULL,
    observed_outcome TEXT,
    feedback_comments TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_feedback_recommendation ON human_feedback (recommendation_id);
CREATE INDEX IF NOT EXISTS idx_feedback_farmer ON human_feedback (farmer_id, created_at DESC);

CREATE TABLE IF NOT EXISTS ingestion_replay_runs (
    run_id UUID PRIMARY KEY,
    run_type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    records_processed BIGINT NOT NULL DEFAULT 0,
    records_errored BIGINT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'RUNNING' CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED', 'ABORTED')),
    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_replay_source_status ON ingestion_replay_runs (source_name, status, start_time DESC);

CREATE TABLE IF NOT EXISTS system_audit_log (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON system_audit_log (entity_type, entity_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_created ON system_audit_log (created_at DESC);
