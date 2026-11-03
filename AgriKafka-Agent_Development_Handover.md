# AgriKafka-Agent — Development Handover

**Purpose:** Carry the project context, decisions, architecture, research direction, and Antigravity setup plan into a fresh ChatGPT conversation.

**Project status:** Architecture direction agreed; development setup and implementation have not yet begun.

---

## 1. Project identity

**Project title:** AgriKafka-Agent: Fault-Tolerant, Real-Time Agricultural Risk Monitoring and Decision Support

**Course:** Stream Processing and Analytics  
**Course code:** AI372IA  
**Team:** Aanish Khan, Daksh Chauhan, Pranav Pratyush  
**Faculty guides:** Dr. Vijayalakshmi M N and Dr. S. Anupama Kumar

### Product in one sentence

AgriKafka-Agent is a real-time agricultural monitoring and decision-support system that combines live environmental telemetry, data-quality and sensor-health assessment, crop-context-aware risk detection, and a bounded tool-using AI investigator that produces evidence-grounded recommendations for human approval.

### Core questions it should answer

1. Is something unusual happening in this field?
2. Is it a genuine environmental/crop risk, or is the underlying data unreliable?
3. What evidence supports the assessment?
4. What practical next step should the farmer consider?
5. Can the pipeline continue and recover correctly when components fail?

It is not an autonomous irrigation controller, disease-diagnosis system, or replacement for an agronomist.

---

## 2. Final product direction

There are two user experiences.

### Farmer-facing application

Build a mobile-first responsive Progressive Web App (PWA). Telegram can be retained as an initial notification and approval channel, but should not be the only farmer interface.

Expected farmer capabilities:

- Register farms and fields.
- Maintain field profiles: location, crop, variety, sowing date, growth stage, soil type, irrigation method, sensor type, placement and depth.
- View field conditions and data freshness.
- Receive understandable risk and sensor-fault alerts.
- Inspect why an alert was generated.
- View evidence-backed recommendations and their sources.
- Approve/reject or acknowledge recommendations.
- Review alert history.
- Eventually support Kannada and English, low-bandwidth use, and accessible mobile UX.

The farmer must not need to understand Kafka, Spark, consumer lag, anomaly algorithms or infrastructure metrics.

### Operations / analyst dashboard

Use Grafana for engineering and operational monitoring, not as the only farmer-facing product.

Show:

- Field readings and environmental trends.
- Sensor health and stale-data warnings.
- Detector outputs and triage classifications.
- Retrieved evidence and agent decisions.
- Kafka throughput, consumer lag and broker health.
- Spark processing latency and failures.
- DLQ volume, recovery and duplicate-action checks.

### Important UI separation

Farmer application = field decisions and understandable explanations.  
Grafana = system operations, engineering diagnostics and research measurements.

---

## 3. Architecture direction

### High-level architecture

```text
LIVE DATA SOURCES
  - IMD AWS/ARG station observations (access to verify)
  - openSenseMap public sensor observations (find and verify active station)
  - Farmer-owned sensors / gateway (future field deployment)
  - Weather API / forecast context
             |
             v
INGESTION
  - Python API connectors
  - MQTT gateway / webhook receivers where appropriate
  - Normalisation, timestamps, provenance, validation
             |
             v
APACHE KAFKA (KRaft)
  - raw telemetry
  - weather context
  - validated observations
  - sensor health
  - candidate risk events
  - agent actions
  - feedback
  - DLQ and operational metrics
             |
             v
PYSPARK STRUCTURED STREAMING
  - event-time processing, windows, watermarks
  - stream joins and contextual features
  - deduplication and quality indicators
             |
             v
DATA QUALITY + SENSOR HEALTH
  - stale/missing data
  - stuck values
  - spikes, drift, dropout
  - implausible values
  - distinguish natural flatlines from sensor faults
             |
             v
CROP-CONTEXT-AWARE RISK ENGINE
  - crop profile, soil type, growth stage
  - sensor depth and placement
  - weather, rainfall, soil moisture
  - ET / water-balance indicators where feasible
  - EWMA, rolling Z-score, Isolation Forest baselines
  - explainable risk indicators
             |
             v
CANDIDATE ALERTS
             |
             v
BOUNDED ALERT INVESTIGATOR AGENT
  - checks sensor health and data freshness
  - fetches field history and neighbouring context
  - fetches weather/forecast context
  - fetches crop profile
  - retrieves ICAR / FAO / regional guidance
  - conditionally decides what evidence is still needed
             |
             v
DETERMINISTIC GUARDRAILS
  - schema validation
  - citation ID validation
  - safety rules
  - uncertainty and evidence checks
  - no physical actuation
             |
             v
HUMAN APPROVAL / FEEDBACK
             |
       +-----+------------------+
       |                        |
       v                        v
FARMER PWA / TELEGRAM       TIMESCALEDB
       |                        |
       +------------------------+
                                |
                           GRAFANA
```

