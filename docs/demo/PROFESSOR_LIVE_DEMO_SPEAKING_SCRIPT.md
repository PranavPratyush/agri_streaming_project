# AgriKafka-Agent: Professor-Facing Live Demonstration Speaking Script

**Demonstration Title:** Fault-Tolerant, Real-Time Agricultural Risk Monitoring and Bounded Multi-Agent Decision Support  
**Target Duration:** 15–20 minutes  
**Demonstrators:** Aanish Khan, Daksh Chauhan, Pranav Pratyush  
**Evaluation Domains:** Stream Processing & Analytics (SPA) + Agentic Artificial Intelligence (AAI)  

---

## [00:00 – 02:30] Phase 1: Architecture, Problem Formulation & Safety Invariants

### 🖥️ Screen / Visual:
- Open `docs/architecture/ARCHITECTURE_V1.md` or display the high-level architecture diagram.
- Highlight the strict architectural boundary between the **Deterministic Stream Processing Pipeline** and the **Bounded Multi-Agent Decision Layer**.

### 🗣️ Speaking Script:
> "Good afternoon, Professors. Today we are presenting **AgriKafka-Agent**, an end-to-end, fault-tolerant platform for real-time agricultural crop risk monitoring and decision support, grounded in the semi-arid agro-ecological context of Kolar District, Karnataka, focusing on rainfed Finger Millet (*Eleusine coracana*, Ragi GPU-28) in red sandy loam (*Alfisols*).
>
> In agricultural technology, an all-too-common design flaw is treating AI as an oracle—feeding unvalidated, noisy raw telemetry directly into Large Language Models. In real fields, sensors suffer from battery depletion, physical fouling, ADC quantization noise, and intermittent network outages. If an LLM directly generates irrigation or chemical spray commands from faulty telemetry, it causes severe crop damage and economic loss.
>
> To solve this, our architecture enforces two foundational safety invariants:
> 1. **Dual-Engine Separation:** Every sensor reading is strictly verified through deterministic physical rate-of-change and sensor-health filters before entering an agronomic risk engine. Only statistically significant, physics-verified candidate risk events trigger agentic investigation.
> 2. **Zero Autonomous Physical Actuation:** Neither AI agents nor human reviewers can ever dispatch autonomous hardware commands to pumps or sprayers. The platform produces accredited, evidence-backed advisories that require explicit human approval."

---

## [02:30 – 05:00] Phase 2: Live Ingestion & Fault-Tolerant Transport

### 🖥️ Screen / Visual:
- Open Terminal 1.
- Run: `.venv\Scripts\python.exe services/ingestion/src/agri_ingestion/cli.py live-osm --station-id 689b2bdc569c2d0007586ae9 --once --dry-run`
- Show the formatted JSON event output.

### 🗣️ Speaking Script:
> "Let us examine Phase 2: Ingestion and Event Normalization.
> 
> As you can see on the terminal, our Python ingestion service is actively polling physical station `Sarvamangalam` on the openSenseMap network at Lat 12.00°N, Lon 79.80°E. 
> Notice the metadata in the output:
> - The payload adheres to our canonical schema version `1.0.0` defined using Pydantic v2.
> - The `provenance` block records `is_synthetic: false` and explicitly tags the origin as `physical_sensor` with raw payload hashes.
> - Telemetry latency is calculated in real time—here it is currently 19 seconds.
> - Each event is assigned a deterministic compound `idempotency_key` based on station, sensor ID, and event timestamp, ensuring deduplication throughout downstream processing.
>
> If an external provider experiences an outage, our ingestion adapter enforces bounded exponential backoff and automatically routes unparseable or failed messages to our Kafka Dead-Letter Queue (`agri.dead-letter-queue`) without crashing the ingestion service."

---

## [05:00 – 07:30] Phase 3: Sensor Health Forensics & Deterministic Crop Risk

### 🖥️ Screen / Visual:
- Open Terminal 1.
- Run: `.venv\Scripts\python.exe services/risk-engine/src/agri_risk_engine/cli.py audit-thresholds`
- Open code file: `services/risk-engine/src/agri_risk_engine/health/detectors/flatline.py` around line 45.

