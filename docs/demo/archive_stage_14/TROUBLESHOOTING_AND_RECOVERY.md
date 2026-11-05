# Troubleshooting and Emergency Recovery Guide
**System:** AgriKafka-Agent  
**Target Environment:** Local Demonstration & Examination  

---

## 1. Quick Emergency Reset (The "Nuclear" Option)

If a service is in an unrecoverable state right before or during a presentation:

```powershell
# 1. Stop all containers cleanly
docker-compose down

# 2. Start all containers in detached mode
docker-compose up -d

# 3. Wait 15 seconds for Kafka and TimescaleDB health checks to pass, then verify
docker-compose ps
```

---

## 2. Common Scenarios & Instant Solutions

### Scenario A: Docker Desktop "Named Pipe" Connection Failure on Windows
**Symptom:**  
`failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`

**Cause:**  
Docker Desktop background process was terminated or suspended by Windows power management.

**Resolution:**  
Start Docker Desktop daemon using PowerShell:
```powershell
Start-Process -FilePath "C:\Users\prana\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe"
```
Wait 20 seconds for the engine to initialize, then verify with `docker ps`.

---

### Scenario B: Live openSenseMap API Unreachable (Offline Fallback)
**Symptom:**  
`requests.exceptions.ConnectionError` or HTTP `503 Service Unavailable` when running `live_station.py` during campus network outage.

**Remedy / Offline Fallback:**  
Do **NOT** attempt to debug the campus Wi-Fi proxy. Switch seamlessly to the verified historical replay adapter:
```powershell
python apps/ingestion-service/src/agri_ingestion/adapters/replay.py `
  --file data/historical/kolar_historical_weather.csv `
  --speed 50
```
*Speaking Point:* "To demonstrate continuous stream processing during external provider network maintenance, we activate our high-speed replay adapter running at 50x wall-clock speed against historical telemetry recorded for Kolar."

---

### Scenario C: Kafka Port Conflict (`127.0.0.1:9092 already in use`)
**Symptom:**  
`agrikafka-broker-dev` fails to start with `port is already allocated`.

**Resolution:**
```powershell
# Identify process holding port 9092
Get-NetTCPConnection -LocalPort 9092 | Select-Object OwningProcess

# Terminate orphaned process or previous Kafka container
Stop-Process -Id <OwningProcessId> -Force
```

---

### Scenario D: PySpark Stream Processor Out of Memory or Exited
**Symptom:**  
`docker logs agrikafka-stream-processor` shows container exited with code 137 (OOM) or Py4J network error.

**Resolution:**  
1. Restart the stream processor container:
   ```powershell
   docker restart agrikafka-stream-processor
   ```
2. PySpark will automatically resume from its durable checkpoint on volume `spark-checkpoints` without reprocessing committed offsets or duplicating records.

---

### Scenario E: TimescaleDB Connection Refused
**Symptom:**  
`psql: error: connection to server on socket "/var/run/postgresql/.s.PGSQL.5432" failed: FATAL: role "agri_admin" does not exist`

**Resolution:**  
Ensure you specify the correct credentials:
- User: `agri_admin`
- Database: `agrikafka`
- Host: `127.0.0.1` (or inside container via `docker exec -it agrikafka-timescaledb psql -U agri_admin -d agrikafka`)
If migrations were wiped, re-run Alembic migration:
```powershell
alembic upgrade head
```

---

## 3. Pre-Flight Verification Script (One Command Check)

Run this one-liner before the professors arrive to confirm all subsystems are green:

```powershell
docker-compose ps; `
curl.exe -s http://127.0.0.1:3001/api/health; Write-Output ""; `
curl.exe -s http://127.0.0.1:9090/-/healthy; Write-Output ""; `
docker exec agrikafka-broker-dev /opt/kafka/bin/kafka-topics.sh --bootstrap-server 127.0.0.1:9092 --list
```

