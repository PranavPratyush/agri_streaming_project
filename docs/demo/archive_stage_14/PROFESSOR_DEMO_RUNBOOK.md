# Professor Demonstration Runbook (10–15 Minutes)
**System:** AgriKafka-Agent Streaming Platform  
**Target Audience:** Stream Processing and Analytics (SPA) Professors  
**Hardware / OS:** Windows 10/11 with Docker Desktop (WSL 2 backend)  
**Host Environment:** Local Python 3.10+ Virtual Environment (`.venv`)  

---

## 1. Pre-Demo Setup & Verification Checklist (5 Minutes Before)

Ensure Docker Desktop is running before launching terminal windows.

```powershell
# Verify Docker is operational
docker ps
```

### Pre-allocated Ports Summary
- **Kafka KRaft Broker:** `127.0.0.1:9092`
- **TimescaleDB / PostgreSQL:** `127.0.0.1:5432`
- **Prometheus Scraper:** `127.0.0.1:9090`
- **Grafana Dashboards:** `127.0.0.1:3001` (User: `admin` / Password: `agri_admin_dev_insecure`)

---

## 2. Terminal Layout Setup (5 Dedicated Terminals)

Arrange 5 PowerShell terminals side-by-side on your screen:

### Terminal 1: Infrastructure & Services (Root Dir)
```powershell
cd c:\Users\prana\OneDrive\Desktop\spa_pbl\agri_streaming_project
docker-compose up -d
docker-compose ps
```
*Expected Output:*
All 5 containers (`agrikafka-broker-dev`, `agrikafka-timescaledb`, `agrikafka-prometheus`, `agrikafka-grafana`, `agrikafka-stream-processor`) in state `Up` or `Up (healthy)`.

### Terminal 2: Stream Processor Logs (PySpark Monitor)
```powershell
cd c:\Users\prana\OneDrive\Desktop\spa_pbl\agri_streaming_project
docker logs -f agrikafka-stream-processor
```
*Expected Output:*
Periodic micro-batch triggers, watermark updates, and structured aggregation logs.

### Terminal 3: Kafka Console Consumer (Raw Telemetry Topic)
```powershell
cd c:\Users\prana\OneDrive\Desktop\spa_pbl\agri_streaming_project
docker exec -it agrikafka-broker-dev /opt/kafka/bin/kafka-console-consumer.sh `
  --bootstrap-server 127.0.0.1:9092 `
  --topic agri.sensor-readings `
  --from-beginning
```
*Expected Output:*
Real-time JSON streams as observations arrive from physical sensors or replay.

### Terminal 4: Ingestion & Control Execution (Active Workspace)
```powershell
cd c:\Users\prana\OneDrive\Desktop\spa_pbl\agri_streaming_project
.\.venv\Scripts\Activate.ps1
```
*(This terminal is where you run live station polls, historical replays, and fault injections.)*

### Terminal 5: TimescaleDB SQL Inspection
```powershell
cd c:\Users\prana\OneDrive\Desktop\spa_pbl\agri_streaming_project
docker exec -it agrikafka-timescaledb psql -U agri_admin -d agrikafka
```
*(Ready for interactive queries during the demo.)*

---

## 3. Minute-by-Minute Demonstration Sequence (12 Minutes Total)

| Minute | Stage & Action | Demonstration Action | What to Show on Screen | Speaking Point |
| :---: | :--- | :--- | :--- | :--- |
| **00:00 – 01:30** | **System Architecture & Context** | Open Grafana `01 - System Overview` in browser (`http://127.0.0.1:3001`). | Grafana overview panel showing zero-broker ZooKeeper KRaft architecture and live metrics. | Introduce project: Real-time decision support for Finger Millet (Ragi GPU-28) in Kolar, Karnataka. Explain why streaming is essential (timely moisture stress vs. batch delay). |
| **01:30 – 03:00** | **Infrastructure & Topic Partitioning** | In Terminal 1, run topic list command: `docker exec agrikafka-broker-dev /opt/kafka/bin/kafka-topics.sh --bootstrap-server 127.0.0.1:9092 --list`. | Terminal output showing 9 canonical topics (`agri.sensor-readings`, `agri.validated-observations`, etc.). | Explain topic design as code, 3-partition parallelism for sensor telemetry, keying by `field_id:variable` to guarantee in-order delivery per sensor. |
| **03:00 – 05:00** | **Live Physical Telemetry Ingestion** | In Terminal 4, execute live openSenseMap ingest: `python apps/ingestion-service/src/agri_ingestion/adapters/live_station.py`. | Terminal 3 shows incoming JSON message. Terminal 4 prints 5 physical variables (Temp, Humidity, Rain, Wind, Pressure) from station `Sarvamangalam`. | Emphasize provenance: Live physical hardware in Kolar. Explain SI normalization and dual timestamp preservation (`event_time` vs `ingestion_time`). |
| **05:00 – 07:00** | **PySpark Structured Streaming** | Switch to Terminal 2 (`docker logs -f agrikafka-stream-processor`). | PySpark micro-batch execution logs showing batch completion, watermark advancement (10-min bounded state), and output sink write. | Detail event-time semantics, watermarking to handle late arrival without unbounded state growth, and aggregation into sliding windows. |
| **07:00 – 09:00** | **Fault Tolerance & Dead-Letter Queue (DLQ)** | In Terminal 4, execute injected bad payload: `python scripts/demo/inject_fault.py --scenario corrupt_payload`. | In Terminal 2, Spark catches the validation error without crashing. In Terminal 3 (or DLQ consumer), record arrives in `agri.dead-letter-queue` with stack trace. | Highlight system resilience: bad sensor packets cannot halt the pipeline; they are quarantined with root-cause diagnostic metadata for sensor forensics. |
| **09:00 – 10:30** | **TimescaleDB Hypertables & Analytical Queries** | In Terminal 5, run SQL: `SELECT observed_variable, numeric_value, unit, event_time FROM observations ORDER BY event_time DESC LIMIT 5;`. | Tabular SQL output showing stored records, UTC timestamps, and idempotency guarantees. | Explain TimescaleDB hypertables: automatic time-range chunking for time-series queries while retaining full SQL join capability with crop metadata. |
| **10:30 – 12:00** | **Grafana Observability & Q&A Wrap-Up** | Switch browser to Grafana `03 - Spark Streaming & Checkpoint Health` and `05 - Data Quality & Sensor Health`. | Active graph lines showing input rate, processing latency, and data quality distribution. | Summarize end-to-end telemetry flow. Invite professors' questions on state store durability, out-of-order event handling, and scaling. |

---

## 4. Teardown & Reset Procedure

To cleanly stop the demonstration environment after your presentation:

```powershell
# Stop all Docker containers cleanly
docker-compose down

# (Optional) Remove volumes if a total fresh reset is desired:
# docker-compose down -v
```

