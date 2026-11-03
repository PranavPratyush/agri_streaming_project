# AgriKafka-Agent: Operational Observability & Incident Runbook

**Stage 14 Operational Runbook**  
*Platform:* AgriKafka-Agent (Fault-Tolerant, Real-Time Agricultural Risk Monitoring and Decision Support)  
*Crop Context:* Finger Millet (*Eleusine coracana* / Ragi GPU-28), Red Sandy Loam, Kolar District, Karnataka  
*Dashboard Boundary:* Grafana is strictly the engineering/operations dashboard, not the farmer-facing product.

---

## 1. System Architecture & Port Allocation

All operational and telemetry interfaces are bound strictly to `127.0.0.1` (localhost) to prevent unauthenticated network exposure.

| Service / Component | Container / Target | Local Host Binding | Prometheus Scrape Port | Protocol | Purpose |
|---|---|---|---|---|---|
| **Prometheus Server** | `prometheus` | `127.0.0.1:9090` | N/A (`:9090/metrics`) | HTTP | Telemetry aggregation & alerting |
| **Grafana Operations** | `grafana` | `127.0.0.1:3000` | N/A | HTTP | Engineering & pipeline dashboards |
| **Kafka KRaft Broker** | `kafka` | `127.0.0.1:9092` | Internal | Kafka Wire | Event streaming bus |
| **TimescaleDB** | `timescaledb` | `127.0.0.1:5432` | N/A | PostgreSQL | Long-term telemetry & alert storage |
| **FastAPI Backend** | `backend-api` | `127.0.0.1:8000` | `127.0.0.1:8000/metrics` | HTTP | Core REST API & farmer PWA backend |
| **Ingestion Adapters** | `ingestion` | N/A | `127.0.0.1:8001/metrics` | HTTP | Open-Meteo & station poller metrics |
| **PySpark Streaming** | `stream-processor` | N/A | `127.0.0.1:8002/metrics` | HTTP | Micro-batch & watermark metrics |
| **Risk & Health Engine** | `risk-engine` | N/A | `127.0.0.1:8003/metrics` | HTTP | Deterministic risk & sensor forensics |
| **Persistence Sink** | `persistence-sink`| N/A | `127.0.0.1:8004/metrics` | HTTP | Database consumer & write metrics |

---

## 2. Grafana Dashboards Catalog

The 7 pre-provisioned dashboards are located in `infra/grafana/dashboards/` and automatically mounted into Grafana at `/etc/grafana/dashboards`.

| Dashboard File | UID | Title | Key Metrics & Visualizations |
|---|---|---|---|
| `01-system-overview.json` | `agri-01-system-overview` | System Overview | Broker health, total records ingested vs processed, active candidate alerts, DLQ count, and end-to-end throughput rates. |
| `02-kafka-and-consumer-groups.json` | `agri-02-kafka-and-consumer-groups` | Kafka & Consumer Groups | Dispatch rates by topic, consumption rates by group, consumer lag per partition, and dead-letter queue growth. |
| `03-spark-streaming-checkpoint-health.json` | `agri-03-spark-streaming-health` | Spark Streaming & Checkpoints | Micro-batch execution latency, input vs processed row counts, watermark lag (seconds), late rows dropped, and checkpoint commits. |
| `04-ingestion-source-freshness.json` | `agri-04-ingestion-source-freshness` | Ingestion Source Freshness | Telemetry freshness latency per station, adapter operational state, external poll latency, and HTTP 429 rate-limit events. |
| `05-data-quality-sensor-health.json` | `agri-05-data-quality-sensor-health` | Data Quality & Sensor Health | Sensor health status classifications (HEALTHY, STALE, SUSPECT, FAULTY, UNKNOWN), reason codes, natural flatline exemptions, and safety blocks. |
| `06-candidate-alerts-investigator.json` | `agri-06-candidate-alerts-investigator` | Candidate Alerts & Investigator | Alerts by risk type and severity, suppressed alerts, investigator invocation duration, tool call rates, token usage, and fallback rates. |
| `07-reliability-evaluation-metrics.json` | `agri-07-reliability-evaluation-metrics` | Reliability & Persistence Metrics | TimescaleDB connection pool status, upsert operation volumes (inserts vs deduplication skips), query latency, and human feedback ratings. |

---

## 3. Incident Triage Runbooks

### Alert 1: `ServiceDown`
- **Severity:** Critical
- **Trigger Expression:** `up == 0` for 1 minute
- **Impact:** Core platform telemetry or streaming pipeline component is completely halted or disconnected.
- **Triage Steps:**
  1. Identify failing service from the alert label (`$labels.service`).
  2. Inspect container status:
     ```bash
     docker compose ps
     ```
  3. Check container logs for unhandled exceptions or OOM kills:
     ```bash
     docker compose logs --tail=100 <service-name>
     ```
  4. If the service is the Kafka broker or TimescaleDB, check port availability (`9092` or `5432`) and disk space on persistent Docker volumes.
  5. Restart the affected service:
     ```bash
     docker compose restart <service-name>
     ```

