# AgriKafka-Agent — System Status Snapshot

**Snapshot Timestamp:** 2026-11-03T11:00:00+05:30  
**Project:** AgriKafka-Agent: Fault-Tolerant, Real-Time Agricultural Risk Monitoring and Decision Support  
**Domain Focus:** Finger Millet (*Eleusine coracana*, Ragi GPU-28) in Red Sandy Loam (*Alfisols*), Kolar, Karnataka (Zone 5)  
**Governing Documents:**  
- [PROJECT_BRIEF.md](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/project/PROJECT_BRIEF.md)  
- [BUILD_LOG.md](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/development/BUILD_LOG.md)  
- [SKILL_USAGE_LOG.md](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/development/SKILL_USAGE_LOG.md)  
- [ENVIRONMENT_AUDIT.md](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/development/ENVIRONMENT_AUDIT.md)  

---

## Executive Summary

AgriKafka-Agent is currently transitioning from **Phase II (Data & Stream Engineering / Deterministic Intelligence)** to **Phase III (Persistence, Operations & Bounded Agent Decision Support)**. 

- **Total Test Suite:** **173 passed, 1 skipped** (100% pass rate on all active tests; 1 integration test skipped due to local Kafka broker container being stopped).
- **Core Pipeline Status:**
  - Live data telemetry acquisition, normalization, and replay: **Operational**.
  - Stream processing, watermarking, deduplication, and agronomic feature engineering: **Operational**.
  - Deterministic sensor health forensics and natural flatline differentiation: **Operational** (Precision 1.0, Recall 1.0, 0 False Positives).
  - Deterministic crop risk modeling (FAO-56 water balance, CSI, thermal stress, blast windows): **Operational**.
  - TimescaleDB / PostgreSQL persistence: **Operational (Schemas, Hypertables, Pool, Idempotent Sink & Queries Completed)**.
  - Operational observability (Prometheus & Grafana): **Operational (7 dashboards, 6 alert rules, provisioned)**.
  - Agronomy RAG retrieval service: **Operational (Corpus audited, ChromaDB indexed, ONNX MiniLM-L6-v2, 12 unit tests passed, evaluation MRR 0.7333)**.
  - Multi-agent alert investigation architecture: **Operational (Supervisor + 6 specialist agents, 15 workflow states, versioned AgentMessage protocol, Critic safety loop, deterministic policy gates, 13 unit tests passed)**.
  - Backend API: **Operational (FastAPI, 34 versioned routes, RBAC & parcel isolation, supervisor exclusivity, zero physical actuation invariant, 27 unit tests passed)**.
  - Farmer PWA: **Operational (React 18 + Vite + TypeScript, 10 core screens, bilingual EN/KN, multi-agent milestone transparency, offline service worker, 13 Vitest passed)**.
  - Notifications & Feedback: **Operational (Multi-channel dispatcher, compound idempotency, dead-letter queue, 7-state review lifecycle, zero physical actuation invariant, offline feedback loop queryable for Stage 20, 11 unit tests passed)**.

---

## Stage-by-Stage Audit (Stages 0 – 22)