### 🗣️ Speaking Script:
> "Now let us turn to Stream Processing and Analytics: Sensor Health Forensics.
>
> On screen is our deterministic threshold configuration table. Notice that our parameters are not arbitrary heuristics—every value has explicit scientific provenance.
> For example:
> - The stuck sensor variance epsilon is set to $10^{-4}$, which corresponds to the ADC quantization noise floor of typical capacitive soil sensors.
> - The rate of change limit for ambient temperature is 5.0 °C per minute, grounded in WMO-No. 8 and IMD meteorological observation standards.
> 
> A major analytical breakthrough in our pipeline is **natural flatline differentiation**. In typical industrial IoT, zero variance is naively flagged as a stuck sensor. However, in agriculture:
> 1. Rain gauges legitimately read zero for weeks during rainless periods.
> 2. Soil moisture reaches a residual dry plateau (hygroscopic water) where moisture does not fluctuate.
> 
> Our `FlatlineDetector` implements physical exemption logic: if atmospheric VPD is elevated and cumulative precipitation is zero, it exempts the dry plateau from being falsely flagged as a hardware fault. In our 24-fixture benchmark, this achieved a Precision of 1.0, Recall of 1.0, and 0 False Positives."

---

## [07:30 – 12:00] Phase 4: Bounded Multi-Agent Investigation Architecture

### 🖥️ Screen / Visual:
- Open Terminal 1.
- Run Healthy Investigation:  
  `.venv\Scripts\python.exe services/alert-investigator/src/agri_investigator/cli.py investigate --field-id field-kolar-001 --severity HIGH --sensor-health HEALTHY`
- Open code file: `services/alert-investigator/src/agri_investigator/supervisor.py` lines 180–310.

### 🗣️ Speaking Script:
> "Now we demonstrate our core Agentic AI contribution: the **Multi-Agent Investigation Architecture**.
>
> In response to faculty feedback, this is **not** a single LLM with tools, nor is it six uncoordinated chatbots. It is a formal, bounded pure-Python supervisor managing six specialist agents with typed message contracts:
>
> 1. **Sensor Reliability Agent:** Consumes raw observations and deterministic health results. It verifies whether readings are physically trustworthy for agronomic decision-making.
> 2. **Field Context Agent:** Simultaneously looks up parcel soil characteristics (Red Sandy Loam / Alfisols), root-zone depth (0.5m), and current phenological growth stage (Flowering / Grain Filling).
> 3. **Crop Risk Analyst Agent:** Consumes both outputs and calculates biological stress—verifying that soil moisture has dropped below the critical FAO-56 depletion threshold ($p=0.65$).
> 4. **Agronomy Knowledge Agent:** Queries our Chroma vector knowledge base to retrieve accredited package-of-practices guidance from ICAR-CRIDA and UAS Bangalore.
> 5. **Agricultural Advisory Agent:** Synthesizes the evidence into an actionable advisory card, complete with assumptions, limitations, and citations.
> 6. **Critic / Safety Agent:** Audits the advisory against strict safety policies. It verifies that every cited document ID exists, that no prohibited synthetic chemical dosages are recommended, and that no guaranteed outcomes are claimed.
>
> Notice in the CLI output:
> - Total messages exchanged: 12.
> - Citations verified: `TNAU-AGRITECH-RAGI-2020:SEC02:CH01`.
> - State transitioned to `awaiting_human_review`.
>
> Now watch what happens when we introduce a sensor fault:
> *(Run `.venv\Scripts\python.exe services/alert-investigator/src/agri_investigator/cli.py investigate --sensor-health FAULTY`)*
>
> Notice that the Sensor Reliability Agent immediately catches the `STUCK_VALUE_DETECTED` flag, and the Supervisor terminates the workflow with `ABSTAINED_SENSOR_FAULT`. Downstream advisory generation is halted, completely preventing hallucinated recommendations."

---

## [12:00 – 14:30] Phase 5: Agronomy Corpus & RAG Retrieval Engine

### 🖥️ Screen / Visual:
- Open Terminal 1.
- Run: `.venv\Scripts\python.exe packages/agronomy-rag/src/agri_agronomy_rag/cli.py query "ragi protective irrigation drought" --limit 3`
- Open `knowledge/source-register.csv`.