### Alert 2: `StaleSourceTelemetry`
- **Severity:** Warning
- **Trigger Expression:** `agri_ingestion_source_freshness_seconds > 300` for 2 minutes
- **Impact:** Upstream station observations are lagging by more than 5 minutes, leading to potential delayed risk alerts.
- **Triage Steps:**
  1. Check target station and adapter: `$labels.adapter` and `$labels.station_id`.
  2. Verify if the upstream provider API is reachable:
     - Check rate limits: inspect `agri_ingestion_rate_limit_hits_total`.
     - Check poll duration: inspect `agri_ingestion_request_duration_seconds`.
  3. If rate-limited (HTTP 429), verify backoff jitter configuration in `services/ingestion/adapters/`.
  4. If the physical station is offline, verify whether the fallback reanalysis adapter or satellite cache can be engaged.

### Alert 3: `SustainedConsumerLag`
- **Severity:** Warning
- **Trigger Expression:** `agri_kafka_consumer_lag_records > 500` for 3 minutes
- **Impact:** Processing pipeline falling behind ingestion rate; late observations may violate watermark boundaries.
- **Triage Steps:**
  1. Identify consumer group and topic: `$labels.consumer_group`, `$labels.topic`.
  2. Inspect Spark micro-batch processing duration (`agri_spark_batch_duration_seconds`). If duration > trigger interval (e.g., > 10s), Spark is compute-constrained.
  3. Inspect persistence sink batch latency (`agri_db_query_duration_seconds`). If TimescaleDB writes are slow, check database lock contention or disk I/O.
  4. Verify consumer thread health and restart consumer if thread died.

### Alert 4: `RepeatedSparkMicroBatchFailures`
- **Severity:** Critical
- **Trigger Expression:** `rate(agri_spark_checkpoint_commits_total{status="failure"}[5m]) > 0` for 2 minutes
- **Impact:** Structured Streaming query cannot commit checkpoint offsets. Data processing halted, risking duplicated state or crash-loop.
- **Triage Steps:**
  1. Inspect PySpark log output for driver and executor errors:
     ```bash
     docker compose logs --tail=150 stream-processor
     ```
  2. Verify checkpoint directory health and write permissions on Docker volume `spark_checkpoints`:
     ```bash
     docker compose exec stream-processor ls -la /tmp/spark_checkpoints
     ```
  3. If checkpoint state is corrupted, trigger safe recovery replay following ADR-002 checkpoint recovery procedures.

### Alert 5: `DeadLetterQueueGrowth`
- **Severity:** Warning
- **Trigger Expression:** `increase(agri_kafka_dlq_messages_total[5m]) > 5` for 1 minute
- **Impact:** Invalid, corrupted, or schema-violating events are arriving at the Kafka ingress.
- **Triage Steps:**
  1. Review `$labels.reason_code` and `$labels.original_topic`.
  2. Inspect sample messages on the DLQ topic `agri.dlq.observations`:
     ```bash
     docker compose exec kafka kafka-console-consumer.sh \
       --bootstrap-server localhost:9092 \
       --topic agri.dlq.observations \
       --from-beginning --max-messages 10
     ```
  3. Verify whether an upstream adapter introduced an unversioned contract change or schema drift.
  4. Route fixed records back via the replay tool if payloads are salvageable.

### Alert 6: `CriticalCropStressIndex`
- **Severity:** Critical
- **Trigger Expression:** `agri_risk_composite_stress_index > 0.85` for 15 minutes
- **Impact:** Prolonged severe physiological or water stress detected for field parcel (e.g., Ragi moisture stress during flowering stage).
- **Triage Steps:**
  1. Identify field: `$labels.field_id`.
  2. Check sensor health status on Dashboard 05 (`05-data-quality-sensor-health`). Ensure sensors are not in `FAULTY` or `SUSPECT` state.
  3. If the agronomic safety gate blocked the automated advisory (`agri_advisory_safety_gate_blocks_total` incremented), check reason code (e.g., `UNVERIFIED_SENSOR`).
  4. Check whether the bounded investigator agent initiated an investigation (`agri_investigator_invocations_total`).
  5. Check notification dispatch status (`agri_notification_attempts_total`).

---

## 4. Routine Operations & Verification

### Verifying Prometheus Health
```bash
# Check Prometheus liveness
curl -s http://127.0.0.1:9090/-/healthy
# Expected: Prometheus Server is Healthy.

# Check active scrape targets
curl -s http://127.0.0.1:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

### Verifying Grafana Health & Datasources
```bash
# Check Grafana liveness
curl -s http://127.0.0.1:3000/api/health
# Expected: {"commit":"...","database":"ok","version":"11.2.0"}

# Check Prometheus datasource connectivity (authenticated)
curl -u admin:admin_secure_password_dev_only \
  http://127.0.0.1:3000/api/datasources/name/Prometheus
```

### Starting / Stopping Observability Stack
```bash
# Start Prometheus and Grafana
docker compose up -d prometheus grafana

# Tail Prometheus logs
docker compose logs -f prometheus

# Stop observability stack
docker compose stop prometheus grafana
```