### Two data paths

Do not abandon the existing historical dataset. Change its role.

**Live path — primary live demonstration**
- Physical sensor or weather-station observations from a verified live feed.
- IMD AWS/ARG is a candidate for Indian weather observations, subject to registration/access verification.
- openSenseMap is a candidate for global physical sensor observations, including possible soil-moisture measurements; identify and verify a currently active station before relying on it.
- Farmer-owned sensor integration is the long-term product direction.

**Historical/replay path — controlled research evaluation**
- Existing Open-Meteo historical dataset.
- Accelerated replay through Kafka.
- Labelled injected dry-down, heat, stuck sensor, spike, drift, dropout and other fault scenarios.
- Use for reproducible detector comparisons and fault injection.

Both paths must use the same canonical event schema and preserve source provenance. Never represent modelled/reanalysis soil moisture as a physical sensor reading, or a remote station reading as a measurement from the farmer's own field.

### Candidate Kafka topics

Standardise names before implementation. Suggested direction:

- `sensor-readings`
- `weather-data`
- `validated-observations`
- `sensor-health`
- `crop-alerts`
- `agent-actions`
- `feedback`
- `dead-letter`
- `agri-ops-metrics`

The earlier detailed plan used `sensor-readings`, `weather-data`, `crop-alerts`, `agent-actions`, `feedback`, and `dead-letter`; the environment document separately proposed `agri.raw`, `agri.validated`, `agri.risk-events`, `agri.dlq`, and `agri.ops-metrics`. Do not mix both naming schemes without a deliberate decision.

### Reliability principles

- Kafka KRaft; three brokers for the final replication/failure demonstration.
- A single-broker development profile is acceptable for initial local development.
- Persistent Spark checkpoints.
- Explicit event-time and late-event policy.
- Idempotent producers and idempotent downstream actions.
- Consumer offset management.
- DLQ with inspectable error metadata and safe replay.
- Retries with bounded backoff.
- LLM timeout and rule-based fallback.
- Alert-ID keyed deduplication to avoid duplicate farmer notifications.
- Do not claim end-to-end exactly-once semantics without proving them.

---

## 4. Technology stack — current preferred direction

| Layer | Preferred technology |
|---|---|
| IDE | Google Antigravity |
| Language | Python |
| Containerisation | Docker + Docker Compose |
| Messaging | Apache Kafka, KRaft |
| Stream processing | PySpark Structured Streaming |
| Statistical/ML detection | EWMA, rolling Z-score, Isolation Forest |
| Time-series storage | TimescaleDB (PostgreSQL extension) |
| Vector store | Chroma |
| Embeddings | Sentence Transformers |
| Agent framework | LangGraph or direct Python tool calling; decision pending |
| LLM | Hosted API or Ollama; provider decision pending |
| Farmer interface | Responsive PWA; frontend framework decision pending |
| Operations dashboard | Grafana |
| Metrics/monitoring | Prometheus + Grafana |
| Notifications | Telegram Bot initially; other channels later |
| Testing | pytest + scenario/fault-injection harness |

TimescaleDB is the selected direction over plain PostgreSQL because it extends PostgreSQL for time-series workloads. Confirm compatibility and pin exact versions during implementation.

### Decisions still open

Do not assume these have been finalised:

