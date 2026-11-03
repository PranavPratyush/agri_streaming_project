# AgriKafka-Agent: Fault-Tolerant, Real-Time Agricultural Risk Monitoring and Decision Support

> **Course:** AI372IA — Stream Processing and Analytics  
> **Team:** Aanish Khan, Daksh Chauhan, Pranav Pratyush  
> **Faculty Guides:** Dr. Vijayalakshmi M N and Dr. S. Anupama Kumar  
> **Status:** Stage 9 Complete (Multi-Source Ingestion Layer & Event Contracts Established)  

---

## 1. Project Overview

AgriKafka-Agent is a real-time agricultural monitoring and decision-support system that combines live environmental telemetry, data-quality and sensor-health assessment, crop-context-aware risk detection, and a bounded tool-using AI investigator that produces evidence-grounded recommendations for human approval.

### System Invariants
- **Kafka is the Event Backbone:** High-throughput partitioned topics for all telemetry, detections, actions, and feedback.
- **PySpark Structured Streaming:** Windowed aggregations, watermarking, joins, and feature engineering.
- **Deterministic Services:** Sensor-health forensics and crop-risk math are deterministic code, never LLM inference.
- **Bounded AI Investigator:** Evaluates only candidate alerts that survive stream detection filters. No LLM calls on raw telemetry.
- **Strict UI Separation:** Farmer PWA for field decisions; Grafana for operations and engineering telemetry.
- **Zero Autonomous Actuation:** Recommendations require explicit farmer approval before action is logged.

---

## 2. Documentation & Development Quick Links

- **Canonical Project Handover:** [`docs/project/reference/AgriKafka-Agent_Development_Handover.md`](docs/project/reference/AgriKafka-Agent_Development_Handover.md)
- **Project Brief & Source of Truth:** [`docs/project/PROJECT_BRIEF.md`](docs/project/PROJECT_BRIEF.md)
- **Ingestion Service Documentation:** [`services/ingestion/README.md`](services/ingestion/README.md)
- **Kafka Topology Specification:** [`docs/architecture/KAFKA_TOPOLOGY.md`](docs/architecture/KAFKA_TOPOLOGY.md)
- **Event Contracts Specification:** [`docs/architecture/EVENT_CONTRACTS.md`](docs/architecture/EVENT_CONTRACTS.md)
- **Open Architectural Decisions:** [`docs/project/OPEN_DECISIONS.md`](docs/project/OPEN_DECISIONS.md)
- **Environment Audit Report:** [`docs/development/ENVIRONMENT_AUDIT.md`](docs/development/ENVIRONMENT_AUDIT.md)
- **Skill Usage Transparency Log:** [`docs/development/SKILL_USAGE_LOG.md`](docs/development/SKILL_USAGE_LOG.md)
- **Development Build Log:** [`docs/development/BUILD_LOG.md`](docs/development/BUILD_LOG.md)
- **Developer Guide & Rules:** [`DEVELOPMENT.md`](DEVELOPMENT.md)

---

## 3. Local Kafka Infrastructure (Stage 8)

The project includes a pinned, single-broker Apache Kafka `3.8.0` in KRaft consensus mode (no ZooKeeper), bound strictly to `127.0.0.1:9092` with named persistent storage.

### 3.1 Prerequisites
- Docker Desktop (WSL2 backend active)
- Python 3.11/3.13 with `uv` (`uv venv` and `uv sync`)

### 3.2 Quickstart Commands

```powershell
# Start Kafka container and wait for healthy KRaft status
docker compose up -d kafka

# Idempotently provision the 9 canonical Kafka topics
uv run python infra/kafka/init_topics.py --bootstrap-server 127.0.0.1:9092

# Execute end-to-end Producer/Consumer smoke test
uv run python infra/kafka/smoke_test.py 127.0.0.1:9092

# Verify persistence across container restart (drill)
uv run python infra/kafka/verify_persistence.py 127.0.0.1:9092

# Safe shutdown (preserves persistent volumes)
docker compose down
```

