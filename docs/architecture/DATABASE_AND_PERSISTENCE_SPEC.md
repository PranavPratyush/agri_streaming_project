# AgriKafka-Agent — TimescaleDB & PostgreSQL Persistence Specification

- **Module:** `packages/database-client/` (`agri_persistence`) & `infra/database/`
- **Architecture Reference:** [ADR-0004: Persistence Strategy & Time-Series Storage](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0004-persistence-and-timeseries-storage.md)
- **Status:** Approved / Implemented
- **Date:** 2026-11-03

---

## 1. System Context & Compatibility

AgriKafka-Agent requires persistent storage for both high-velocity streaming time-series data (observations, rolling window aggregates, sensor-health evaluations, crop stress candidate alerts) and relational agricultural entities (farm and crop profiles, sensor metadata, agent investigation reports, farmer recommendations, human feedback, and audit logs).

### Pinned Engine & Driver Compatibility Matrix

| Component | Pinned Version | Image / Package | Rationale |
|---|---|---|---|
| **Database Engine** | TimescaleDB 2.16+ on PostgreSQL 16 | `timescale/timescaledb:latest-pg16` | Standard PostgreSQL 16 relational engine augmented with TimescaleDB hypertables, automated chunk partitioning, and columnar compression. |
| **Python Client Driver** | Psycopg 3.3.7 | `psycopg[binary]>=3.2.0` | Official modern PostgreSQL driver with binary C-extensions, native UUID, TIMESTAMPTZ, and JSONB mapping. |
| **Connection Pool** | Psycopg-Pool 3.3.3 | `psycopg-pool>=3.2.0` | Bounded connection pool with thread-safe acquisition, max lifetime, idle cleanup, and health checks. |
| **Persistence Volume** | Named Docker Volume | `agrikafka_timescale_dev_data` | Mapped to `/var/lib/postgresql/data` ensuring durable storage across container lifecycle restarts. |

---

## 2. Schema Architecture & Hypertables vs Relational Tables

In accordance with [ADR-0004](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0004-persistence-and-timeseries-storage.md) and PostgreSQL best practices, tables are partitioned as hypertables **only** when their write velocity and query patterns justify time-space chunking.

### 2.1 Time-Series Hypertables

Hypertables automate chunk creation and time-range query pruning. In TimescaleDB, **all PRIMARY KEY and UNIQUE constraints on a hypertable must contain the time partitioning column**.

```
                           ┌───────────────────────────────┐
                           │      observations             │ (Partition: event_time, 7-day chunks)
                           │ PK: (idempotency_key, time)   │
                           └───────────────▲───────────────┘
                                           │
                           ┌───────────────┴───────────────┐
                           │      windowed_features        │ (Partition: window_start, 7-day chunks)
                           │ PK: (field, name, time, type) │
                           └───────────────▲───────────────┘
                                           │
                           ┌───────────────┴───────────────┐
                           │   sensor_health_events        │ (Partition: event_time, 7-day chunks)
                           │ PK: (idempotency_key, time)   │
                           └───────────────▲───────────────┘
                                           │
                           ┌───────────────┴───────────────┐
                           │   crop_candidate_alerts       │ (Partition: event_time, 14-day chunks)
                           │ PK: (alert_id, event_time)    │
                           └───────────────────────────────┘
```

1. **`observations` (Hypertable, 7-day chunks):**
   - Captures raw and validated physical sensor readings, weather context, and historical replays.
   - Primary Key: `(idempotency_key, event_time)`.
   - Columns: `idempotency_key`, `event_id`, `event_time`, `ingestion_time`, `field_id`, `sensor_id`, `source_provider`, `source_type`, `observed_variable`, `numeric_value`, `unit`, `latitude`, `longitude`, `elevation`, `sensor_depth_m`, `provenance`, `quality_flags` (JSONB), `metadata` (JSONB), `created_at`.
   - Distinct Timestamps: Strictly separates `event_time` (when observation occurred) from `ingestion_time` (when received).
