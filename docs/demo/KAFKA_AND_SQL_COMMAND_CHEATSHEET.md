# Kafka and SQL Command Cheatsheet
**System:** AgriKafka-Agent  
**Database:** TimescaleDB / PostgreSQL 16 (`127.0.0.1:5432`)  
**Message Broker:** Apache Kafka 3.8.0 KRaft (`127.0.0.1:9092`)  

---

## 1. TimescaleDB Verification Queries (Run inside `psql` or DBeaver)

To enter the database CLI directly from host PowerShell:
```powershell
docker exec -it agrikafka-timescaledb psql -U agri_admin -d agrikafka
```

### Query 1: Verify Hypertables Status
```sql
SELECT hypertable_name, num_dimensions, num_chunks, compression_enabled 
FROM timescaledb_information.hypertables;
```
*Expected Output:*
Shows `observations`, `windowed_features`, `sensor_health_events`, and `crop_candidate_alerts` as active hypertables.

### Query 2: Inspect Recent Sensor Observations (Chronological)
```sql
SELECT 
    event_time,
    field_id,
    sensor_id,
    observed_variable,
    numeric_value,
    unit,
    source_provider
FROM observations 
ORDER BY event_time DESC 
LIMIT 10;
```

### Query 3: Count Records by Variable and Provider
```sql
SELECT 
    source_provider,
    observed_variable,
    count(*) as record_count,
    min(numeric_value) as min_val,
    avg(numeric_value)::numeric(10,2) as avg_val,
    max(numeric_value) as max_val
FROM observations 
GROUP BY source_provider, observed_variable
ORDER BY source_provider, observed_variable;
```

### Query 4: Inspect Sensor Health Events
```sql
SELECT 
    event_time,
    sensor_id,
    field_id,
    health_status,
    anomaly_type,
    confidence_score,
    diagnostic_details
FROM sensor_health_events
ORDER BY event_time DESC 
LIMIT 10;
```

### Query 5: Inspect Candidate Agronomic Alerts
```sql
SELECT 
    alert_id,
    event_time,
    field_id,
    crop_name,
    growth_stage,
    severity,
    risk_type,
    triggering_condition
FROM crop_candidate_alerts
ORDER BY event_time DESC 
LIMIT 10;
```

### Query 6: Check Idempotency Key Distribution
```sql
SELECT 
    idempotency_key, 
    count(*) as occurrences 
FROM observations 
GROUP BY idempotency_key 
HAVING count(*) > 1;
```
*Expected Output:*
`0 rows` (verifies zero duplicates exist).

---

## 2. Kafka CLI Inspection Commands (Run from Host PowerShell)

### Command 1: List All Topics
```powershell
docker exec agrikafka-broker-dev /opt/kafka/bin/kafka-topics.sh `
  --bootstrap-server 127.0.0.1:9092 `
  --list
```

### Command 2: Describe a Topic (Partitions, Replicas, Min-ISR)
```powershell
docker exec agrikafka-broker-dev /opt/kafka/bin/kafka-topics.sh `
  --bootstrap-server 127.0.0.1:9092 `
  --describe `
  --topic agri.sensor-readings
```

### Command 3: Monitor Live Raw Telemetry Stream
```powershell
docker exec -it agrikafka-broker-dev /opt/kafka/bin/kafka-console-consumer.sh `
  --bootstrap-server 127.0.0.1:9092 `
  --topic agri.sensor-readings `
  --from-beginning `
  --property print.key=true `
  --property print.timestamp=true
```

### Command 4: Monitor Validated Observations Stream
```powershell
docker exec -it agrikafka-broker-dev /opt/kafka/bin/kafka-console-consumer.sh `
  --bootstrap-server 127.0.0.1:9092 `
  --topic agri.validated-observations `
  --from-beginning
```

### Command 5: Inspect Dead-Letter Queue (DLQ)
```powershell
docker exec -it agrikafka-broker-dev /opt/kafka/bin/kafka-console-consumer.sh `
  --bootstrap-server 127.0.0.1:9092 `
  --topic agri.dead-letter-queue `
  --from-beginning
```

### Command 6: Inspect Consumer Groups and Partition Lag
```powershell
docker exec agrikafka-broker-dev /opt/kafka/bin/kafka-consumer-groups.sh `
  --bootstrap-server 127.0.0.1:9092 `
  --list

# Describe specific consumer group:
docker exec agrikafka-broker-dev /opt/kafka/bin/kafka-consumer-groups.sh `
  --bootstrap-server 127.0.0.1:9092 `
  --describe `
  --group agrikafka-timescaledb-consumer
```

---

## 3. Fast Manual Ingestion & Test Trigger Commands

### Run OpenSenseMap Live Station Ingestion:
```powershell
.\.venv\Scripts\Activate.ps1
python apps/ingestion-service/src/agri_ingestion/adapters/live_station.py
```

### Run Historical Open-Meteo Replay (100x Speed):
```powershell
.\.venv\Scripts\Activate.ps1
python apps/ingestion-service/src/agri_ingestion/adapters/replay.py --speed 100
```

### Inject a Malformed Record to Test DLQ:
```powershell
.\.venv\Scripts\Activate.ps1
python scripts/demo/inject_fault.py --scenario corrupt_payload
```

