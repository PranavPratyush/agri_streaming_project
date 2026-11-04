# AgriKafka-Agent: Kafka CLI & TimescaleDB SQL Cheatsheet (Stages 0–19)

**Purpose:** Rapid Reference Cheatsheet for Technical Live Demonstration & Faculty Inquiries  
**Broker Host Listener:** `127.0.0.1:9092`  
**TimescaleDB Connection:** `127.0.0.1:5432` | Database: `agrikafka` | User: `agri_admin` (or `agri_readonly`)  

---

## 1. Apache Kafka KRaft CLI Commands

Run these inside the Kafka broker container or from a terminal with Kafka binaries installed:

### 1.1 List All Canonical Topics
```bash
docker exec -it agrikafka-broker-dev /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --list
```
*Expected Topics:*
```
agri.candidate-alerts
agri.dead-letter-queue
agri.human-feedback
agri.investigation-results
agri.operational-metrics
agri.sensor-health-events
agri.sensor-readings
agri.validated-observations
agri.weather-data
```

### 1.2 Describe Topic Partitions & Replication Factor
```bash
docker exec -it agrikafka-broker-dev /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --describe --topic agri.candidate-alerts
```
*Expected Output:* `PartitionCount: 3`, `ReplicationFactor: 1`, `Configs: retention.ms=2592000000,cleanup.policy=delete`.

### 1.3 Consume Raw Sensor Telemetry (`agri.sensor-readings`)
```bash
docker exec -it agrikafka-broker-dev /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic agri.sensor-readings \
  --from-beginning --max-messages 5 --property print.key=true
```

### 1.4 Consume PySpark Validated Observations (`agri.validated-observations`)
```bash
docker exec -it agrikafka-broker-dev /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic agri.validated-observations \
  --from-beginning --max-messages 5 --property print.key=true
```

### 1.5 Consume Deterministic Sensor Health Forensics (`agri.sensor-health-events`)
```bash
docker exec -it agrikafka-broker-dev /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic agri.sensor-health-events \
  --from-beginning --max-messages 5 --property print.key=true
```

### 1.6 Consume Candidate Risk Alerts (`agri.candidate-alerts`)
```bash
docker exec -it agrikafka-broker-dev /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic agri.candidate-alerts \
  --from-beginning --max-messages 5 --property print.key=true
```

### 1.7 Inspect Consumer Group Offset Lag
```bash
docker exec -it agrikafka-broker-dev /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group agri-group-stream-processor
```

---

## 2. TimescaleDB / PostgreSQL Analytical Queries

Connect via `psql`:
```bash
docker exec -it agrikafka-timescaledb psql -U agri_admin -d agrikafka
```
*(Or use read-only credentials: `-U agri_readonly -d agrikafka`)*

### 2.1 Sensor Freshness & Forensic Health Status
```sql
SELECT 
    sm.sensor_id,
    sm.field_id,
    sm.sensor_model,
    sm.measured_variable,
    latest_obs.last_value,
    latest_obs.last_event_time,
    ROUND(EXTRACT(EPOCH FROM (NOW() - latest_obs.last_event_time))::numeric, 1) AS latency_seconds,
    COALESCE(latest_health.health_state, 'UNKNOWN') AS health_state,
    COALESCE(latest_health.reason_code, 'NO_DATA') AS reason_code
FROM sensor_metadata sm
LEFT JOIN LATERAL (
    SELECT o.event_time AS last_event_time, o.numeric_value AS last_value
    FROM observations o
    WHERE o.sensor_id = sm.sensor_id
    ORDER BY o.event_time DESC LIMIT 1
) latest_obs ON TRUE
LEFT JOIN LATERAL (
    SELECT sh.health_state, sh.reason_code
    FROM sensor_health_events sh
    WHERE sh.sensor_id = sm.sensor_id
    ORDER BY sh.event_time DESC LIMIT 1
) latest_health ON TRUE
WHERE sm.is_active = TRUE
ORDER BY latency_seconds ASC NULLS LAST;
```

### 2.2 Recent Candidate Crop Risk Alerts
```sql
SELECT 
    alert_id,
    field_id,
    event_time,
    alert_type,
    severity,
    status,
    composite_stress_index,
    fao56_depletion_fraction,
    blast_risk_score,
    thermal_stress_score,
    sensor_health_state,
    uncertainty_score
FROM crop_candidate_alerts
ORDER BY event_time DESC
LIMIT 10;
```

### 2.3 Multi-Agent Investigation Runs
```sql
SELECT 
    run_id,
    alert_id,
    field_id,
    current_state,
    revision_count,
    final_decision,
    reliability_score,
    confidence_score,
    summary,
    created_at,
    updated_at
FROM multi_agent_investigation_runs
ORDER BY created_at DESC
LIMIT 10;
```

### 2.4 Agent-to-Agent Message Audit Trail
```sql
SELECT 
    message_id,
    run_id,
    from_agent,
    to_agent,
    message_type,
    payload->>'verdict' AS verdict,
    created_at
FROM agent_messages
ORDER BY created_at ASC
LIMIT 20;
```

### 2.5 Farmer Recommendations & Human Review Status
```sql
SELECT 
    recommendation_id,
    alert_id,
    field_id,
    action_category,
    action_title,
    urgency,
    approval_status,
    advisory_version,
    approved_by,
    approved_at,
    created_at
FROM farmer_recommendations
ORDER BY created_at DESC
LIMIT 10;
```

### 2.6 Multi-Agent Linked Farmer Feedback
```sql
SELECT 
    feedback_id,
    recommendation_id,
    investigation_id,
    rating,
    action_taken,
    advisory_relevant,
    evidence_useful,
    sensor_issue_reported,
    feedback_comments,
    created_at
FROM human_feedback
ORDER BY created_at DESC
LIMIT 10;
```

### 2.7 Notification Dispatches & DLQ Tracking
```sql
SELECT 
    dispatch_id,
    alert_id,
    channel,
    status,
    attempts,
    delivered_at,
    error_message,
    created_at
FROM notification_dispatches
ORDER BY created_at DESC
LIMIT 10;
```