2. **`windowed_features` (Hypertable, 7-day chunks):**
   - Stores 5-minute tumbling and 30-minute sliding window aggregations calculated by PySpark (VPD, dew point, leaf wetness proxy, mean, min, max, stddev).
   - Primary Key: `(field_id, feature_name, window_start, window_type)`.
3. **`sensor_health_events` (Hypertable, 7-day chunks):**
   - Captures forensic health diagnostics from the deterministic sensor health engine.
   - Primary Key: `(idempotency_key, event_time)`.
   - Columns include `health_state`, `reason_code`, `is_usable_for_advisory`, `metrics` (JSONB), `evidence` (JSONB).
4. **`crop_candidate_alerts` (Hypertable, 14-day chunks):**
   - Stores numerical alerts raised by the FAO-56 crop risk engine.
   - Primary Key: `(alert_id, event_time)`.
   - Columns include `composite_stress_index`, `fao56_depletion_fraction`, `blast_risk_score`, `thermal_stress_score`, `contributing_features` (JSONB), `suppression_reason`.

### 2.2 Relational Tables (Entities & Decision Lineage)

1. **`field_profiles`:** Field parcels, crop cultivars (Ragi GPU-28), soil properties (AWC, FC, WP), and phenological stages. Key: `field_id` TEXT PRIMARY KEY.
2. **`sensor_metadata`:** Hardware probe specifications, installation depths, sampling cadences, and provenance classifications. Key: `sensor_id` TEXT PRIMARY KEY.
3. **`investigation_reports`:** Bounded LLM investigation summaries, corroborating/conflicting evidence, and confidence scores. Key: `investigation_id` UUID PRIMARY KEY.
4. **`farmer_recommendations`:** Proposed actionable advisories, approval status (`PROPOSED`, `APPROVED`, `REJECTED`, `SUPERSEDED`), and expiry timestamps. Key: `recommendation_id` UUID PRIMARY KEY.
5. **`human_feedback`:** Farmer and agronomist verification, ratings (1–5), actions taken, and observed outcomes. Key: `feedback_id` UUID PRIMARY KEY.
6. **`ingestion_replay_runs`:** Metadata, records processed, and status for historical replay and live ingestion runs. Key: `run_id` UUID PRIMARY KEY.
7. **`system_audit_log`:** Immutable audit trail of administrative actions and approvals. Key: `audit_id` BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY.
8. **`schema_migrations`:** Applied schema migration versions and execution timestamps. Key: `version` INTEGER PRIMARY KEY.

---

## 3. Delivery Semantics & Idempotent Upsert Strategy

### 3.1 Transport & Delivery Guarantees

AgriKafka-Agent deliberately avoids claiming "end-to-end exactly-once" delivery across decoupled distributed services. Instead, it implements:

$$\text{At-Least-Once Kafka Delivery} + \text{Database Uniqueness Constraints} = \text{Effectively-Once Persistent State}$$

### 3.2 Kafka Consumer Offset Commit Protocol

In `KafkaDatabaseConsumer` (`agri_persistence/consumer.py`):
1. Automatic offset commit is disabled: `enable.auto.commit = False`.
2. Telemetry is consumed and parsed into canonical Stage 7 contracts (`AgriObservationEvent`, `SensorHealthResultEvent`, `CropRiskCandidateAlertEvent`).
3. Database transaction is executed with explicit conflict handling:
   - For observations & sensor health: `ON CONFLICT (idempotency_key, event_time) DO NOTHING`.
   - For candidate alerts & window features: `ON CONFLICT (...) DO UPDATE SET ...`.
4. Kafka offset is committed **synchronously only after** the database transaction successfully commits.
5. If the consumer crashes before offset commit, re-polled messages are safely rejected by the database unique constraint without inserting duplicate rows.

---