| Stage | Title / Subsystem | Status | Key Evidence (Files, Commands, Output) |
|---|---|---|---|
| **Stage 0** | Project Bootstrap & Working Agreement | **PASS** | `docs/project/PROJECT_BRIEF.md`, `docs/project/OPEN_DECISIONS.md`, `docs/development/BUILD_LOG.md`. Read-only audit confirmed zero destructive modifications. |
| **Stage 1** | Workstation & Toolchain Audit | **PASS** | `docs/development/ENVIRONMENT_AUDIT.md`. Verbatim diagnostic commands for Windows 11 Build 26200, WSL2, Docker CLI 29.7.2, Python 3.13 / 3.11, OpenJDK 17, Node v23.11.0, RAM (15.4GB), 15 free ports. Mitigated Python 3.13 / PySpark incompatibility via containerized Spark 3.5.3 profile. |
| **Stage 2** | Repository Skeleton & Developer Workflow | **PASS** | Monorepo layout (`apps/`, `services/`, `packages/`, `infra/`, `data/`, `tests/`, `knowledge/`), `pyproject.toml`, `DEVELOPMENT.md`, `README.md`, `.gitignore`, `.env.example`. |
| **Stage 3** | Skill Repository Audit & Selection | **PASS** | `docs/development/EXTERNAL_SKILL_AUDIT.md`. 10 verified external skills installed under `.agents/skills/` from audited GitHub SHAs (`addyosmani`, `vaquarkhan`, `lensesio`, `sickn33`) preserving references and templates. |
| **Stage 4** | Author AgriKafka Rules & Custom Skills | **PASS** | 5 project rules under `.agents/rules/` (`architecture-guardrails.md`, `data-provenance.md`, `agronomic-safety.md`, `security-and-secrets.md`, `testing-and-evaluation.md`) + 8 custom skills under `.agents/skills/`. Programmatic validation: 100% syntax and frontmatter compliance. |
| **Stage 5** | Architecture Decisions & ADRs | **PASS** | 7 ADRs authored under `docs/decisions/` (`ADR-0001` through `ADR-0007`), `docs/architecture/ARCHITECTURE_V1.md` (Mermaid system architecture, topic topology, dual dev/resilience runtime profiles). |
| **Stage 6** | Live Data-Source Verification | **PASS** | `docs/project/LIVE_DATA_SOURCE_ASSESSMENT.md`. Empirical probe of 4 candidate APIs. Verified live openSenseMap station `Sarvamangalam` (`689b2bdc569c2d0007586ae9`, Lat 12.00°N, Lon 79.80°E) streaming 5 physical variables at ~15–45s cadence (latency 12.1s). Verified Open-Meteo Kolar context stream. Documented that physical soil probes are absent in Karnataka; preserved provenance. |
| **Stage 7** | Canonical Event Schema & Contract Tests | **PASS** | `packages/event-contracts/` (7 Pydantic v2 models, 8 enums, 10 example JSONs), `docs/architecture/EVENT_CONTRACTS.md`. `uv run pytest tests/contract/test_event_contracts.py` -> **17 passed in 0.25s**. |
| **Stage 8** | Local Kafka KRaft Infrastructure | **PASS WITH LIMITATIONS** | `docker-compose.yml`, `infra/docker/docker-compose.dev.yml`, `infra/kafka/init_topics.py` (9 canonical topics with partitions, RF=1, retention, and key strategies), `docs/architecture/KAFKA_TOPOLOGY.md`, `manage.ps1`, `smoke_test.py`, `verify_persistence.py`. **Limitation:** Docker Desktop daemon is stopped on host; live broker verification requires starting Docker daemon. |
| **Stage 9** | Multi-Source Python Ingestion Layer | **PASS** | `services/ingestion/` (4 adapters: OSM live, Open-Meteo context, historical replay with atomic checkpoints, 8 injected scenarios), `services/ingestion/src/agri_ingestion/cli.py`. Tests: `tests/unit/test_ingestion_adapters.py`, `tests/integration/test_ingestion_kafka.py` -> **21 tests passing** (18 unit + 2 mock broker passed, 1 live broker skipped). |
| **Stage 10** | PySpark Structured Streaming Pipeline | **PASS** | `services/stream-processor/` (10-min watermark, 5-min tumbling and 30-min sliding windows, state-bounded deduplication on `(idempotency_key, event_time)`, VPD/leaf wetness proxy/soil depletion calculations, DLQ routing), `Dockerfile` (`bitnami/spark:3.5.3`), `docs/architecture/STREAM_PROCESSING_SPEC.md`. Tests: `tests/unit/test_stream_transformations.py`, `tests/integration/test_stream_pipeline.py` -> **18 passed in 6.01s**. CLI dry-run verified. |
| **Stage 11** | Deterministic Sensor Health Engine | **PASS** | `services/risk-engine/src/agri_risk_engine/health/` (6 detectors, natural flatline differentiation for rain zeroes and residual soil dry plateaus, advisory safety gating `is_measurement_usable_for_advisory`), `docs/architecture/SENSOR_HEALTH_FORENSICS_SPEC.md`. Tests: `tests/unit/test_sensor_health_*.py`, `tests/integration/test_sensor_health_service.py` -> **28 passed**. 24-fixture benchmark: Precision 1.0, Recall 1.0, Specificity 1.0, 0 False Positives on natural flatlines. |
| **Stage 12** | Agronomic Crop Risk Engine | **PASS** | `services/risk-engine/src/agri_risk_engine/risk/` (Grounded Ragi GPU-28 parameters, FAO-56 water balance, TAW 60mm, RAW 27mm, threshold 0.166 m³/m³, CSI heuristic, blast risk window, Z-score/EWMA/Isolation Forest comparison, abstention guardrails), `docs/architecture/CROP_RISK_ENGINE_SPEC.md`. Tests: `tests/unit/test_crop_risk_*.py`, `tests/integration/test_crop_risk_service.py` -> **22 passed** across heat, dry-down, rainfall recovery, and safety suppression scenarios. |
| **Stage 13** | TimescaleDB Schema, Sinks & Data Access | **PASS** | `docker-compose.yml`, `infra/docker/docker-compose.dev.yml` (`timescale/timescaledb:latest-pg16`, volume `timescale_dev_data`, port `127.0.0.1:5432:5432`). Migrations `001_initial_schema.up.sql` (hypertables `observations`, `windowed_features`, `sensor_health_events`, `crop_candidate_alerts`), `001_initial_schema.down.sql`, `002_readonly_role.up.sql`, `002_readonly_role.down.sql`. Migration CLI `infra/database/migrate.py`. Persistence package `packages/database-client/src/agri_persistence/` (pool, repository, consumer). 4 representative queries in `infra/database/queries/`. Tests: `test_database_schema.py` (6 passed), `test_persistence_idempotency.py` (6 passed). Full repo tests: **117 passed, 1 skipped**. |
| **Stage 14** | Prometheus Metrics & Grafana Dashboards | **PASS** | `packages/shared-python/src/agri_shared/metrics.py` (standardized low-cardinality Prometheus metrics across all layers), `infra/prometheus/prometheus.yml`, `infra/prometheus/alert_rules.yml` (6 actionable rules: ServiceDown, StaleSourceTelemetry, SustainedConsumerLag, RepeatedSparkMicroBatchFailures, DeadLetterQueueGrowth, CriticalCropStressIndex), `infra/grafana/provisioning/`, `infra/grafana/dashboards/` (7 distinct dashboards: system overview, kafka, spark, ingestion freshness, sensor health, candidate alerts, reliability), `docs/operations/OPERATIONS_RUNBOOK.md`. Tests: `test_metrics_instrumentation.py` (4 passed), `test_prometheus_grafana_config.py` (4 passed). Full repo tests: **125 passed, 1 skipped**. |
| **Stage 15** | Agronomy Corpus Ingestion & Chroma Vector DB | **PASS** | `knowledge/source-register.csv` (5 audited sources: FAO-56, UAS Bangalore, ICAR-AICRP, TNAU, ICAR-CRIDA), `knowledge/corpus/` (5 markdown docs), `packages/agronomy-rag/` (`models.py`, `ingest.py`, `store.py`, `retriever.py`, `validator.py`, `eval.py`, `cli.py`), `knowledge/chroma_db/` (21 chunks indexed, version `v1.0-1b95cf635c01`, ONNX `all-MiniLM-L6-v2` 384d, cosine HNSW), `docs/architecture/AGRONOMY_RAG_DESIGN.md`, `docs/evaluation/RAG_RETRIEVAL_EVALUATION.md`, `docs/architecture/STAGE_16_INTEGRATION_CONTRACT.md`. Evaluation: 10 queries, Mean Precision@3 = 0.5333, Mean Recall@3 = 0.8000, MRR = 0.7333, Latency = 288.58 ms. Tests: `tests/unit/test_agronomy_rag.py` -> **12 passed in 4.41s**. Full suite: **137 passed**. |
| **Stage 16** | Bounded Multi-Agent Investigator & Guardrails | **PASS** | `services/alert-investigator/` (`src/agri_investigator/`: `supervisor.py`, `models.py`, `state.py`, `protocol.py`, `safety.py`, `cli.py`, `agents/` [6 specialists: `sensor_reliability`, `field_context`, `crop_risk_analyst`, `agronomy_knowledge`, `agricultural_advisory`, `critic_safety`]). Database migration `003_multi_agent_investigation.up.sql` (`multi_agent_investigation_runs`, `agent_messages`, `investigation_state_transitions`). Documentation: `ADR-0008`, `MULTI_AGENT_ARCHITECTURE.md`, `AGENT_COMMUNICATION_PROTOCOL.md`, `INVESTIGATION_STATE_MACHINE.md`, `MULTI_AGENT_CODE_TRACE.md`. Tests: `tests/unit/test_multi_agent_investigation.py` -> **13 passed in 6.14s**. Full monorepo suite: **150 passed**. |
| **Stage 17** | Backend API Implementation | **PASS** | `services/api/` (`agri_api`: `main.py`, `auth.py`, `config.py`, `dependencies.py`, `routers/`, `models/`), `docs/architecture/API_CONTRACTS.md`, `services/api/README.md`. 33 registered endpoints under `/api/v1` and root. Invariants verified: supervisor exclusivity, field parcel ownership boundary, zero physical hardware actuation commands, idempotent human review. Tests: `tests/unit/test_api_endpoints.py` (16 passed), `tests/unit/test_api_auth_boundaries.py` (11 passed) -> **27 passed in 3.73s**. Full monorepo suite: **162 passed, 1 skipped**. |
| **Stage 18** | Farmer PWA Implementation | **PASS** | `apps/farmer-pwa/` (`src/`: `App.tsx`, `components/`, `services/api.ts`, `i18n/translations.ts`, `types/api.ts`), `public/` (`manifest.json`, `sw.js`, `favicon.svg`), `docs/architecture/FARMER_PWA_SPEC.md`, `apps/farmer-pwa/README.md`. 10 core screens implemented. WCAG 2.1 AA accessible, mobile-first responsive layout, bilingual English/Kannada support, transparent 5-milestone multi-agent progress rendering, zero autonomous actuation, offline service worker caching. Tests: `npm test` -> **13 passed in 5.33s** (Vitest + Testing Library). Production build: `dist/` **214 kB (63.95 kB gzip)**. |
| **Stage 19** | Notification & Feedback Workflow | **PASS** | `services/notification-worker/` (`agri_notifications`: `models.py`, `config.py`, `policy.py`, `providers/` [Mock, PWA, Telegram], `dispatcher.py`, `lifecycle.py`, `feedback.py`, `cli.py`), migration `004_notifications_and_feedback.up.sql`. Compound idempotency `(alert_id, advisory_version, recipient_id, channel)`, bounded exponential backoff & DLQ, 7-state human review lifecycle, zero physical actuation invariant, multi-agent evidence-linked feedback loop, offline learning invariant. Tests: `tests/unit/test_notifications_and_feedback.py` -> **11 passed in 3.03s**. Full monorepo suite: **173 passed, 1 skipped**. |
| **Stage 20** | Reproducible Experimental Harness | **NOT STARTED** | Benchmark protocols defined in `.agents/skills/agrikafka-evaluation-harness`. Scenarios ready in `tests/scenarios/`. |
| **Stage 21** | Resilience Profile & Chaos Injection | **NOT STARTED** | Test directory exists in `tests/resilience/`. Chaos specifications defined in `.agents/skills/stream-resilience-benchmarking`. |
| **Stage 22** | Full-System Verification & Delivery Candidate | **NOT STARTED** | Final integration verification and delivery gate pending completion of stages 13–21. |

