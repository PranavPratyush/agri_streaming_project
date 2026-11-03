# AgriKafka-Agent — Project Brief & Source of Truth

**Project Title:** AgriKafka-Agent: Fault-Tolerant, Real-Time Agricultural Risk Monitoring and Decision Support  
**Course:** AI372IA — Stream Processing and Analytics  
**Team:** Aanish Khan, Daksh Chauhan, Pranav Pratyush  
**Faculty Guides:** Dr. Vijayalakshmi M N and Dr. S. Anupama Kumar  
**Status:** Baseline Specification (Stage 0 Complete)  

---

## 1. System Invariants (Non-Negotiable Guardrails)

These eight core architectural invariants govern all design, implementation, and evaluation in this project:

1. **Kafka is the Event Backbone:** All telemetry, contextual observations, detection events, agent actions, farmer feedback, and operational metrics pass through partitioned, replayable Kafka topics.
2. **PySpark Structured Streaming for Windowed Processing:** PySpark performs high-volume stream ingestion, event-time windowing, watermarking, stateful aggregations, stream-stream joins, and contextual feature generation.
3. **Deterministic Services for Health & Risk:** Data-quality checks, physical plausibility, sensor-health forensics, and agronomic crop-water/risk calculations are executed by deterministic code services—never by an LLM.
4. **Selective LLM Investigation:** The LLM/agent investigates **only** selected candidate alerts flagged by stream detectors.
5. **No LLM Call per Raw Reading:** High-frequency readings flow exclusively through Kafka and Spark. Zero raw telemetry events trigger LLM inference directly.
6. **Strict Separation of User Interfaces:**
   - **Farmer PWA:** Field-level decisions, simple explanations, transparent evidence, and actionable approval/rejection.
   - **Grafana Dashboard:** Engineering operations, pipeline telemetry, consumer lag, detector diagnostics, and system health.
7. **No Autonomous Physical Actuation:** The system produces bounded recommendations requiring human review. No automated irrigation valves, chemical sprayers, or physical actuators are triggered without explicit farmer approval.
8. **Empirical Semantics Claim:** Never claim end-to-end exactly-once processing or commercial parity without empirical proof and documented recovery test evidence.

---

## 2. Product Purpose & Problem Statement

### Purpose
AgriKafka-Agent is a real-time agricultural monitoring and decision-support system that combines live environmental telemetry, data-quality and sensor-health assessment, crop-context-aware risk detection, and a bounded tool-using AI investigator that produces evidence-grounded recommendations for human approval.

### Core Questions Answered
1. Is something unusual happening in this field?
2. Is it a genuine environmental/crop risk, or is the underlying data unreliable (sensor fault, noise)?
3. What empirical evidence and agronomic literature support this assessment?
4. What practical, verified next step should the farmer take?
5. Can the stream processing and reasoning pipeline recover gracefully when brokers, workers, or external APIs fail?

### Problem Statement & Research Gaps
Threshold-based agricultural monitoring floods farmers with false alarms because it cannot distinguish genuine crop stress from sensor malfunctions (drift, stuck values, spikes) or transient noise. Existing agentic farming assistants operate primarily as isolated, request-response chat applications lacking a durable, partitioned stream backbone, stream-level fault recovery, or rigorous citation grounding.

This project designs, implements, and benchmarks an event-driven architecture uniting Apache Kafka, PySpark Structured Streaming, deterministic triage engines, and a bounded tool-using agent with strict guardrails and human-in-the-loop validation.

---

## 3. Two Distinct User Experiences

| Dimension | Farmer Experience (PWA) | Operations & Research Dashboard (Grafana) |
|---|---|---|
| **Primary Audience** | Farmers, field managers, agricultural extension workers | System engineers, researchers, evaluators |
| **Interface Technology** | Mobile-first responsive Progressive Web App (PWA) + Telegram notifications | Grafana + Prometheus + TimescaleDB SQL queries |
| **Key Views** | Field status, crop growth stage, data freshness, clear alerts, plain-language evidence, action cards (Approve/Reject) | Kafka topic throughput, partition lag, Spark micro-batch latency, DLQ volume, detector anomaly scores, agent token cost |
| **Language & Accessibility**| English + Kannada support, low-bandwidth resilience, high-contrast field visibility | Technical charts, heatmaps, logs, metric traces |
| **Farmer Abstraction** | Complete abstraction from Kafka, Spark, consumer groups, and anomaly math | Direct visibility into infrastructure metrics and fault-recovery states |

---

## 4. System Architecture & Component Boundaries