## 4. Retention, Compression & Sizing Analysis

### 4.1 Expected Telemetry Volume

- Active Prototype Deployment: 1 field parcel, 10 physical & derived sensor variables.
- Sampling Cadence: 1 reading every 5 minutes (288 observations / sensor / day).
- Daily Raw Observations: $10 \times 288 = 2,880\text{ rows/day}$.
- Annual Raw Volume: $\sim 1,051,200\text{ rows/year}$.
- Uncompressed Storage Footprint: $\sim 250\text{ bytes/row} \implies \sim 720\text{ KB/day} \approx 260\text{ MB/year}$.

### 4.2 Columnar Compression Policy

TimescaleDB columnar compression reorganizes chunk rows into compressed column arrays:
- **Chunk Interval:** 7 days for observation tables, 14 days for alert tables.
- **Compression Rule:** Chunks older than 14 days are compressed:
  ```sql
  ALTER TABLE observations SET (
      timescaledb.compress,
      timescaledb.compress_segmentby = 'field_id, observed_variable',
      timescaledb.compress_orderby = 'event_time DESC'
  );
  SELECT add_compression_policy('observations', INTERVAL '14 days');
  ```
- **Compression Ratio:** Typically achieves 85% to 92% compression, reducing annual storage to $<35\text{ MB/year}$.

### 4.3 Retention Invariant

**Raw agricultural research data is never automatically dropped or pruned.** Historical telemetry represents irreplaceable ground truth for multi-season agronomic model calibration. Cold data is retained in compressed chunks or exported to columnar Parquet archives rather than dropped.

---

## 5. Security & Access Control: Restricted Read-Only Role

In compliance with [.agents/rules/security-and-secrets.md](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/.agents/rules/security-and-secrets.md):

- Migration `002_readonly_role.up.sql` creates dedicated user `agri_readonly`.
- Granted Permissions:
  - `CONNECT ON DATABASE agrikafka`
  - `USAGE ON SCHEMA public`
  - `SELECT ON ALL TABLES IN SCHEMA public`
  - `SELECT ON ALL SEQUENCES IN SCHEMA public`
  - `ALTER DEFAULT PRIVILEGES ... GRANT SELECT`
- Explicitly Denied Privileges:
  - `REVOKE ALL PRIVILEGES ON SCHEMA public FROM agri_readonly;`
  - `REVOKE CREATE ON SCHEMA public FROM agri_readonly;`
  - No `INSERT`, `UPDATE`, `DELETE`, `ALTER`, or `DROP` permissions.
- Use Case: LLM alert investigator inspection tools, MCP database servers, and Grafana operations dashboards connect strictly via `agri_readonly`.

---

## 6. Migration CLI & Rollback Guidance

The database migration runner (`infra/database/migrate.py`) tracks schema evolution through the `schema_migrations` table:

```bash
# Check migration status
python infra/database/migrate.py status

# Apply pending migrations
python infra/database/migrate.py up

# Roll back the latest migration
python infra/database/migrate.py down

# Validate migration files offline
python infra/database/migrate.py validate
```

---

## 7. Representative Analytical Queries

Four verified SQL queries are codified in `infra/database/queries/`:

1. **Field 24-Hour Timeline (`01_field_timeline.sql`):** Time-ordered environmental observations and quality flags for a specific field parcel over the preceding 24 hours.
2. **Sensor Freshness Dashboard (`02_sensor_freshness.sql`):** Real-time sensor latency (seconds elapsed since last reading) and latest forensic health state.
3. **Recent Candidate Alerts (`03_recent_alerts.sql`):** High-severity alerts raised in the last 72 hours with CSI, depletion fraction, and investigation status.
4. **Full Alert Evidence Chain (`04_alert_evidence_chain.sql`):** Complete relational audit trail linking a candidate alert to its contributing sensor metrics, agent investigation report, farmer recommendation, and human feedback.