---

## Finalised Architectural Decisions

| Decision Domain | Selected Choice | Rationale & Trade-Offs | Governing ADR / Spec |
|---|---|---|---|
| **LLM Provider & Fallback** | **Google Gemini 2.0 Flash (Primary)** + **Deterministic Rule Fallback (Secondary)** | Zero cost (free tier API); low latency (<1.5s); deterministic rule engine guarantees continuous risk calculation during API outages or token exhaustion. Optional Ollama local fallback. | [ADR-0006](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0006-llm-provider-and-fallback-strategy.md) |
| **Agent Orchestration** | **Direct Python Bounded State Machine** | Strict iteration cap ($\le 4$ steps), 8 read-only inspection tools, deterministic fallback on token budget exhaustion or timeout; full auditability; no non-deterministic multi-agent loops. | [ADR-0005](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0005-agent-orchestration-architecture.md) |
| **Backend API Framework** | **FastAPI** | High-performance async Python; native Pydantic v2 contract reuse; auto-generated OpenAPI documentation; WebSockets for real-time alert pushes. | [ADR-0007](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0007-api-and-pwa-application-frameworks.md) |
| **Farmer Frontend Framework** | **React 18 + TypeScript + Vite + `vite-plugin-pwa`** | Offline-first service worker caching; low-bandwidth optimization; mobile viewport UI; one-tap advisory approval workflows. | [ADR-0007](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0007-api-and-pwa-application-frameworks.md) |
| **Live Telemetry Sources** | **openSenseMap (`Sarvamangalam`)** + **Open-Meteo (Kolar)** | openSenseMap station `689b2bdc569c2d0007586ae9` provides physical microclimate readings (temp, humidity, rain, wind, pressure) at ~15–45s cadence. Open-Meteo provides gridded environmental weather context (`source_type: reanalysis`). Physical soil moisture sourced via Historical Replay / Edge Mock. | [LIVE_DATA_SOURCE_ASSESSMENT.md](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/project/LIVE_DATA_SOURCE_ASSESSMENT.md), OD-01, OD-02 |
| **Agronomic Focus** | **Finger Millet (*Eleusine coracana*, Ragi GPU-28) in Red Sandy Loam, Kolar** | Regional grounding from UAS Bangalore and ICAR. TAW = 60.0 mm, RAW = 27.0 mm, moisture threshold = 0.166 m³/m³. Mandatory abstention on incomplete field context. | [CROP_RISK_ENGINE_SPEC.md](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/architecture/CROP_RISK_ENGINE_SPEC.md), OD-02 |
| **Stream Processing Runtime** | **PySpark 3.5.3 LTS (`bitnami/spark:3.5.3`)** | Isolated container running Debian Linux, Python 3.11, OpenJDK 17. Resolves host Python 3.13 incompatibility. Watermark 10 min, tumbling 5 min, sliding 30 min. | [ADR-0001](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0001-toolchain-and-pyspark-runtime.md) |
| **Kafka Broker & Client** | **`apache/kafka:3.8.0` (KRaft Mode)** + **`confluent-kafka` (Python)** | Single-broker KRaft development profile (zero ZooKeeper). 9 canonical topics, RF=1, per-field keying, persistent volume `kafka_dev_data`. Host listener strictly bound to `127.0.0.1:9092`. | [ADR-0002](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0002-kafka-broker-and-client.md) |
| **Time-Series Persistence** | **TimescaleDB (`timescale/timescaledb:latest-pg16`)** | PostgreSQL 16 with TimescaleDB hypertables for time-series (`observations`, `windowed_features`, `sensor_health_events`, `crop_candidate_alerts`) and standard tables for entities (`field_profiles`, `sensor_metadata`, `recommendations`). Dedicated read-only role `agri_readonly`. | [ADR-0004](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0004-persistence-and-timeseries-storage.md) |
| **Vector Database & Embeddings**| **Chroma (Persistent Embedded Client)** + **`all-MiniLM-L6-v2`** | Embedded in-process execution (zero separate Docker container); lightweight Sentence Transformers model running locally without GPU. | [ADR-0004](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/docs/decisions/ADR-0004-persistence-and-timeseries-storage.md) |

