# AgriKafka-Agent: Professor-Facing Live Demonstration Runbook (Stages 0–19)

**Target Audience:** Professor Evaluation Panel (Stream Processing & Analytics / Agentic AI)  
**Demonstration Mode:** Live Technical Walkthrough & Pipeline Execution  
**Duration:** 15–20 minutes  
**Working Directory:** `c:\Users\prana\OneDrive\Desktop\spa_pbl\agri_streaming_project`  
**Execution Environment:** Windows Laptop (PowerShell 5.1/7 or VS Code Terminal) + Python virtual environment (`.venv`)  

---

## 1. Quick Pre-Flight Checklist

Before opening the presentation:
1. Ensure your terminal is in the project root:
   ```powershell
   cd c:\Users\prana\OneDrive\Desktop\spa_pbl\agri_streaming_project
   ```
2. Verify virtual environment Python:
   ```powershell
   .venv\Scripts\python.exe --version
   ```
   *Expected:* `Python 3.13.x` (or `3.11.x`).
3. Check target port availability (all should be clear):
   ```powershell
   Get-NetTCPConnection -LocalPort 9092, 5432, 8000, 5173, 9090, 3001 -ErrorAction SilentlyContinue
   ```

---

## 2. Timed Demonstration Sequence (15–20 Minutes)

| Phase | Time | Demonstration Content | Key Screens & Commands | What to Emphasize to Professors |
|---|---|---|---|---|
| **Phase 1** | 00:00 – 02:30 | **Architecture & Scientific Grounding** | Show `docs/architecture/ARCHITECTURE_V1.md` | Dual-engine separation: deterministic physics (FAO-56) vs bounded multi-agent reasoning. Zero autonomous physical actuation. |
| **Phase 2** | 02:30 – 05:00 | **Live Ingestion & Fault-Tolerant Replay** | Run `live-osm` polling & synthetic `inject` | Real physical telemetry (Sarvamangalam station) with 19s latency; graceful DLQ routing on network drop. |
| **Phase 3** | 05:00 – 07:30 | **Sensor Health Forensics & Physics Thresholds** | Run `risk-engine cli audit-thresholds` | 6 deterministic detectors; natural flatline differentiation (rain zeroes & dry plateaus); WMO/IMD grounding. |
| **Phase 4** | 07:30 – 12:00 | **Multi-Agent Supervisor & Specialist Agents** | Run `investigate` CLI (Healthy vs Faulty) | 6 specialist agents with typed Pydantic contracts; shared state; agent message protocol; Critic safety revision loop. |
| **Phase 5** | 12:00 – 14:30 | **Agronomy RAG Knowledge Retrieval** | Run `agri_agronomy_rag query` | ChromaDB vector search (ONNX 384d) over audited Indian extension corpus (FAO-56, ICAR, UASB); citation verification. |
| **Phase 6** | 14:30 – 17:30 | **Farmer PWA & Human Review Lifecycle** | Run PWA preview & Backend API | React 18 + Vite PWA; bilingual EN/KN; 5-milestone agent transparency; 8-state review lifecycle; idempotent approval. |
| **Phase 7** | 17:30 – 20:00 | **Persistence, Observability & Verification** | Run Pytest test suite & show Grafana config | 173 passing tests; TimescaleDB hypertables; 7 provisioned Grafana dashboards; 6 actionable Prometheus alerts. |

---

## 3. Step-by-Step Copy-Paste Commands

### Step 1: Scientific Thresholds & Grounding Audit (Phase 1 & 3)
Run in PowerShell:
```powershell
.venv\Scripts\python.exe services/risk-engine/src/agri_risk_engine/cli.py audit-thresholds
```
- **What it does:** Prints the deterministic sensor physics table and rate-of-change thresholds.
- **Expected Output:** Table showing Stuck Variance Epsilon ($10^{-4}$), Stuck Diurnal Window (12h), Temperature Rate of Change ($5^\circ\text{C/min}$), and Soil Moisture Rate of Change ($0.08\,\text{m}^3/\text{m}^3/\text{min}$) with scientific citations to WMO-No. 8 and UAS Bangalore Alfisol physics.

---

### Step 2: Live Ingestion & Physical Telemetry (Phase 2)
Run in PowerShell:
```powershell
.venv\Scripts\python.exe services/ingestion/src/agri_ingestion/cli.py live-osm --station-id 689b2bdc569c2d0007586ae9 --once --dry-run
```
- **What it does:** Polls live openSenseMap station Sarvamangalam (`689b2bdc569c2d0007586ae9`, Lat 12.00°N, Lon 79.80°E).
- **Expected Output:** 5 normalized observation events (`temperature_2m`, `relative_humidity_2m`, `precipitation`, `wind_speed_10m`, `barometric_pressure`) with `is_synthetic: false`, latency under 30s, and canonical schema version `1.0.0`.
- **Offline / Sandbox Fallback:** If internet is disconnected, demonstrate the injected dry-down scenario:
  ```powershell
  .venv\Scripts\python.exe services/ingestion/src/agri_ingestion/cli.py inject --scenario drought_drydown_ragi --field-id field-kolar-001 --steps 3 --dry-run
  ```