```text
====================================================================================================
                                      LIVE & REPLAY DATA SOURCES
   [Live Physical Station / openSenseMap]   [Open-Meteo Replay Backbone]   [Injected Fault Harness]
====================================================================================================
                                                   │
                                                   ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ INGESTION LAYER (Python Connectors, Schema Normalisation, Provenance Tagging, Idempotent Producer)│
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                   │
                                                   ▼
====================================================================================================
                                      APACHE KAFKA (KRaft Mode)
  Topics: sensor-readings | weather-data | validated-observations | sensor-health | crop-alerts
          agent-actions   | feedback     | dead-letter            | agri-ops-metrics
====================================================================================================
                     │                                                     ▲
                     ▼                                                     │
┌───────────────────────────────────────────────────────────────────────┐  │
│ PYSPARK STRUCTURED STREAMING                                          │  │
│ - Watermarking & Event-Time Windowing (5m tumbling, 30m sliding)      │  │
│ - Stream-Stream Enrichment (Sensor Telemetry ⨝ Weather Context)       │  │
│ - Quality Assessment & Flatline Differentiation                       │  │
│ - Baseline Detectors: EWMA, Rolling Z-Score, Isolation Forest         │  │
└───────────────────────────────────────────────────────────────────────┘  │
                     │                                                     │
                     ▼ (Candidate Alerts Only)                             │
┌───────────────────────────────────────────────────────────────────────┐  │
│ BOUNDED ALERT INVESTIGATOR AGENT (Consumer Group: agri-agent-core)    │  │
│ 1. Read-Only Deterministic Tool Execution:                            │  │
│    - get_sensor_health()          - get_field_history()               │  │
│    - get_weather_forecast()       - get_crop_profile()                │  │
│    - retrieve_agronomy_guidance() (Chroma Vector Store: ICAR/FAO)     │  │
│ 2. Triage Reasoning: Classifies as [real_stress | sensor_fault | noise]│  │
│ 3. Advisory Drafting: Grounds action in retrieved passages            │  │
└───────────────────────────────────────────────────────────────────────┘  │
                     │                                                     │
                     ▼                                                     │
┌───────────────────────────────────────────────────────────────────────┐  │
│ DETERMINISTIC GUARDRAILS (Non-LLM Validation)                         │  │
│ - Strict JSON Schema validation & Citation ID verification            │  │
│ - Safety filter: blocks pesticide dosages & autonomous actuation      │  │
│ - Uncertainty detection & fallback on low confidence / LLM timeout    │  │
└───────────────────────────────────────────────────────────────────────┘  │
                     │                                                     │
                     ├─────────────────────────────────────────────────────┘
                     ▼
====================================================================================================
                              HUMAN APPROVAL & PERSISTENCE LAYER
   [Farmer PWA & Telegram: Approve / Reject] ───► [Kafka topic: feedback] ───► [TimescaleDB]
                                                                                     │
                                                                                     ▼
                                                                            [Grafana Dashboard]
====================================================================================================
```

---

## 5. Data Paths & Source-of-Truth Distinctions

Every record in AgriKafka-Agent strictly maintains provenance metadata to prevent conflating physical measurements with synthetic or modelled data.

### Source Categories & Provenance Tagging
1. **Physical Sensor (`source_type: physical_sensor`):** Direct in-situ hardware (e.g. verified openSenseMap station or private IoT gateway). Contains hardware ID, depth, placement, battery, RSSI.
2. **External Weather Station (`source_type: weather_station`):** In-situ atmospheric stations (e.g., IMD AWS/ARG or university station). Measures ambient temperature, RH, pressure, rain gauge. Not representative of field soil moisture.
3. **Modelled / Reanalysis Data (`source_type: reanalysis_model`):** Gridded historical estimates (Open-Meteo ERA5 / Land reanalysis). Zero missing values by design. Soil moisture is modelled, not measured.
4. **Forecast Data (`source_type: numerical_forecast`):** Numerical weather predictions (Open-Meteo API, IMD district forecast). Look-ahead context only.
5. **Derived Features (`source_type: derived_calculation`):** Computed by PySpark (e.g., VPD, leaf-wetness proxy, Crop Water Stress Index, rolling z-scores).
6. **Historical Replay (`source_type: historical_replay`):** Accelerated playback of historical data through Kafka with preserved event timestamps and simulation watermarks.
7. **Injected Scenarios (`source_type: injected_fault | injected_stress`):** Controlled perturbations introduced to benchmark detectors (e.g. stuck sensor, sensor drift, sudden spike, drought dry-down, heatwave). Ground-truth labels are stored in evaluation manifests.

---

## 6. Technology Stack Preferences