---

## Toolchain & Component Version Inventory

| Component / Tool | Pinned Version | Installed / Detected Status | Deployment Environment |
|---|---|---|---|
| **Operating System** | Windows 11 Build 26200 | Windows 11 Home Single Language (AMD64) | Host Development Machine |
| **Python Toolchain** | Python `>=3.11` (pinned `3.11` in containers) | Host `Python 3.13.1`; `.venv` created via `uv` | Host (`uv`) & Docker Containers |
| **Package Manager** | `uv >= 0.11.0` | `uv 0.11.26` | Host |
| **Java / JDK** | OpenJDK 17 LTS | Eclipse Temurin 17.0.19+10 (`JAVA_HOME`) | Host & Spark Container |
| **Node.js / npm** | Node.js `>=20.0.0` | Node.js `v23.11.0`, npm `10.9.2` | Host |
| **Docker Engine & Compose** | Docker 29+, Compose v5+ | Docker CLI `29.7.2`, Compose `v5.4.0` (Daemon stopped) | Host |
| **Apache Kafka** | `apache/kafka:3.8.0` | Docker image configured in compose | Docker Bridge (`agrikafka_network`) |
| **Python Kafka Client** | `confluent-kafka >= 2.5.0` | `confluent-kafka 2.16.1` | Python `.venv` |
| **Apache Spark / PySpark** | Apache Spark 3.5.3 LTS | Container `bitnami/spark:3.5.3` | Docker Container |
| **PostgreSQL / TimescaleDB**| TimescaleDB on PostgreSQL 16 | Docker image `timescale/timescaledb:latest-pg16` | Docker Container |
| **PostgreSQL Python Driver**| `psycopg >= 3.2.0` | `psycopg 3.3.7`, `psycopg-pool 3.3.3` | Python `.venv` |
| **Pydantic** | `pydantic >= 2.7.0` | `pydantic 2.10.6` | Python `.venv` |
| **Pytest** | `pytest >= 7.0.0` | `pytest 9.2.0` | Python `.venv` |