---

### Step 3: Agronomy RAG Vector Knowledge Retrieval (Phase 5)
Run in PowerShell:
```powershell
.venv\Scripts\python.exe packages/agronomy-rag/src/agri_agronomy_rag/cli.py query "ragi protective irrigation drought" --limit 3
```
- **What it does:** Queries the Chroma persistent vector database over the 5 audited extension sources.
- **Expected Output:**
  - Status: `SUCCESS`
  - Corpus Version: `v1.0-1b95cf635c01`
  - Model: `sentence-transformers/all-MiniLM-L6-v2 (ONNX) (384d)`
  - Matches: `ICAR-CRIDA-DRYLAND-2019:SEC03:CH01`, `UASB-POP-RAGI-2022:SEC03:CH01` with relevance scores $> 0.55$ and accredited excerpts.

---

### Step 4: Multi-Agent Investigation Execution (Phase 4 — Core Professor Requirement)

#### 4A. Healthy Observation Investigation:
```powershell
.venv\Scripts\python.exe services/alert-investigator/src/agri_investigator/cli.py investigate --field-id field-kolar-001 --severity HIGH --sensor-health HEALTHY
```
- **What it demonstrates:**
  1. `sensor_reliability_agent` & `field_context_agent` run in parallel.
  2. `crop_risk_analyst` aggregates telemetry and crop vulnerability.
  3. `agronomy_knowledge_agent` queries Chroma vector DB.
  4. `agricultural_advisory_agent` generates grounded deficit drip irrigation advisory.
  5. `critic_safety_agent` audits citations, chemical policy, and actuation safety.
  6. Final state: `awaiting_human_review`, citations verified (`TNAU-AGRITECH-RAGI-2020:SEC02:CH01`), deterministic safety gate: `Passed: True`.

#### 4B. Sensor-Fault Safety Abstention:
```powershell
.venv\Scripts\python.exe services/alert-investigator/src/agri_investigator/cli.py investigate --field-id field-kolar-001 --severity HIGH --sensor-health FAULTY
```
- **What it demonstrates:**
  - `sensor_reliability_agent` immediately flags `STUCK_VALUE_DETECTED`.
  - Supervisor halts downstream agricultural advisory generation to prevent hallucinated farm interventions.
  - Final decision: `ABSTAINED_SENSOR_FAULT`.

---

### Step 5: Farmer PWA & Backend API Execution (Phase 6)

#### Terminal 1 — Start Backend API:
```powershell
.venv\Scripts\python.exe -m uvicorn agri_api.main:app --host 127.0.0.1 --port 8000
```
- Verify in browser: `http://127.0.0.1:8000/docs` (OpenAPI Swagger UI with 34 interactive endpoints).
- Probe liveness: `http://127.0.0.1:8000/healthz`.

#### Terminal 2 — Start Farmer PWA:
```powershell
npm run preview --prefix apps/farmer-pwa
```
- Open browser: `http://localhost:5173`.
- **Demonstrate on PWA:**
  1. **Overview Screen:** Real-time conditions, moisture depletion warning, and sensor reliability card.
  2. **Trends Screen:** 24h & 7d soil moisture curve against the FAO-56 critical threshold ($0.166\,\text{m}^3/\text{m}^3$).
  3. **Alert Detail Screen:** Multi-agent milestone progress tracker (Sensor Reliability -> Field Context -> Risk Analysis -> Agronomy RAG -> Critic Review).
  4. **Advisories Screen:** One-tap `Approve`, `Reject`, or `Request Inspection` with idempotency token and feedback dialog.
  5. **Bilingual Toggle:** Switch between English and Kannada (ಕನ್ನಡ).

---

### Step 6: Full Verification Test Suite (Phase 7)
Run in PowerShell:
```powershell
.venv\Scripts\python.exe -m pytest tests/unit/ tests/contract/ -q
```
- **Expected Output:** `173 passed, 1 skipped` in ~15 seconds.
- Demonstrates 100% test coverage across contracts, ingestion, stream processing, sensor health, risk calculations, persistence, RAG, multi-agent supervisor, FastAPI API, and notifications.

---

## 4. Docker Full-Stack Startup (When Docker Desktop is Active)

When Docker Desktop is running on host, you can launch the containerized stack:
```powershell
docker compose up -d kafka timescaledb prometheus grafana
```
- **Verify containers:** `docker compose ps`
- **Initialize Kafka topics:**
  ```powershell
  .venv\Scripts\python.exe infra/kafka/init_topics.py --bootstrap-server 127.0.0.1:9092
  ```
- **Open Grafana:** `http://127.0.0.1:3001` (User: `admin`, Password: `agri_admin_dev_insecure`).
- **Open Prometheus:** `http://127.0.0.1:9090`.