Or use the provided management scripts:
- **Windows PowerShell:** `.\infra\kafka\manage.ps1 [start|init|list|smoke|persist|stop]`
- **Linux/macOS Bash:** `./infra/kafka/manage.sh [start|init|list|smoke|persist|stop]`

---

## 4. Repository Structure

```text
agri_streaming_project/
├── .agents/                      # Antigravity operating rules and skills
│   ├── rules/                    # 6 architectural, safety & transparency rules
│   └── skills/                   # External and custom skills
├── apps/
│   └── farmer-pwa/               # Mobile-first responsive PWA for farmers
├── data/
│   ├── historical/               # Historical baseline datasets (Open-Meteo)
│   └── scenarios/                # Labeled fault & stress scenario manifests
├── docs/
│   ├── architecture/             # Topology & Event Contracts specifications
│   ├── decisions/                # Architectural Decision Records (ADRs)
│   ├── development/              # Environment audit, skill usage & build logs
│   ├── experiments/              # Benchmark plans & empirical results
│   └── project/                  # Project brief, handover, and open decisions
├── infra/
│   ├── docker/                   # Docker Compose topologies (dev & cluster)
│   ├── grafana/                  # Dashboards and alert panels
│   ├── kafka/                    # KRaft cluster configuration & topic init
│   └── prometheus/               # Scrape targets and metric rules
├── knowledge/                    # Agronomy references (FAO-56, ICAR) & Chroma DB
├── packages/
│   ├── event-contracts/          # Canonical Pydantic schemas & topic definitions
│   └── shared-python/            # Reusable logging, config, and Kafka helpers
├── services/
│   ├── alert-investigator/       # Bounded tool-calling AI triage agent
│   ├── api/                      # FastAPI backend service
│   ├── ingestion/                # Telemetry connectors & replay producer
│   ├── notification-worker/      # Telegram & PWA notification dispatcher
│   ├── risk-engine/              # Deterministic anomaly & sensor-health service
│   └── stream-processor/         # PySpark Structured Streaming application
├── tests/
│   ├── contract/                 # Schema & serialization contract tests (17/17 pass)
│   ├── integration/              # End-to-end Kafka & DB integration tests
│   ├── resilience/               # Chaos drills (broker kill, worker crash)
│   ├── scenarios/                # ~60 labeled scenario detector benchmarks
│   └── unit/                     # Isolated deterministic unit tests
├── .env.example                  # Safe environment variable template
├── .gitignore                    # Monorepo git exclusion rules
├── docker-compose.yml            # Single-broker KRaft Kafka dev profile
├── pyproject.toml                # uv workspace & project configuration
└── requirements.txt              # Phase 1 EDA legacy dependencies
```

---

## 5. Phase 1: Historical Dataset Acquisition & EDA (Preserved)

*The baseline data acquisition and exploratory analysis established in Phase 1 remain fully preserved:*

1. Pull 2 years of **hourly Open-Meteo historical data** for 10 Karnataka virtual fields.
2. Preserve timestamps and field IDs for replay.
3. Run baseline EDA before any fault/stress injection.
4. Generate the charts requested for Phase 1.
5. Produce files that parameterize the fault injector.

### Dataset Design
- **Period:** 2024-10-05 through 2026-10-04 (hourly cadence)
- **Locations:** 10 representative Karnataka district/city coordinates
- **Core variables:** `temperature_2m`, `relative_humidity_2m`, `dew_point_2m`, `precipitation`, `vapour_pressure_deficit`, `soil_moisture_0_to_7cm`, `wind_speed_10m`
- **Timezone:** Asia/Kolkata
- **Total Rows:** 175,200 (10 fields × 730 days × 24 hours)

### Run Phase 1 Locally
```bash
# Windows
.venv\Scripts\activate
pip install -r requirements.txt

python acquire_open_meteo.py
python eda_open_meteo.py
```
Outputs are stored in `eda_output/` and compiled in `AgriKafka_EDA_Report/`.