1. Farmer PWA frontend framework.
2. Backend API framework (FastAPI is a reasonable candidate, not yet locked).
3. Hosted LLM provider versus local Ollama.
4. LangGraph versus direct Python tool calling.
5. Exact live sensor source and verified station.
6. Exact Kafka/Spark/Python/database versions.
7. Crop(s) and soil contexts for the first meaningful crop-specific model.
8. Whether to use Schema Registry / Avro / JSON Schema initially.

---

## 5. Why the agentic layer is justified — and its limits

The project should not use an LLM for every raw reading. Kafka and Spark handle high-volume deterministic processing. The LLM/agent is only invoked for selected candidate alerts.

### Three approaches to compare

| Variant | Design |
|---|---|
| B1 | Deterministic rules/statistical detection only |
| B2 | Single LLM with context preassembled, plus RAG |
| B3 | Bounded tool-using investigator agent, plus RAG and deterministic guardrails |

### What the agent adds

A single LLM can explain information supplied to it. RAG can retrieve relevant documents. Neither automatically provides a controlled, conditional investigation workflow.

A bounded agent can select and sequence read-only tools based on prior results:

- `get_sensor_health()`
- `get_field_history()`
- `get_neighbouring_field_context()`
- `get_weather_observations()`
- `get_weather_forecast()`
- `get_crop_profile()`
- `calculate_crop_water_status()`
- `retrieve_agronomy_guidance()`

Example:
- If sensor health is faulty, classify as a sensor issue and do not generate irrigation advice based on invalid data.
- If readings are valid, investigate field history, crop context and weather.
- If evidence is incomplete or contradictory, fetch additional context or ask for missing field information.
- If evidence remains insufficient, abstain from a specific recommendation and request field inspection.

### Critical architectural boundary

Do not make the LLM responsible for:
- Numerical sensor-health checks.
- Statistical anomaly detection.
- Crop-water calculations.
- Citation ID validation.
- Safety enforcement.
- Physical actuation.

These should be deterministic services or human-controlled actions.

The agent should be bounded, auditable and primarily read-only. No irrigation hardware control or autonomous chemical application.

### How to prove the agent is worth the complexity

Compare B1, B2 and B3 on the same scenarios.

Measure:
- Macro-F1 for `real_stress`, `sensor_fault`, `noise`.
- Precision/recall and false-alert reduction at comparable genuine-stress recall.
- Evidence completeness.
- Citation-grounding rate.
- Unsupported/unsafe recommendation rate.
- Latency per stage.
- LLM calls and token use per alert.
- Fallback rate and tool failures.

Do not assume agentic AI is better. The experiments must establish whether its incremental value justifies the complexity.

---

## 6. Existing systems and research to benchmark

These were identified during prior research. Treat company capability descriptions as vendor-reported unless independently validated.

### Commercial products

1. **Fasal** — Indian precision agriculture. Soil/weather sensors, irrigation and disease advisories, device-health monitoring, mobile alerts, API/webhook integration and multilingual product experience. Particularly relevant to Indian farmer UX and sensor telemetry.
   - https://fasal.co/
   - Research Fasal's enterprise API and device-health capabilities.

2. **CropX** — soil sensors, weather, satellite/machinery integration, irrigation planning and agronomic models.
   - https://cropx.com/

3. **Arable** — field sensing, weather, crop/plant measurements, evapotranspiration and crop-water indicators; API integration.
   - https://www.arable.com/

4. **Semios** — precision agriculture, pest management, weather and irrigation monitoring, alerts and automation.
   - https://semios.com/

5. **Cropin / OrbitAI** — agricultural intelligence and agentic AI. Cropin announced OrbitAI in July 2026, describing specialised agents connected to agricultural data and predictive models. Important benchmark: agentic AI in agriculture is not itself a novel claim.
   - https://www.cropin.com/

### Research projects

1. **CottonBot (2025)** — cotton-farming assistant using real soil-moisture sensors, weather APIs, LLM-RAG and agentic tools, including crop-stage/root-zone-aware irrigation advice. It overlaps substantially with our proposed real-sensor + RAG + agent design. Study carefully and narrow novelty claims.
   - https://doi.org/ (retrieve exact DOI and full citation before using in paper; prior search result: https://turn879649search2 is not a permanent citation URL).

