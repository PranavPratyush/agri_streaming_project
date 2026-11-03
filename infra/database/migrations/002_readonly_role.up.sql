-- AgriKafka-Agent Migration 002: Create Restricted Read-Only Role
-- Purpose: Provide read-only inspection access for LLM agents, MCP tools, and analytics dashboards
-- Guarantees: Zero DDL (CREATE, DROP, ALTER) and zero DML writes (INSERT, UPDATE, DELETE)

DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles WHERE rolname = 'agri_readonly'
   ) THEN
      CREATE ROLE agri_readonly WITH LOGIN PASSWORD 'agri_readonly_password_insecure';
   END IF;
END
$do$;

-- Revoke all administrative and modification rights
REVOKE ALL PRIVILEGES ON SCHEMA public FROM agri_readonly;
REVOKE CREATE ON SCHEMA public FROM agri_readonly;

-- Grant minimal connect and usage rights
GRANT CONNECT ON DATABASE agrikafka TO agri_readonly;
GRANT USAGE ON SCHEMA public TO agri_readonly;

-- Grant SELECT only on current and future tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO agri_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO agri_readonly;

-- Grant SELECT on sequences (for reading current identity values if needed)
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO agri_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO agri_readonly;