### 🗣️ Speaking Script:
> "Let us look at Phase 5: Grounded Retrieval-Augmented Generation.
>
> Our RAG service operates independently from agent execution so it can be evaluated quantitatively.
> We indexed 5 audited Indian agricultural extension documents:
> - FAO-56 Irrigation and Drainage Paper
> - UAS Bangalore Package of Practices for Ragi GPU-28
> - ICAR-CRIDA District Contingency Plan for Kolar
> - TNAU Agritech Portal Millet Guide
> - ICAR-AICRP Small Millets Annual Report
>
> Documents are embedded using `sentence-transformers/all-MiniLM-L6-v2` in ONNX format (384 dimensions) and indexed in ChromaDB with cosine distance HNSW.
> In the terminal output, you see our top 3 retrieval matches:
> 1. `ICAR-CRIDA-DRYLAND-2019:SEC03:CH01` with relevance score 0.6511.
> 2. `UASB-POP-RAGI-2022:SEC03:CH01` with relevance score 0.5644.
>
> In our gold-standard evaluation across 10 representative queries, our retrieval engine achieved a Mean Recall@3 of 0.80 and a Mean Reciprocal Rank (MRR) of 0.7333 with average latency of 288 milliseconds."

---

## [14:30 – 17:30] Phase 6: Farmer PWA & Human Review Lifecycle

### 🖥️ Screen / Visual:
- Open browser at `http://localhost:5173` (Farmer PWA).
- Show:
  1. Overview screen with moisture deficit alert.
  2. Trends screen with FAO-56 critical threshold line.
  3. Alert detail screen showing the 5-milestone investigation tracker.
  4. Advisories screen and click `Approve` or `Request Inspection`.
  5. Toggle language button to show Kannada (ಕನ್ನಡ).

### 🗣️ Speaking Script:
> "Now let us view the interface built for the actual user: the **Farmer Responsive Progressive Web App (PWA)**.
>
> Built using React 18, Vite, and TypeScript, this PWA is optimized for low-bandwidth mobile viewports and meets WCAG 2.1 AA accessibility standards:
> - **Field Overview:** Farmers see their active parcel, current soil moisture (0.12 m³/m³), and visual data provenance tags distinguishing ground probes from weather stations.
> - **Depletion Trends:** The trends screen plots soil moisture against the critical FAO-56 depletion threshold of 0.166 m³/m³, visually explaining why the field is under water stress.
> - **Transparent Multi-Agent Progress:** In the alert detail view, we provide a 5-milestone progress bar. Farmers see that sensor reliability was verified, field context was reviewed, risk was analyzed, agronomic knowledge was retrieved, and the Critic passed safety validation. Notice that raw prompt text and hidden chain-of-thought are strictly hidden—farmers see clear, actionable summaries only.
> - **Human Review Controls:** Advisories require human review. When an agronomist clicks `Approve`, an idempotent request updates the database to `APPROVED`. If someone attempts a conflicting action later, the API rejects it with HTTP 409 Conflict.
> - **Bilingual Support:** With one tap, the entire UI switches seamlessly between English and Kannada (ಕನ್ನಡ), ensuring regional accessibility."

---

## [17:30 – 20:00] Phase 7: Observability, Persistence & Comprehensive Verification

### 🖥️ Screen / Visual:
- Run full test suite: `.venv\Scripts\python.exe -m pytest tests/unit/ tests/contract/ -q`
- Open `infra/grafana/dashboards/01-system-overview.json` or show Grafana provisioned dashboards.

### 🗣️ Speaking Script:
> "To conclude, let us examine System Reliability, Persistence, and Observability.
>
> In Terminal 1, we are executing our complete test suite covering contract schemas, ingestion adapters, PySpark windowing, sensor health benchmarks, risk engines, persistence repositories, RAG retrieval, multi-agent state machines, FastAPI endpoints, and notification dispatches.
> Notice: **173 passed, 1 skipped (100% pass rate)**.
>
> In our persistence layer:
> - TimescaleDB hypertables store time-series observations and candidate alerts partitioned on event time.
> - Idempotent upserts prevent duplicate records on Kafka consumer replay.
> - A dedicated read-only role (`agri_readonly`) protects reporting queries.
>
> In our operational monitoring layer:
> - Prometheus scrapes standardized, low-cardinality metrics across all services.
> - 6 actionable alert rules detect sustained consumer lag, stale source telemetry, and dead-letter queue growth.
> - 7 production-grade Grafana dashboards provide full observability from Kafka broker throughput down to individual agent execution latencies.
>
> In summary, AgriKafka-Agent successfully bridges real-time stream processing with grounded, safety-bounded multi-agent decision support. We welcome your questions."