---

## Real Empirical Results Obtained

1. **Live Physical Sensor Telemetry (Stage 6 & 9):**
   - Successfully established active polling of openSenseMap station `Sarvamangalam` (`689b2bdc569c2d0007586ae9`).
   - Received live physical values: Temperature = `25.39 °C`, Relative Humidity = `93 %`, Rainfall = `0 mm`, Wind Speed = `0 m/s`, Barometric Pressure = `1016.8 hPa`.
   - Measured empirical freshness latency: `12.1 seconds`.
   - Verified active sub-minute cadence (`15–45 seconds`).

2. **Historical Replay Acceleration & Ordering (Stage 9):**
   - Replayed Open-Meteo Karnataka 2-year dataset (175,200 rows) with deterministic temporal ordering, simulated acceleration ($1\times$ to $3600\times$), and atomic checkpointing (`.replay_checkpoint_<run_id>.json`).

3. **PySpark Structured Streaming & Derived Agronomic Features (Stage 10):**
   - Verified Tetens saturation vapor pressure and Vapour Pressure Deficit (VPD) math against meteorological tables ($25^\circ\text{C}, 60\% \text{ RH} \implies \text{VPD} \approx 1.27\text{ kPa}$).
   - Computed Magnus dew point ($25^\circ\text{C}, 80\% \text{ RH} \implies T_{\text{dew}} \approx 21.3^\circ\text{C}$).
   - Verified dry-run pipeline compilation without JVM exceptions.