2. **AgroNova (2026)** — autonomous IoT greenhouse climate-control architecture with sensor nodes, gateway/server agents and LLM advisory; reported seven-month tomato greenhouse deployment and >380,000 measurements. Study architecture and deployment lessons.
   - Use the exact research result previously identified as `turn666676search3`; verify full title, authors, venue and DOI before citing.

### What to learn

- Fasal: Indian farmer workflows, sensor health, mobile UX, local languages.
- CropX/Arable: multi-source field context and agronomic modelling.
- Cropin: domain-specific agents and agricultural intelligence.
- CottonBot: real sensors, crop-stage context, RAG and tool-using agents.
- AgroNova: edge/gateway architecture and long-running real-world deployment.

### Honest positioning

Do not claim AgriKafka-Agent is commercially superior to these products. They have major advantages in real deployments, sensors, agronomic data and validation.

Position the project as a reproducible, inspectable research architecture investigating:
- Fault-aware agricultural stream processing.
- Sensor-fault versus genuine-risk triage.
- Bounded evidence-gathering agents.
- Grounded recommendations.
- Measurable reliability and recovery.

The novelty claim must be narrowed after a focused literature review. Say “to the best of our search” only where justified.

---

## 7. Data sources and agronomic limitations

### Live source candidates

**IMD AWS/ARG**
- Official IMD API portal: https://api.imd.gov.in/
- AWS/ARG endpoint documented in earlier research: `https://api.imd.gov.in/api/v1/aws_data?sid=13` for Karnataka state ID 13.
- Documented fields included current temperature, dew point, RH, wind speed/direction, timestamp and coordinates.
- Endpoint returned an unauthenticated-access error during prior testing. Registration/access must be verified before implementation.
- These are weather station observations, not necessarily soil-moisture readings.

**openSenseMap**
- https://opensensemap.org/
- API documentation: https://docs.opensensemap.org/
- Public global environmental sensor network. Potential soil-moisture sensor measurements exist, but identify an active station and inspect actual sensor type, timestamp, unit, location and update frequency before relying on it.

**ThingSpeak**
- https://thingspeak.com/
- Public channels can be read using REST APIs.
- Previous inspection found some agriculture-related channels were stale. Do not assume a public channel is live; verify last update and cadence.

**Open-Meteo**
- https://open-meteo.com/
- Existing historical data is useful for replay and test scenarios.
- Forecast/current APIs can provide environmental context, but modelled/forecast values must be labelled distinctly from physical station readings.

### Existing historical dataset

The primary historical dataset from the project overview:

- Open-Meteo Historical Weather API.
- Ten virtual field locations across Karnataka.
- Period: 5 Oct 2024 to 4 Oct 2026.
- 175,200 hourly records (10 × 730 × 24).
- 14 columns.
- Variables include temperature, relative humidity, dew point, precipitation, vapour pressure deficit, wind speed and modelled soil moisture at 0–7 cm.
- No actual NPK, pH or directly measured leaf wetness.
- Leaf-wetness proxy may be derived, but must be labelled as derived.
- Reanalysis soil moisture is modelled, not physical sensor ground truth.

Prior EDA findings in the project overview were explicitly marked for rechecking before publication:
- 0 missing values and 0 duplicate field/timestamp pairs.
- Exact one-hour cadence.
- VPD vs RH correlation reported as -0.94; VPD vs temperature +0.87.
- Rain-to-soil-moisture lag correlations were weak (strongest reported r = 0.297).
- Long natural flatlines existed for precipitation and soil moisture; flatlines alone must not trigger sensor-fault labels.
- A large one-hour temperature jump needs investigation for timezone/join artifacts.

### Agronomic foundation

Consider FAO-56 crop evapotranspiration methods, crop coefficients, soil-water balance and crop growth-stage context. ICAR and regional agricultural university material should support local advice.

