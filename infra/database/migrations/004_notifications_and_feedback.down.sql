-- Revert Migration 004

DROP TABLE IF EXISTS notification_dispatches CASCADE;

ALTER TABLE human_feedback DROP COLUMN IF EXISTS idempotency_key;
ALTER TABLE human_feedback DROP COLUMN IF EXISTS cited_agent_outputs;
ALTER TABLE human_feedback DROP COLUMN IF EXISTS expert_followup_requested;
ALTER TABLE human_feedback DROP COLUMN IF EXISTS sensor_issue_notes;
ALTER TABLE human_feedback DROP COLUMN IF EXISTS sensor_issue_reported;
ALTER TABLE human_feedback DROP COLUMN IF EXISTS field_context_correct;
ALTER TABLE human_feedback DROP COLUMN IF EXISTS evidence_useful;
ALTER TABLE human_feedback DROP COLUMN IF EXISTS advisory_relevant;
ALTER TABLE human_feedback DROP COLUMN IF EXISTS advisory_version;
ALTER TABLE human_feedback DROP COLUMN IF EXISTS alert_id;
ALTER TABLE human_feedback DROP COLUMN IF EXISTS investigation_id;

ALTER TABLE farmer_recommendations DROP COLUMN IF EXISTS advisory_version;
ALTER TABLE farmer_recommendations DROP CONSTRAINT IF EXISTS farmer_recommendations_approval_status_check;
ALTER TABLE farmer_recommendations ADD CONSTRAINT farmer_recommendations_approval_status_check 
    CHECK (approval_status IN ('PROPOSED', 'APPROVED', 'REJECTED', 'SUPERSEDED'));