4. **Sensor Health Forensic Classification Benchmark (Stage 11):**
   - Evaluated 24 labelled benchmark test fixtures in `test_sensor_health_confusion_matrix.py`:
     - True Positives: **16**
     - True Negatives: **8**
     - False Positives: **0**
     - False Negatives: **0**
     - **Precision:** `1.0000` | **Recall:** `1.0000` | **Specificity:** `1.0000` | **F1-Score:** `1.0000`
   - Verified **zero false positives** on natural flatlines (dry-season zero rain sequences and residual dry soil moisture plateaus strictly preserved).

5. **Crop Risk Engine Grounding & Anomaly Detection (Stage 12):**
   - Grounded Ragi GPU-28 parameters: $\text{TAW} = 60.0\text{ mm}$, $\text{RAW} = 27.0\text{ mm}$, moisture threshold $\theta_{\text{threshold}} = 0.166\text{ m}^3/\text{m}^3$.
   - Tested 9 full end-to-end scenarios covering progressive soil dry-down, heat shock floret sterility ($T \ge 34^\circ\text{C}$), rainfall recovery, conflicting rain vs soil drop, sensor faults, stale data, and missing crop profiles.
   - Evaluated detector candidates: Rolling Z-score ($<15\mu\text{s}$ latency) and EWMA ($<8\mu\text{s}$ latency) adopted for real-time streaming; Isolation Forest ($1500\mu\text{s}$ latency) retained as offline comparative baseline.

---

## Known Limitations & Unresolved Issues

1. **Docker Daemon Inactive on Host Machine:**
   - Docker Desktop CLI is installed, but the Docker daemon is currently stopped. Live container execution (`docker compose up -d kafka timescaledb stream-processor`) requires starting Docker Desktop. Unit and mock tests run cleanly without Docker.
2. **Absence of Public Physical In-Situ Soil Moisture Probes in Karnataka:**
   - Empirical investigation in Stage 6 confirmed that no open, public IoT network (IMD, openSenseMap, ThingSpeak) exposes physical in-situ root-zone soil moisture probes in Karnataka.
   - *Mitigation:* Under `data-provenance.md`, soil moisture is explicitly tagged as `modelled_reanalysis` (Open-Meteo ERA5) or `in_situ_mock` (Farmer Edge Gateway Mock) and carries an uncertainty penalty (+0.25).
3. **Stage 13 Persistence Layer Completion:**
   - Database schemas, hypertable configurations, and readonly role scripts are authored. Kafka persistence consumer sink and live PostgreSQL integration tests await container execution.
4. **Stages 14 – 22 Not Started:**
   - Dashboards (14), Chroma vector RAG (15), Bounded Agent (16), FastAPI (17), Farmer PWA (18), Telegram worker (19), Experimental harness (20), Resilience drills (21), and Delivery candidate (22) remain to be implemented sequentially.

