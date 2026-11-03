# AgriKafka-Agent — Open Decisions Register

**Project:** AgriKafka-Agent: Fault-Tolerant, Real-Time Agricultural Risk Monitoring and Decision Support  
**Created:** Stage 0 (Baseline Setup)  
**Updated:** Stage 6 (Live Data-Source Verification & Architecture Sign-Off)  
**Status:** Active  

This document tracks all architectural, technology, agronomic, and infrastructure decisions for the AgriKafka-Agent project. Every architectural decision is formally evaluated, documented in an Architectural Decision Record (ADR) under `docs/decisions/`, and approved by the lead user.

---

## Decision Summary Table

| ID | Decision Area | Status | Chosen Option / Resolution | Associated ADR / Doc | Target Stage | Owner |
|---|---|---|---|---|---|---|
| **OD-01** | Live Sensor Source & Active Station | **RESOLVED** | Primary: openSenseMap Station `Sarvamangalam` (`689b2bdc...`); Context: Open-Meteo Kolar; Soil moisture: Replay + Edge Mock | [Assessment](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/project/LIVE_DATA_SOURCE_ASSESSMENT.md) | Stage 6 | Team / User |
| **OD-02** | Initial Crop & Soil Context | **RESOLVED** | Finger Millet (Ragi - *Eleusine coracana*) in Red Sandy Loam (Kolar, Karnataka) | [PROJECT_BRIEF.md](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/project/PROJECT_BRIEF.md) | Stage 6 | Team / User |
| **OD-03** | Core Toolchain (Python / Java / Spark) | **APPROVED** | Host Python 3.11 via `uv` + Spark 3.5.3 (JDK 17/Py 3.11 in Docker) | [ADR-0001](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0001-toolchain-and-pyspark-runtime.md) | Stage 1 | Lead Eng |
| **OD-04** | Backend API Framework | **APPROVED** | FastAPI (Async ASGI, Pydantic models, automatic OpenAPI) | [ADR-0007](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0007-api-and-pwa-application-frameworks.md) | Stage 5 | Lead Eng |
| **OD-05** | Farmer PWA Frontend Framework | **APPROVED** | React 18 + TypeScript + Vite + `vite-plugin-pwa` | [ADR-0007](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0007-api-and-pwa-application-frameworks.md) | Stage 5 | Lead Eng |
| **OD-06** | LLM Provider & Fallback Strategy | **APPROVED** | Primary Google Gemini Flash (Free tier) + Deterministic Rule Fallback | [ADR-0006](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0006-llm-provider-and-fallback-strategy.md) | Stage 5 | Lead Eng |
| **OD-07** | Agent Orchestration Architecture | **APPROVED** | Direct Python Bounded State Machine (Zero external graph churn) | [ADR-0005](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0005-agent-orchestration-architecture.md) | Stage 5 | Lead Eng |
| **OD-08** | Vector Store & Embedding Model | **APPROVED** | Chroma Persistent Client (Local directory) + `all-MiniLM-L6-v2` | [ADR-0004](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0004-persistence-and-timeseries-storage.md) | Stage 5 | Lead Eng |
| **OD-09** | Event Serialization & Schema Governance | **APPROVED** | Strict JSON Schema via Pydantic v2 (Dual-boundary validation) | [ADR-0003](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0003-event-serialization-schema-governance.md) | Stage 5 | Lead Eng |
| **OD-10** | Deployment Target & Cluster Topology | **APPROVED** | Dual Profiles: Single-Broker `dev` (~1.8GB) & 3-Broker `resilience` (~4.8GB) | [ADR-0002](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0002-kafka-broker-and-client.md) | Stage 5 | Lead Eng |

---

## Detailed Decision Profiles

### OD-01: Live Sensor Source & Active Station Selection
- **Context:** Requires an active live telemetry source for the live streaming demonstration alongside the 2-year Karnataka historical replay dataset.
- **Evaluation:** Evaluated openSenseMap, IMD AWS portal, ThingSpeak, and Open-Meteo.
- **Resolution:**
  1. *Primary Live Physical Stream:* openSenseMap Station `Sarvamangalam` (`689b2bdc569c2d0007586ae9`), co-located with `Aurovanam` (`68a93536e035980007f6036b`). Sub-minute authentic physical observations (temperature, humidity, rain, wind, pressure).
  2. *Regional Environmental Context:* Open-Meteo Current API for Kolar, Karnataka (13.13°N, 78.13°E), carrying `source_type: reanalysis`.
  3. *Soil Moisture Telemetry:* Kept on the historical replay path (replaying the 2-year dataset) and an authenticated Edge Gateway Mock (`services/ingestion/farmer_edge_mock.py`). Conflating modelled Open-Meteo soil moisture with physical sensor telemetry is strictly forbidden.
