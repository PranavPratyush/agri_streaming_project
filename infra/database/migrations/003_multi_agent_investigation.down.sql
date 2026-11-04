-- ============================================================================
-- AgriKafka-Agent: Multi-Agent Investigation Architecture Schema (Rollback)
-- Migration: 003_multi_agent_investigation.down.sql
-- ============================================================================

DROP TABLE IF EXISTS investigation_state_transitions CASCADE;
DROP TABLE IF EXISTS agent_messages CASCADE;
DROP TABLE IF EXISTS multi_agent_investigation_runs CASCADE;

