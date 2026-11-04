# AgriKafka-Agent: Live Demonstration Troubleshooting & Recovery Runbook

**Purpose:** Rapid Remediation and Safe Failover Guide for Live Evaluation  
**Safety Invariant:** Never delete persistent volumes or wipe database tables during routine recovery.  

---

## 1. Quick Emergency Triage Matrix

| Symptom / Failure | Root Cause | Immediate Safe Remediation |
|---|---|---|
| **openSenseMap Ingestion Fails with `NameResolutionError`** | Host internet disconnected or DNS blocked by sandbox. | Run Ingestion with `--dry-run` or switch to the synthetic replay adapter (`inject --scenario drought_drydown_ragi`). |
| **Kafka Connection Refused (`127.0.0.1:9092`)** | Docker Desktop engine is stopped or container crashed. | Start container: `docker compose up -d kafka`. If Docker unavailable, use CLI `--dry-run` modes which verify pipeline logic without network brokers. |
| **TimescaleDB Connection Refused (`127.0.0.1:5432`)** | TimescaleDB container is not running. | Backend API automatically falls back to `LocalMemoryRepository`. All API endpoints continue functioning seamlessly. |
| **PWA Shows "Network Error" on Data Fetching** | Backend API server is not running on port 8000. | Start API: `.venv\Scripts\python.exe -m uvicorn agri_api.main:app --port 8000`. The PWA also has built-in offline mock fixtures. |
| **Multi-Agent Run Exceeds Max Revisions** | Critic detected repeated policy or citation mismatches. | System terminates safely with `ABSTAINED_MAX_REVISIONS_EXCEEDED` and logs audit trail. This is expected defensive behavior. |
| **Port Conflict on Port 8000, 5173, or 3001** | Previous session left orphaned background process. | Identify and terminate owning PID: `Get-Process -Id (Get-NetTCPConnection -LocalPort <port>).OwningProcess | Stop-Process -Force`. |

---

## 2. Safe Fallback Demonstration Plan (Zero Internet / Zero Docker)

If the examination room has no internet access or Docker Desktop fails to initialize, execute the **100% Offline Standalone Profile**:

### Step 1: Execute Standalone Ingestion
```powershell
.venv\Scripts\python.exe services/ingestion/src/agri_ingestion/cli.py inject --scenario drought_drydown_ragi --field-id field-kolar-001 --steps 3 --dry-run
```
- Explains: Canonical Pydantic event validation, ISO-8601 UTC timestamps, provenance tagging, and idempotency key computation.

### Step 2: Execute Standalone Sensor Health Audit
```powershell
.venv\Scripts\python.exe services/risk-engine/src/agri_risk_engine/cli.py audit-thresholds
```
- Explains: 6 deterministic detectors, stuck variance floor ($10^{-4}$), and natural flatline differentiation.

### Step 3: Execute Standalone RAG Retrieval
```powershell
.venv\Scripts\python.exe packages/agronomy-rag/src/agri_agronomy_rag/cli.py query "ragi protective irrigation drought" --limit 3
```
- Explains: ChromaDB persistent vector search (ONNX 384d) over audited local Indian extension corpus.

### Step 4: Execute Standalone Multi-Agent Investigation
```powershell
.venv\Scripts\python.exe services/alert-investigator/src/agri_investigator/cli.py investigate --field-id field-kolar-001 --severity HIGH --sensor-health HEALTHY
```
- Explains: Supervisor coordination, parallel context acquisition, crop risk modeling, advisory generation, and Critic safety review.

### Step 5: Execute Standalone Backend & PWA
```powershell
# Terminal 1:
.venv\Scripts\python.exe -m uvicorn agri_api.main:app --host 127.0.0.1 --port 8000

# Terminal 2:
npm run preview --prefix apps/farmer-pwa
```
- Explains: 10 core screens, responsive mobile layout, bilingual Kannada/English support, 5-milestone investigation transparency, and human review actions.

---

## 3. Service Lifecycle Management Commands

### 3.1 Graceful Stack Shutdown
```powershell
# Stop application servers
# (Press Ctrl+C in Uvicorn and Vite terminals)

# Stop Docker infrastructure cleanly (preserving named volumes)
docker compose down
```

### 3.2 Restarting Individual Services
- **Restart Kafka only:**
  ```powershell
  docker compose restart kafka
  ```
- **Restart TimescaleDB only:**
  ```powershell
  docker compose restart timescaledb
  ```
- **Restart Prometheus / Grafana:**
  ```powershell
  docker compose restart prometheus grafana
  ```

### 3.3 Inspecting Container Logs
- **Kafka logs:** `docker logs --tail 50 -f agrikafka-broker-dev`
- **TimescaleDB logs:** `docker logs --tail 50 -f agrikafka-timescaledb`
- **Spark streaming logs:** `docker logs --tail 50 -f agrikafka-stream-processor`

### 3.4 Checking Persistent Volumes
```powershell
docker volume ls --filter name=agrikafka
```
*Expected named volumes:*
- `agrikafka_dev_data` (Kafka commit logs)
- `agrikafka_spark_checkpoints` (PySpark state store & offsets)
- `agrikafka_timescale_dev_data` (PostgreSQL / TimescaleDB hypertables)
- `agrikafka_prometheus_data` (Prometheus TSDB)
- `agrikafka_grafana_data` (Grafana dashboards & state)

