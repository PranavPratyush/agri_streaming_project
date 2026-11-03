# Teammate Demonstration Day Checklist
**Project:** AgriKafka-Agent Streaming Platform  
**Target User:** Presenter / Teammate demonstrating the live platform  
**Estimated Run Time:** 10–15 Minutes  

---

## 1. Pre-Flight Checklist (10 Minutes Before Presentation)

Complete these verification steps before calling the evaluators over:

- [ ] **Docker Desktop is Running**: Ensure the whale icon in the Windows notification tray is steady (not animated).
- [ ] **WSL 2 Engine is Healthy**: Run `wsl -l -v` in PowerShell. Both `Ubuntu` and `docker-desktop` should report state `Running`.
- [ ] **PowerShell Virtual Environment Active**: Run `.\.venv\Scripts\Activate.ps1`. Prompt shows `(.venv)`.
- [ ] **All 5 Containers Running**:
  ```powershell
  docker-compose ps
  ```
  Confirm all 5 services report `Up` or `Up (healthy)`.
- [ ] **Grafana Accessible**: Open browser to [http://127.0.0.1:3001](http://127.0.0.1:3001). Log in with `admin` / `agri_admin_dev_insecure`.
- [ ] **Prometheus Scraping**: Open browser to [http://127.0.0.1:9090/targets](http://127.0.0.1:9090/targets). Confirm targets are green.

---

## 2. Terminal Layout Strategy (Open 4 Windows)

Organize your screen with your browser on the left half and 4 PowerShell terminals arranged on the right half:

### Terminal 1: Infrastructure & Topics
```powershell
cd C:\Users\<YourUsername>\Projects\agri_streaming_project
docker exec agrikafka-broker-dev /opt/kafka/bin/kafka-topics.sh --bootstrap-server 127.0.0.1:9092 --list
```
*Purpose:* Shows Kafka KRaft status and topic inventory.

### Terminal 2: PySpark Structured Streaming Logs
```powershell
cd C:\Users\<YourUsername>\Projects\agri_streaming_project
docker logs -f agrikafka-stream-processor
```
*Purpose:* Displays real-time micro-batch progress, watermarks, and schema enforcement.

### Terminal 3: Kafka Console Stream Monitor
```powershell
cd C:\Users\<YourUsername>\Projects\agri_streaming_project
docker exec -it agrikafka-broker-dev /opt/kafka/bin/kafka-console-consumer.sh `
  --bootstrap-server 127.0.0.1:9092 `
  --topic agri.sensor-readings `
  --from-beginning
```
*Purpose:* Shows live messages arriving on the topic as soon as ingestion fires.

### Terminal 4: Command Execution Terminal
```powershell
cd C:\Users\<YourUsername>\Projects\agri_streaming_project
.\.venv\Scripts\Activate.ps1
```
*Purpose:* The active terminal where you run ingestion, replay, and fault injection.

---

## 3. Live Demonstration Sequence (Step-by-Step)

### Step 1: Prove System Architecture (1–2 mins)
- Point to **Grafana Dashboard `01 - System Overview`** (`http://127.0.0.1:3001/d/agri-01-system-overview/01-system-overview`).
- Highlight:
  - Single-broker KRaft architecture (zero ZooKeeper dependency).
  - TimescaleDB hypertable persistence.
  - Sub-second pipeline latency.

### Step 2: Ingest Live Physical Hardware Telemetry (3–4 mins)
In **Terminal 4**, run:
```powershell
python services/ingestion/src/agri_ingestion/cli.py live-osm --station-id 689b2bdc569c2d0007586ae9 --once
```
- Watch **Terminal 3**: Raw JSON observation arrives instantly with RFC 3339 UTC timestamp.
- Watch **Terminal 2**: PySpark processes the micro-batch and updates the watermark.
- **Talking Point:** *"We are ingesting real-world physical telemetry from station Sarvamangalam in Kolar, Karnataka. Dual timestamps preserve both physical sample time and platform arrival time."*

### Step 3: Demonstrate Fault-Tolerant Dead-Letter Queue (DLQ) (3–4 mins)
In **Terminal 4**, run the fault injection script:
```powershell
python scripts/demo/inject_fault.py --scenario corrupt_payload
```
- Look at **Terminal 2**: PySpark catches the schema contract violation (`StreamValidationError`).
- Notice: The stream processor does **NOT** crash; it continues executing.
- Inspect the DLQ in **Terminal 4**:
  ```powershell
  docker exec agrikafka-broker-dev /opt/kafka/bin/kafka-console-consumer.sh `
    --bootstrap-server 127.0.0.1:9092 `
    --topic agri.dead-letter-queue `
    --from-beginning `
    --max-messages 1
  ```
- **Talking Point:** *"Malformed or poisoned packets are safely quarantined with root-cause diagnostic metadata, protecting downstream agronomic models from corrupt state."*

### Step 4: Show Analytical Persistence in TimescaleDB (2 mins)
In **Terminal 4**, query TimescaleDB directly:
```powershell
docker exec agrikafka-timescaledb psql -U agri_admin -d agrikafka -c `
  "SELECT observed_variable, numeric_value, unit, event_time FROM observations ORDER BY event_time DESC LIMIT 5;"
```
- **Talking Point:** *"Observations are stored in native TimescaleDB hypertables partitioned by event time with idempotent deduplication."*

### Step 5: Wrap-up on Operational Dashboards (2 mins)
- Switch browser to **Grafana Dashboard `05 - Data Quality & Sensor Health`**.
- Show the sensor health breakdown, spike anomaly rates, and DLQ drop counters.

---

## 4. Emergency Fallback Procedures

### Fallback A: Live OpenSenseMap Station API Times Out or Campus Wi-Fi Blocks It
**Action:** Do not waste time debugging the Wi-Fi. Immediately switch to the deterministic high-speed historical replay:
```powershell
python services/ingestion/src/agri_ingestion/cli.py replay --speed 50
```
**Talking Point:** *"Because live station APIs are subject to external ISP rate-limiting, our architecture includes a high-speed historical replay adapter reproducing verified Kolar weather telemetry at 50x wall-clock speed."*

### Fallback B: Port 3001 or 9092 is Already in Use
```powershell
# Identify process using port
Get-NetTCPConnection -LocalPort 3001 | Select-Object OwningProcess
Stop-Process -Id <OwningProcessId> -Force
```

### Fallback C: Quick Restart of Stream Processor
If PySpark stops reporting progress:
```powershell
docker restart agrikafka-stream-processor
docker logs -f agrikafka-stream-processor
```
*(PySpark will resume automatically from its durable checkpoint volume without data loss).*

