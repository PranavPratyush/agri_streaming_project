-- AgriKafka-Agent Rollback 001: Drop Initial Schema & Hypertables

DROP TABLE IF EXISTS system_audit_log CASCADE;
DROP TABLE IF EXISTS ingestion_replay_runs CASCADE;
DROP TABLE IF EXISTS human_feedback CASCADE;
DROP TABLE IF EXISTS farmer_recommendations CASCADE;
DROP TABLE IF EXISTS investigation_reports CASCADE;
DROP TABLE IF EXISTS crop_candidate_alerts CASCADE;
DROP TABLE IF EXISTS sensor_health_events CASCADE;
DROP TABLE IF EXISTS windowed_features CASCADE;
DROP TABLE IF EXISTS observations CASCADE;
DROP TABLE IF EXISTS sensor_metadata CASCADE;
DROP TABLE IF EXISTS field_profiles CASCADE;
DROP TABLE IF EXISTS schema_migrations CASCADE;
