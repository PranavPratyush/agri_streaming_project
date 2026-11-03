# ADR-0004: Persistence Strategy & Time-Series Storage

- **Status:** Proposed (Pending User Approval)
- **Date:** 2026-11-01
- **Deciders:** Lead Engineer, Team (Aanish Khan, Daksh Chauhan, Pranav Pratyush)
- **Technical Domain:** Persistence Layer, Time-Series Data, Relational Models

---

## 1. Context & Problem Statement
AgriKafka-Agent requires durable storage for high-frequency windowed sensor aggregates, telemetry events, detector anomalies, agent investigation records, and human approval decisions. We need a persistence engine that excels at time-series queries (for Grafana dashboards) while supporting relational schemas (for farm profiles, user registrations, and audit logs).

---

## 2. Options Considered

### Option 1: Plain PostgreSQL 16
- Standard relational DB. Lacks native time-partitioned chunking, compression, and automated continuous rollups.

### Option 2: TimescaleDB 2.16 on PostgreSQL 16 (Recommended)
- TimescaleDB extends PostgreSQL with **hypertables** (automatic time-space chunk partitioning), continuous aggregates, and columnar compression.
- Official Docker image: `timescale/timescaledb:latest-pg16`.
- Completely compatible with standard PostgreSQL tools, SQL queries, `asyncpg`, and Grafana native PostgreSQL datasource.

### Option 3: InfluxDB / Prometheus
- Specialized metrics engines, but poorly suited for relational data (farmer accounts, field boundary metadata, audit tables) and lacks standard SQL.

---

## 3. Decision
Standardize on **TimescaleDB 2.16 (PostgreSQL 16)** via Docker Compose:
1. **Hypertables:** Convert high-frequency tables (`field_observations`, `crop_alerts`, `pipeline_metrics`) to hypertables partitioned on `time` with space partitioning on `field_id`.
2. **Relational Tables:** Keep `farms`, `fields`, `crop_profiles`, and `farmer_feedback` as standard relational tables with foreign key constraints.
3. **Chunk Interval:** Configure 7-day chunk time intervals for observation tables.
4. **Grafana Integration:** Connect Grafana directly to TimescaleDB using read-only credentials.

---

## 4. Consequences

### Positive
- Unified database: one container provides both time-series speed and relational integrity.
- Out-of-the-box Grafana compatibility without custom connector services.
- Fast time-bucket queries (`time_bucket('5 minutes', time)`).

### Negative
- Requires ~500 MB to 1 GB of RAM in Docker.

### Neutral
- SQL migrations must handle `create_hypertable()` execution safely.