Do not present a generic 0–100 Crop Stress Index as a validated probability of crop damage. Any score must have documented formula, calibration, uncertainty and limitations.

No disease diagnosis or pesticide/chemical dosage advice from weather and modelled soil moisture alone.

---

## 8. Antigravity setup — 20 external skills

The previous recommended curated list contains 20 skills from four repositories. Verify exact skill folder names and actual SKILL.md files in each repository before installation; some names in the shortlist were descriptive labels and may not match repository folder names exactly.

### A. Software engineering — 5

Source: https://github.com/addyosmani/agent-skills

- `spec-driven-development`
- `planning-and-task-breakdown`
- `incremental-implementation`
- `test-driven-development`
- `code-review-and-quality`

Purpose: requirements/specification, task decomposition, incremental implementation, tests and review.

### B. Data engineering — 9

Source: https://github.com/vaquarkhan/data-engineering-agent-skills

- `streaming-and-messaging-systems`
- `spark-and-distributed-processing`
- `python-data-engineering-and-pipeline-packaging`
- `data-quality-and-contract-testing`
- `data-resiliency-testing-and-failure-injection`
- `safe-backfill-and-replay-orchestration`
- `data-observability-and-sla-management`
- `kafka-resilience-and-schema-evolution`
- `data-contract-testing-with-schema-registry`

Purpose: Kafka/Spark engineering, Python pipelines, data contracts, quality, recovery, replay and observability.

### C. Kafka engineering — 4

Source: https://github.com/lensesio/agentic-engineering-for-apache-kafka

- `kafka-python-client`
- `kafka-topic-audit`
- `kafka-consumer-lag`
- `kafka-dlq-review`

Purpose: Python clients, topic design, lag analysis and DLQ operations.

### D. Agentic AI / RAG — 2

Source: https://github.com/sickn33/agentic-awesome-skills

- `ai-agents-architect`
- `rag-engineer`

Purpose: bounded agent architecture, tools, RAG, embeddings, retrieval evaluation and citations.

**Installation rule:** Do not blindly run installers that place files in legacy paths. Current Antigravity workspace skills location is `.agents/skills/<skill-folder>/`. Copy the complete selected skill folders, preserving references, scripts and examples. Verify each skill's actual name and compatibility first. Install selectively, not entire massive repositories.

---

## 9. MCP integrations — six candidates

### 1. Context7 — connect first

- https://context7.com/
- Documentation retrieval for current library docs.
- Useful for PySpark, Kafka clients, FastAPI, LangGraph, Chroma, TimescaleDB and frontend libraries.

### 2. Lenses MCP — after Kafka exists

- https://github.com/lensesio/lenses-mcp
- Inspect topics, messages, clusters and consumer groups.
- Lenses demo cluster is not automatically our local Docker cluster; configure against the actual cluster.

### 3. PostgreSQL MCP Pro — after DB exists

- https://github.com/crystaldba/postgres-mcp
- Schema inspection, SQL diagnostics and query plans.
- Use a restricted read-only database account for the coding agent.

### 4. Grafana MCP — after observability exists

- https://github.com/grafana/mcp-grafana
- Query metrics/logs, dashboards and alert state.
- Start read-only with limited permissions.

### 5. GitHub MCP — optional

- https://github.com/github/github-mcp-server
- Repository, issue, PR and CI workflow integration.
- Start read-only or with narrowly selected toolsets.

### 6. Open-Meteo MCP — optional

- https://github.com/cmer81/open-meteo-mcp
- Weather, historical, forecast and related environmental queries.
- This is for agent/IDE investigation, not a replacement for the independent Python-to-Kafka ingestion service.

MCPs should be connected progressively. Never expose secrets in committed configuration. Use environment variables/secret storage and least-privilege credentials. Keep database, Kafka and Grafana services private during local development.

---

## 10. Antigravity plugins / Google ecosystem

Inspect availability in Antigravity's Marketplace/Customizations before installing. Plugin names and marketplace availability can change.

1. **Chrome DevTools** — browser debugging, frontend inspection and testing. Relevant when building farmer PWA.
   - https://developer.chrome.com/docs/devtools/