| Tier | Component | Selection | Rationale |
|---|---|---|---|
| **Messaging** | Event Backbone | Apache Kafka (KRaft mode, 3 brokers) | Course requirement; KRaft eliminates ZooKeeper; partitioned by `field_id`. |
| **Processing**| Stream Processing | PySpark Structured Streaming | Unified event-time windowing, watermarking, micro-batch state stores, checkpoint recovery. |
| **Storage** | Time-Series Database | TimescaleDB (PostgreSQL) | Hypertables optimized for time-series sensor aggregates, SQL compatibility, direct Grafana integration. |
| **Vector DB** | Knowledge Retrieval | Chroma | Embedded, zero-cloud-cost vector store for ICAR, FAO-56, and regional agronomy packages. |
| **Embeddings**| Dense Embeddings | `sentence-transformers` (e.g., `all-MiniLM-L6-v2`) | High throughput, local inference, no per-token API cost. |
| **Agent Core**| Triage & Reasoning | Bounded Tool Calling (LangGraph / direct Python) | Strict state transition, conditional branching, inspectable tool calls. |
| **LLM Tier** | Inference | Dual mode: Hosted API (Gemini/OpenAI/Groq) + Local Ollama fallback | High-quality reasoning with local zero-cost resilience fallback. |
| **Operations**| Telemetry & Metrics | Prometheus + Grafana | Industry standard for broker metrics, consumer lag, and pipeline observability. |
| **User Apps** | Farmer Interface | Responsive PWA + Telegram Bot | Instant notification with low-bandwidth, accessible web app for field profile management. |

---

## 7. Safety, Guardrails & Bounded Agent Limits

### Non-LLM Responsibilities (Deterministic Services)
- Numerical sensor-health metrics (stuck value, delta limits, spike detection).
- Statistical anomaly detection (EWMA, rolling z-score, Isolation Forest).
- Water balance and agronomic index math (FAO-56 Penman-Monteith, ET0).
- Citation ID checking against the Chroma retrieval manifest.
- JSON output schema enforcement.

### Agronomic Safety Guardrails
- **No Chemical Dosages:** The system will never output exact pesticide, herbicide, or chemical fertilizer mixing quantities. Only cultural practices, irrigation scheduling, and general IPM guidance from ICAR/KAU are permitted.
- **Uncertainty & Abstention:** If sensor health is degraded or data freshness exceeds threshold, the agent must label the condition as `unreliable_data` or `sensor_fault` and refuse to recommend irrigation action.
- **Human-in-the-Loop:** All advisories are pending recommendations until approved or dismissed by the human farmer via PWA or Telegram.

---

## 8. Evaluation Framework & Research Benchmarks

AgriKafka-Agent will be evaluated systematically against predefined quantitative benchmarks across four dimensions:

### 1. Detector Comparison (Stream Layer)
Compare static thresholding, EWMA, rolling Z-score, and windowed Isolation Forest on ~60 labeled scenarios:
- Metrics: Precision, Recall, Macro-F1, Detection Latency (seconds from event onset to alert).

### 2. Agentic Triage & Grounding Comparison
Benchmark three architectural variants on the same alert corpus:
- **Variant B1:** Deterministic rules & statistical thresholding only.
- **Variant B2:** Single LLM with pre-assembled prompt context + RAG.
- **Variant B3:** Bounded tool-using investigator agent + RAG + deterministic guardrails.
- Metrics: Macro-F1 (`real_stress`, `sensor_fault`, `noise`), Alert Reduction Rate at equal recall, Citation Grounding Rate (percentage of recommendations matching verified retrieval text), Unsafe/Hallucination Rate, Token Cost & Latency.

### 3. Fault Tolerance & Stream Resilience
Execute automated chaos drills:
- Kill 1 of 3 Kafka brokers (KRaft leader election & partition availability).
- Kill a PySpark worker node (micro-batch state recovery from checkpoint).
- Sever LLM API connection (triggering rule-based fallback).
- Metrics: Mean Time to Recovery (MTTR), Data Loss (target: 0), Duplicate Actions (target: 0 via alert deduplication), Consumer Lag drain rate.

### 4. Scalability & Throughput
Evaluate scaling behavior by varying partitions (1, 3, 6) and fields (10 to 1,000):
- Metrics: End-to-end P95/P99 latency, Messages per second (throughput).

---

## 9. Known Limitations & Disclosure

1. **Reanalysis vs In-Situ Sensors:** The primary 2-year Karnataka dataset consists of Open-Meteo ERA5-Land reanalysis estimates. Soil moisture is modelled, not directly measured by a buried probe. This distinction must be prominently disclosed in all reports and papers.
2. **Synthetic / Injected Faults:** Because natural public datasets rarely include labeled agricultural sensor hardware failures alongside verified crop stress, test scenarios are generated via calibrated injection.
3. **Regional Scope:** Agronomic guidance is initially bounded to selected Karnataka agro-climatic zones and specific crop profiles (e.g., Ragi/Maize/Tomato in Red Sandy Loam).
4. **Advisory Nature:** AgriKafka-Agent does not replace certified agronomists or soil testing laboratories.
