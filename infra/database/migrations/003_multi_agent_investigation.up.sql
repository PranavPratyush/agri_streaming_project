-- ============================================================================
-- AgriKafka-Agent: Multi-Agent Investigation Architecture Schema
-- Migration: 003_multi_agent_investigation.up.sql
-- Description: Creates tables for multi-agent runs, versioned agent messages,
--              and state machine transitions.
-- ============================================================================

-- 1. Multi-Agent Investigation Runs
CREATE TABLE IF NOT EXISTS multi_agent_investigation_runs (
    run_id UUID PRIMARY KEY,
    alert_id UUID NOT NULL,
    field_id TEXT NOT NULL REFERENCES field_profiles(field_id),
    current_state TEXT NOT NULL,
    revision_count INTEGER NOT NULL DEFAULT 0,
    max_revisions INTEGER NOT NULL DEFAULT 2,
    final_decision TEXT NOT NULL DEFAULT 'IN_PROGRESS',
    abstention_reason TEXT,
    summary TEXT,
    reliability_score DOUBLE PRECISION,
    confidence_score DOUBLE PRECISION,
    candidate_alert JSONB NOT NULL DEFAULT '{}'::jsonb,
    state_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_multi_agent_runs_alert_id ON multi_agent_investigation_runs (alert_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_runs_field_id ON multi_agent_investigation_runs (field_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_runs_state ON multi_agent_investigation_runs (current_state);
CREATE INDEX IF NOT EXISTS idx_multi_agent_runs_created_at ON multi_agent_investigation_runs (created_at DESC);

-- 2. Structured Versioned Agent Messages
CREATE TABLE IF NOT EXISTS agent_messages (
    message_id UUID PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES multi_agent_investigation_runs(run_id) ON DELETE CASCADE,
    correlation_id UUID NOT NULL,
    parent_message_id UUID,
    from_agent TEXT NOT NULL,
    to_agent TEXT NOT NULL,
    message_type TEXT NOT NULL,
    payload_schema_version TEXT NOT NULL DEFAULT '1.0.0',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    idempotency_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'ACCEPTED',
    error_details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_messages_run_id ON agent_messages (run_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_correlation_id ON agent_messages (correlation_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_routing ON agent_messages (from_agent, to_agent);
CREATE INDEX IF NOT EXISTS idx_agent_messages_created_at ON agent_messages (created_at DESC);

-- 3. Investigation State Transitions
CREATE TABLE IF NOT EXISTS investigation_state_transitions (
    transition_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES multi_agent_investigation_runs(run_id) ON DELETE CASCADE,
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    triggered_by TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_state_transitions_run_id ON investigation_state_transitions (run_id);
CREATE INDEX IF NOT EXISTS idx_state_transitions_created_at ON investigation_state_transitions (created_at DESC);

-- 4. Ensure Read-Only Permissions for Inspection Role
GRANT SELECT ON ALL TABLES IN SCHEMA public TO agri_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO agri_readonly;