2. **Modern Web Guidance** — Google guidance for accessible, performant and secure modern web apps. Use during PWA development.

3. **Gemini API plugin/skills** — conditional on choosing Gemini as the deployed advisory model.
   - https://github.com/google-gemini/gemini-skills

4. **Google Cloud plugin** — only if deployment to GCP is selected. Not required for the local Docker-first prototype.

Do not install plugins just because they are available. Activate only when their subsystem is being developed.

---

## 11. Eight custom AgriKafka skills to author

These are project-specific and should be version-controlled under `.agents/skills/`. Each should eventually have a `SKILL.md`, examples, schemas, references and verification procedures where useful.

1. **`agri-event-contracts`**
   - Canonical event schema.
   - Source provenance, event/ingestion timestamps, units, field ID, sensor ID, quality flags, event IDs.
   - Distinguish physical sensor, external weather station, historical reanalysis and injected scenario records.

2. **`live-sensor-ingestion`**
   - IMD/openSenseMap/farmer-owned connectors.
   - Polling/MQTT, retries, rate limits, timestamp normalisation, freshness, idempotency and Kafka publishing.

3. **`sensor-health-forensics`**
   - Stale readings, missingness, stuck values, spikes, drift, dropout and physical plausibility.
   - Avoid classifying natural precipitation flatlines or normal environmental patterns as sensor faults without corroborating evidence.

4. **`crop-risk-modelling`**
   - Crop, variety, growth stage, soil type, sensor depth, weather and water-balance context.
   - Explainable, documented and calibrated risk calculations.

5. **`agri-rag-grounded-advisory`**
   - ICAR/FAO/regional document ingestion, provenance, chunking, embeddings, retrieval evaluation and citations.
   - Recommendations must be grounded and uncertainty-aware.

6. **`bounded-alert-investigator`**
   - Allowed tool list, conditional investigation sequence, confidence/abstention, escalation and safety.
   - Read-only tools; no physical actuation.

7. **`agrikafka-evaluation-harness`**
   - Fixed scenario set and comparisons B1 rules/statistics, B2 single LLM + RAG, B3 bounded agent + RAG.
   - Macro-F1, precision, recall, false-alert reduction, grounding, safety, latency, token/call cost.

8. **`stream-resilience-benchmarking`**
   - Broker/worker/agent failure, LLM timeout, retries, DLQ, replay, recovery and duplicate-action tests.
   - Record message loss, duplicate actions, MTTR, throughput and P99 latency.

---

## 12. Five project-wide Antigravity rules

Create under `.agents/rules/`.

1. `architecture-guardrails.md`
   - Kafka is the event backbone.
   - Spark handles high-volume stream processing and candidate detection.
   - LLM/agent only handles selected candidate alerts.
   - No LLM on every raw reading.

2. `data-provenance.md`
   - Every observation retains source, event time, ingestion time, units, field/sensor identifiers and quality/provenance labels.
   - Never conflate modelled values with physical measurements.

3. `agronomic-safety.md`
   - No unsupported disease diagnosis, invented crop thresholds, pesticide dosage or autonomous physical action.
   - Communicate uncertainty; require human approval.

4. `security-and-secrets.md`
   - No committed API keys, passwords or tokens.
   - Local-only service exposure by default.
   - Least privilege for MCP and service credentials.

5. `testing-and-evaluation.md`
   - No component is complete without relevant tests.
   - Preserve reproducibility and log experiment parameters.
   - Never invent or fabricate benchmark results.

Use Antigravity rule activation modes thoughtfully: global architectural/security invariants can be always-on; detailed subsystem instructions can be model-selected, glob-scoped or manual.

---

## 13. Custom plugin: AgriKafka DevKit

Eventually package our custom skills, rules and agent definitions as one private project plugin:

**Name:** AgriKafka DevKit

Contents:
- Eight custom skills.
- Five project rules.
- Bounded Alert Investigator agent definition.
- Project verification prompts.
- Optional validation/benchmark scripts.
- MCP configurations where appropriate.

