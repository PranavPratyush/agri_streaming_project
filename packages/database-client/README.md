# agri-persistence

TimescaleDB and PostgreSQL persistence layer for AgriKafka-Agent.

## Responsibilities
- Connection pooling with bounded retries and health checks via `psycopg-pool`.
- Data Access Objects (DAOs) for field profiles, sensor metadata, observations, windowed features, sensor health events, candidate crop risk alerts, investigation reports, farmer recommendations, and human feedback.
- Idempotent upserts (`ON CONFLICT DO NOTHING / UPDATE`) preventing duplicate persisted records upon Kafka message re-delivery.
- Distinct preservation of `event_time` and `ingestion_time` across all time-series tables.
- Representative query execution for field timelines, sensor freshness, recent alerts, and full alert evidence chains.
- Dedicated restricted read-only role (`agri_readonly`) support for MCP and agent introspection.