- **Documentation:** [LIVE_DATA_SOURCE_ASSESSMENT.md](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/project/LIVE_DATA_SOURCE_ASSESSMENT.md)
- **Status:** **RESOLVED & APPROVED**

### OD-02: Initial Crop and Soil Agronomic Context
- **Context:** The risk engine and bounded investigator require specific crop coefficients ($K_c$), root zone depths ($Z_r$), depletion fractions ($p$), and soil available water capacity (AWC).
- **Resolution:**
  - *Crop Focus:* Finger Millet (Ragi - *Eleusine coracana*), the staple rainfed dryland crop of Southern Karnataka (Kolar, Tumakuru, Mandya). Characterized by high drought tolerance and clear moisture-stress stages (flowering/grain-filling).
  - *Soil Focus:* Red Sandy Loam (dominant dryland soil of Kolar district; high drainage, low water holding capacity, Field Capacity ~18%, Wilting Point ~8%).
  - *Agronomic Standards:* ICAR and UAS Bangalore Package of Practices for Dryland Agriculture.
- **Status:** **RESOLVED & APPROVED**

### OD-03: Core Runtime Toolchain Compatibility (Python / Java / Spark)
- **Resolution:** PySpark runs containerized via `bitnami/spark:3.5.3` (Debian Linux, Python 3.11, OpenJDK 17). Host environment uses `uv venv --python 3.11 .venv-agri`.
- **Reference:** [ADR-0001](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0001-toolchain-and-pyspark-runtime.md)
- **Status:** **APPROVED BY USER**

### OD-04: Backend API Framework
- **Resolution:** FastAPI (`>=0.115,<1.0.0`) with `uvicorn` ASGI server.
- **Reference:** [ADR-0007](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0007-api-and-pwa-application-frameworks.md)
- **Status:** **APPROVED BY USER**

### OD-05: Farmer PWA Frontend Framework
- **Resolution:** React 18 + TypeScript + Vite + `vite-plugin-pwa`.
- **Reference:** [ADR-0007](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0007-api-and-pwa-application-frameworks.md)
- **Status:** **APPROVED BY USER**

### OD-06: LLM Provider & Fallback Strategy
- **Resolution:** Primary Google Gemini 2.0 Flash (free tier API) with strict JSON schema mode + deterministic rule-based agronomic fallback on timeout (>8s) or failure. Zero paid cost; zero large model downloads.
- **Reference:** [ADR-0006](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0006-llm-provider-and-fallback-strategy.md)
- **Status:** **APPROVED BY USER**

### OD-07: Agent Orchestration Architecture
- **Resolution:** Direct Python Bounded State Machine (pure Python, <2ms overhead, 100% auditable, strict 4-step cap).
- **Reference:** [ADR-0005](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0005-agent-orchestration-architecture.md)
- **Status:** **APPROVED BY USER**

### OD-08: Persistence & Vector Storage
- **Resolution:** `timescale/timescaledb:latest-pg16` with hypertables for time series; Chroma persistent client (local directory) with `sentence-transformers/all-MiniLM-L6-v2` (384-dim, lightweight CPU execution).
- **Reference:** [ADR-0004](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0004-persistence-and-timeseries-storage.md)
- **Status:** **APPROVED BY USER**

### OD-09: Event Serialization & Schema Governance
- **Resolution:** Strict JSON Schema via shared Pydantic v2 models in `packages/event-contracts/` with dual-boundary validation.
- **Reference:** [ADR-0003](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0003-event-serialization-schema-governance.md)
- **Status:** **APPROVED BY USER**

### OD-10: Kafka Distribution, Client & Cluster Topology
- **Resolution:** `apache/kafka:3.8.0` in KRaft mode with `confluent-kafka >= 2.5`. Dual profiles: `dev` (1 broker, ~1.8GB RAM) and `resilience` (3 brokers, ~4.8GB RAM).
- **Reference:** [ADR-0002](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0002-kafka-broker-and-client.md)
- **Status:** **APPROVED BY USER**
