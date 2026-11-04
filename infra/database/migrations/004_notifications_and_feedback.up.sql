-- Migration 004: Notification Dispatches and Enhanced Feedback Loop
-- Supports Stage 19: Notification & Human Feedback Workflow

-- 1. Update farmer_recommendations to support full review lifecycle
ALTER TABLE farmer_recommendations DROP CONSTRAINT IF EXISTS farmer_recommendations_approval_status_check;
ALTER TABLE farmer_recommendations ADD CONSTRAINT farmer_recommendations_approval_status_check 
    CHECK (approval_status IN ('PROPOSED', 'AWAITING_REVIEW', 'APPROVED', 'REJECTED', 'ACKNOWLEDGED', 'REQUEST_INSPECTION', 'EXPIRED', 'SUPERSEDED'));

ALTER TABLE farmer_recommendations ADD COLUMN IF NOT EXISTS advisory_version INTEGER NOT NULL DEFAULT 1;

-- 2. Enhance human_feedback with multi-agent linkage and granular evaluation attributes
ALTER TABLE human_feedback ADD COLUMN IF NOT EXISTS investigation_id UUID;
ALTER TABLE human_feedback ADD COLUMN IF NOT EXISTS alert_id UUID;
ALTER TABLE human_feedback ADD COLUMN IF NOT EXISTS advisory_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE human_feedback ADD COLUMN IF NOT EXISTS advisory_relevant BOOLEAN DEFAULT TRUE;
ALTER TABLE human_feedback ADD COLUMN IF NOT EXISTS evidence_useful BOOLEAN DEFAULT TRUE;
ALTER TABLE human_feedback ADD COLUMN IF NOT EXISTS field_context_correct BOOLEAN DEFAULT TRUE;
ALTER TABLE human_feedback ADD COLUMN IF NOT EXISTS sensor_issue_reported BOOLEAN DEFAULT FALSE;
ALTER TABLE human_feedback ADD COLUMN IF NOT EXISTS sensor_issue_notes TEXT;
ALTER TABLE human_feedback ADD COLUMN IF NOT EXISTS expert_followup_requested BOOLEAN DEFAULT FALSE;
ALTER TABLE human_feedback ADD COLUMN IF NOT EXISTS cited_agent_outputs JSONB DEFAULT '[]'::jsonb;
ALTER TABLE human_feedback ADD COLUMN IF NOT EXISTS idempotency_key TEXT UNIQUE;

CREATE INDEX IF NOT EXISTS idx_feedback_investigation ON human_feedback (investigation_id);
CREATE INDEX IF NOT EXISTS idx_feedback_alert ON human_feedback (alert_id);
CREATE INDEX IF NOT EXISTS idx_feedback_idempotency ON human_feedback (idempotency_key);

-- 3. Create notification_dispatches table for delivery tracking, deduplication, and retries
CREATE TABLE IF NOT EXISTS notification_dispatches (
    dispatch_id UUID PRIMARY KEY,
    alert_id UUID NOT NULL,
    investigation_id UUID,
    recommendation_id UUID,
    advisory_version INTEGER NOT NULL DEFAULT 1,
    recipient_id TEXT NOT NULL,
    channel TEXT NOT NULL CHECK (channel IN ('pwa_push', 'mock_channel', 'telegram')),
    idempotency_key TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'SENT', 'FAILED', 'DEAD_LETTER')),
    attempts INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    next_retry_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    payload JSONB NOT NULL,
    provider_response JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notifications_recipient_status ON notification_dispatches (recipient_id, status);
CREATE INDEX IF NOT EXISTS idx_notifications_idempotency ON notification_dispatches (idempotency_key);
CREATE INDEX IF NOT EXISTS idx_notifications_alert_rec ON notification_dispatches (alert_id, recommendation_id);