Antigravity plugin documentation:
- https://antigravity.google/docs/plugins
- https://antigravity.google/docs/build-plugins
- Validate with `agy plugin validate --strict` if supported by the installed CLI version.

Do not block initial development on packaging the plugin. First create and verify the individual skills/rules.

---

## 14. Recommended development order

1. Verify environment: Windows/WSL2, Docker Desktop, Docker Compose, Git, Python, Java/Spark compatibility.
2. Create repository and `.agents/` structure.
3. Install/verify the first external skills and connect Context7.
4. Create five rules and initial custom skills.
5. Verify access to live sensor sources; identify one active station with valid timestamps, units and cadence.
6. Define canonical event schema and provenance model.
7. Implement Python ingestion and Kafka topics.
8. Implement Spark validation, event-time windows and sensor-health logic.
9. Implement deterministic risk engine and detector baselines.
10. Add TimescaleDB and Grafana/Prometheus.
11. Build Chroma knowledge base with verified ICAR/FAO/regional documents.
12. Implement bounded investigator agent and guardrails.
13. Build farmer PWA and approval/feedback workflow.
14. Add Lenses/PostgreSQL/Grafana MCP integrations as services become available.
15. Run controlled B1/B2/B3 experiments and fault-injection/scalability benchmarks.
16. Package AgriKafka DevKit after the workflow stabilises.

Build incrementally. Do not ask Antigravity to generate the entire system in one prompt.

---

## 15. Existing user environment context

The user works on Windows and uses Google Antigravity IDE.

Previously reported environment:
- Windows with WSL2.
- WSL version previously reported: 2.7.12.0.
- Docker version previously reported: 29.7.2.
- Docker Compose version previously reported: v5.4.0.
- Python 3.13.1 previously reported.
- Git 2.53.0 previously reported.
- Node.js v22.22.1 previously reported.
- Rust/Cargo 1.93.1 previously reported.

These versions are historical reports, not guaranteed current. Verify before setup. Spark/PySpark compatibility may require a specific Java and Python version; do not assume Python 3.13 will be compatible with the selected Spark release.

---

## 16. Source project documents

The user previously uploaded three project documents. They should be treated as the original source of truth for course requirements and project baseline:

1. `AgriKafka-Agent Project Overview, Design and Plan.md`
2. `SPA Lab-Environment_Tools_and_Setup [Edited].pdf`
3. `SPA Lab-Synopsis[Edited](1).pdf`

Key details from those documents:
- Historical dataset is 175,200 hourly rows, ten virtual Karnataka fields, 5 Oct 2024–4 Oct 2026.
- Proposed initial stack included Kafka, PySpark Structured Streaming, PostgreSQL, AI advisor, dashboard, Docker Compose.
- Detailed project plan specified TimescaleDB, Chroma, Sentence Transformers, Telegram approval, Grafana, Prometheus, detector comparisons and fault injection.
- Course demo window was stated as 19–26 November 2026 in the project overview; verify whether still current.
- Team must explicitly disclose that data is reanalysis/modelled plus injected events, not physical field sensors.
- Literature review references in the initial deck need verification; the project overview said 13 of 30 references could not be traced.

---

## 17. Instructions for the next ChatGPT conversation

Start by acknowledging this handover and continue from the development/setup stage.

Do not re-explain the entire project unless asked.

The immediate task is to turn the toolkit shortlist into an Antigravity-ready setup:

1. Verify exact external skill folder names and `SKILL.md` content in the selected GitHub repositories.
2. Check current Antigravity skill/plugin installation conventions and MCP configuration format.
3. Decide which 5–8 external skills to install first; do not overload the workspace.
4. Generate the five `.agents/rules/*.md` files and initial custom skill templates.
5. Prepare safe MCP configuration examples using environment variables, not hardcoded secrets.
6. Create an installation/setup prompt for Google Antigravity that inspects the environment before modifying it.
7. Keep setup incremental and ask before destructive actions, installing software, exposing ports or using paid services.

Be exact: some skill names in the earlier 20-skill shortlist were descriptive labels and must be verified against their actual repositories before issuing install commands. Likewise, verify marketplace plugin availability rather than assuming a named plugin can be installed.
