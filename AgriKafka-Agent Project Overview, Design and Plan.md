# AgriKafka-Agent: Project Overview, Design and Plan

Oct 15, 2026 · @Pranav

## What the final project will be and do

AgriKafka-Agent will be a working system that watches 10 virtual crop fields in real time, decides whether an alert is real crop stress or a sensor fault, and recommends an action that a farmer approves with one tap.

The finished deliverable has four parts:

- **A one-command stack.** Docker Compose starts a 3-broker Kafka cluster, a PySpark streaming job, TimescaleDB, a vector store for agronomy documents, the agent services, Grafana and a Telegram bot.
- **A live replay.** Two years of hourly weather and soil data for 10 Karnataka fields stream through Kafka at accelerated speed (for example, one hour of data per second).
- **A dashboard and phone alerts.** Grafana shows live readings, stress index, alerts and agent decisions. Telegram delivers each recommendation with Approve and Reject buttons.
- **Results and a paper.** Benchmark tables comparing detectors, agent variants, failure recovery and throughput, written up as an IEEE-format technical paper.

### What a live demo looks like

1. Start the stack. Producers replay the dataset into Kafka, and the dashboard begins to move.
2. Spark computes 5-minute tumbling and 30-minute sliding window aggregates per field, plus a Crop Stress Index. EWMA, z-score and Isolation Forest flag suspicious windows onto the `crop-alerts` topic.
3. The presenter injects two events: a drought-style dry-down in field 4, and a stuck soil-moisture sensor in field 7.
4. The triage agent reads each alert, queries recent history, neighbouring fields and the weather forecast, and classifies it. Field 7 is labelled `sensor_fault` because the flat reading contradicts nearby fields and recent rain. Field 4 is labelled `real_stress` with a confidence score and its evidence.
5. For field 4, the advisor agent retrieves ICAR/FAO passages and drafts a recommendation. A guardrail checks the output format, requires a source citation, and blocks pesticide or chemical dosage advice.
6. The farmer gets a Telegram message, approves it, and the decision returns through a `feedback` topic and appears on the dashboard.
7. Failure round: kill a Kafka broker, a Spark worker and one agent instance, then block the LLM API. The pipeline recovers without losing events, and a rule-based fallback keeps recommendations flowing.

### What it will not do

It will not control real irrigation hardware or act without human approval. Its data is reanalysis weather and soil values plus injected faults, not readings from physical sensors.

## Problem statement and research gaps

**Problem statement.** Threshold-based crop monitoring floods farmers with alerts because it cannot tell real crop stress from sensor faults or transient noise. Existing agentic farming assistants are request-response applications. They are rarely built on a durable, fault-tolerant stream backbone, and their recommendations are rarely checked for grounding. This project builds and evaluates an event-driven pipeline in which Kafka and windowed stream processing detect candidate stress events. A tool-using LLM agent then triages each event, grounds its recommendation in retrieved agronomy sources, and publishes it for human approval, while the system tolerates broker, consumer and LLM failures.

### Research gaps

These gaps come from the searches run so far. State them in the paper as "to the best of our search", and try to disprove each one before you present it.

| # | Gap | Evidence found |
| --- | --- | --- |
| G1 | No agricultural agentic system found that runs on a partitioned, replayable Kafka backbone. Agentic farming papers use REST or edge designs, and Kafka farming papers have no reasoning layer. | CottonBot, a multi-agent farming framework, Farm-LightSeek; a Kafka/Spark plus LLM paper exists only in healthcare |
| G2 | Alerts are not triaged in-stream into real stress, sensor fault or noise. Fault detection is offline, and stress detection assumes clean data. | Rogue soil-sensor detection paper; streaming Isolation Forest on greenhouse data |
| G3 | The agent stage is rarely evaluated as part of a stream: grounding rate, fallback when the LLM fails, duplicate-free replay. | 2026 review noting that deployed systems lack domain-specific hallucination detection |
| G4 | End-to-end latency and recovery benchmarks exclude any LLM stage. | Kafka and Flink benchmark papers are generic |

### Research questions

- **RQ1.** Does agentic triage reduce false alerts reaching the farmer versus threshold-only and statistics-only baselines, without missing true stress events?
- **RQ2.** What share of agent recommendations is grounded in retrieved sources, and how does that compare with an ungrounded LLM?
- **RQ3.** What latency does the agent layer add, and does the system recover from failures without data loss or duplicates?

## Proposed solution

The solution splits the work by speed: Kafka and Spark handle the high-volume, fast detection, and the LLM agent only reasons about the small number of alerts that survive.

**1. Ingestion.** Producers replay real Open-Meteo weather and soil data for 10 virtual fields into Kafka, keyed by `field_id` so each field's readings stay ordered within a partition. A separate producer publishes weather context.

**2. Stream detection.** A PySpark Structured Streaming job joins the two streams on event time, computes tumbling and sliding window aggregates, and calculates a composite Crop Stress Index from temperature, vapour pressure deficit, soil moisture and a leaf-wetness proxy. Three detectors (EWMA, rolling z-score, windowed Isolation Forest) flag windows that look abnormal. Only flagged windows reach the `crop-alerts` topic.

**3. Agentic layer.** Agent services form their own consumer group on `crop-alerts`.

- **Triage agent.** Uses tools to fetch field history, neighbouring fields and the forecast, then outputs JSON: class (`real_stress`, `sensor_fault` or `noise`), confidence and evidence.
- **Advisor agent.** Retrieves ICAR/FAO passages from a local vector store and drafts a recommendation that cites them.
- **Guardrail validator.** Plain code, not an LLM. It checks the JSON schema, requires valid citation IDs, and blocks dosage advice.
- **Notifier.** Plain code that formats and sends the Telegram message.

**4. Human approval.** The farmer approves or rejects each recommendation in Telegram. Decisions go to a `feedback` topic and are stored.

**5. Storage and display.** Aggregates, alerts, agent decisions and latencies are written to TimescaleDB. Grafana reads from it for dashboards and alert rules.

**6. Fault tolerance.** Kafka replication, idempotent producers, Spark checkpoints, committed consumer offsets, a dead-letter topic, LLM timeouts and retries with a rule-based fallback, and alert-ID keyed actions so replays do not send duplicates.

**Why this design.** Calling an LLM on every raw reading would be too slow and costly. Putting it after windowed detection keeps the stream fast, and keeping the guardrail as deterministic code keeps recommendations safe.

## System architecture and methodology

&#91;embedded content: architecture · data flow through Kafka topics\]

Data flows top to bottom, and every arrow between stages passes through a Kafka topic, so a crashed stage resumes from its last committed offset instead of losing events.

### Kafka topics

| Topic | Written by | Read by |
| --- | --- | --- |
| `sensor-readings` | Sensor replay producer, keyed by `field_id` | Spark streaming job |
| `weather-data` | Weather producer | Spark streaming job |
| `crop-alerts` | Spark streaming job | Agent layer consumer group |
| `agent-actions` | Agent layer | Telegram bot and the TimescaleDB writer |
| `feedback` | Telegram bot (farmer decisions) | TimescaleDB writer |
| `dead-letter` | Spark job and agents (failed records) | Manual review |

### Methodology in six steps

1. **Data ingestion.** Replay Open-Meteo data for 10 virtual fields, with labeled faults and stress events injected.
2. **Stream detection.** Window the joined streams, compute the Crop Stress Index, and compare EWMA, z-score and Isolation Forest.
3. **Agentic core.** Triage each alert, retrieve agronomy sources for real stress, validate the draft, and send it for approval.
4. **Evaluation.** Run about 60 labeled scenarios against four baselines and measure classification, alert reduction, grounding and latency.
5. **Resilience testing.** Kill brokers, workers and agents, and block the LLM, then measure recovery and data integrity.
6. **Scalability testing.** Vary partitions, consumers and field count, then measure throughput and P99 latency.

## Datasets

The baseline is real Open-Meteo hourly weather and soil data for 10 Karnataka locations, with labeled faults and stress events injected on top. No public dataset was found that has both labeled sensor faults and labeled stress events, so the labels are created by the team.

### Primary dataset (already collected)

| Property | Value |
| --- | --- |
| Source | Open-Meteo Historical Weather API |
| Coverage | 10 virtual fields across Karnataka |
| Period | 5 Oct 2024 to 4 Oct 2026, hourly |
| Size | 175,200 rows (17,520 per field), 14 columns |
| Analytical variables | Temperature, relative humidity, dew point, precipitation, vapour pressure deficit, wind speed, soil moisture (0-7 cm) |
| Metadata columns | field\_id, timestamp, requested and grid latitude and longitude, elevation |
| Not available | NPK, pH, direct leaf wetness (leaf wetness is derived from humidity and dew point) |

Open-Meteo values come from reanalysis models, so soil moisture is modelled rather than read from a probe. The paper should say this plainly. Zero missing values is a property of gridded data, which is why faults must be injected.

### Injected events (ground truth)

- **Sensor faults:** stuck value, spike, drift, dropout, out-of-range.
- **Crop stress events:** drought dry-down, heat wave, a humid and mild disease-risk window.

Each injected event is logged with its field, start, end and type. These logs are the labels for the detector and agent evaluation.

### Optional validation datasets

Use these to study how real sensors behave, and to calibrate the fault injector.

| Dataset | What it adds | Caveat |
| --- | --- | --- |
| Purdue WHIN open dataset | Real LoRa soil sensors and weather stations: gaps, noise, stuck values | Indiana corn and soy; check the licence |
| Mendeley Smart Agriculture and Plant Health Monitoring | Timestamped soil moisture, pH and TDS from a low-cost IoT build | Small hobby-grade deployment |
| Kaggle IoT Agriculture 2024 | Larger greenhouse set with N and P channels | Greenhouse in Iraq |
| Kaggle soil moisture field-scale network | Multi-depth soil series | No weather columns |

### EDA findings so far

These numbers are as reported in the Phase I deck. Re-run the notebook before you quote them in the paper.

- **Integrity:** 0 missing values, 0 duplicate field and timestamp pairs, exact 1-hour cadence.
- **Daily cycle:** mean temperature rises from 20.46 C at 05:00 to 29.58 C at 14:00, while humidity falls from 86.80% at 06:00 to 47.09% at 14:00.
- **Correlations:** VPD vs relative humidity -0.94, VPD vs temperature +0.87, temperature vs humidity -0.75, humidity vs soil moisture +0.50.
- **Rain to soil lag:** 7 of 10 fields peak at 1 hour, but the strongest correlation is only r = 0.297, so treat the lag as a weak guide for window sizing.
- **Natural flatlines:** precipitation stays flat for 983 to 2,107 hours and soil moisture for 149 to 679 hours. Fault rules must not treat long flat runs as faults on their own.
- **EWMA anomaly rate on clean data:** soil moisture 2.09%, precipitation 1.36%, VPD 0.29%, humidity 0.04%, temperature 0%.
- **To double-check:** a natural one-hour temperature jump of 7.9 to 12.3 C looks too large for this region, so check for a timezone or join artifact.

## Tools and techniques

Every tool below is free or has a free tier, and the stack is written mostly in Python so one team can own all of it.

| Layer | Choice | Why this one |
| --- | --- | --- |
| Messaging | Apache Kafka, KRaft mode, 3 brokers in Docker Compose | Required by the course; KRaft removes the ZooKeeper dependency |
| Stream processing | PySpark Structured Streaming | Built-in event-time windows, watermarks, stream joins and checkpoints; same language as the agent |
| Anomaly detection | EWMA, rolling z-score, windowed Isolation Forest (scikit-learn or River) | Gives a measurable three-way comparison |
| Crop health | Composite Crop Stress Index | Uses variables the dataset has; CWSI would need canopy temperature |
| Time-series storage | TimescaleDB | SQL, and Grafana support out of the box |
| Vector store and RAG | Chroma with sentence-transformers embeddings | Local and free; holds ICAR/FAO passages |
| Agent framework | Python tool-calling, or LangGraph | Explicit tool calls are easy to debug; model-agnostic |
| LLM | Hosted API (free tier) or Ollama locally | Hosted for quality, local as a no-cost fallback |
| Dashboard | Grafana | Live panels and alert rules |
| Alerts and approval | Telegram bot | Phone delivery with Approve and Reject buttons |
| Evaluation | pytest scenario harness, Kafka performance tools, Prometheus | Reproducible numbers for the paper |

### Techniques used

- **Windowing:** 5-minute tumbling windows for baselines and 30-minute windows sliding every 5 minutes for trends.
- **Event-time processing:** watermarks to handle late or out-of-order records when joining sensor and weather streams.
- **Aggregation and summarisation:** mean, min, max and standard deviation per window, plus the stress index.
- **Stream enrichment:** joining readings with weather context before alerting.
- **Retrieval-augmented generation:** recommendations must cite retrieved passages.
- **Guardrails and human-in-the-loop:** deterministic validation and farmer approval before any action is recorded.

## Evaluation plan

The project is judged on numbers, not on a demo alone. Four experiments answer the three research questions.

### 1. Stream detectors

Compare a static threshold, EWMA, rolling z-score and windowed Isolation Forest on the injected events. Metrics: precision, recall, F1 and detection delay.

### 2. Agent triage and recommendations

Build about 60 labeled scenarios (30 real stress, 20 sensor faults, 10 noise) and run four systems on them.

| System | Description |
| --- | --- |
| B1 | Threshold rules only |
| B2 | Statistical triage (EWMA) with no LLM |
| B3 | LLM with no tools and no retrieval |
| B4 | Full AgriKafka-Agent: tools, retrieval, guardrail |

Metrics: macro-F1 of the three classes, alert-reduction rate at equal recall of true stress, grounding rate (share of recommendations with valid retrieved citations, checked by hand), unsafe or wrong rate from manual review, and per-stage latency.

### 3. Resilience

Kill a Kafka broker, a Spark worker and an agent instance, and block the LLM API. Record mean time to recovery, message loss, duplicate processing, and how often the fallback path runs. The target is zero lost messages and zero duplicate actions.

### 4. Scalability

Vary topic partitions (1, 3, 6) and consumer instances, and scale from 100 to 1,000 virtual fields. Record throughput in messages per second and P99 end-to-end latency.

Decide the pass thresholds (for example, the minimum recall of true stress) before running the experiments, so the results cannot be tuned after the fact.

## Course requirements and Phase II timeline

Every item in the course circular maps to a component you can point at during the demo. Phase II demonstrations run 19 to 26 November 2026, and all team members must be present or lose marks.

| Circular requirement | Where it is met | Demo evidence |
| --- | --- | --- |
| Kafka as central platform | 3-broker KRaft cluster | Topic list and broker status |
| Producer and consumer | Replay producers; Spark, agent and notifier consumers | Live message flow |
| At least two topics | `sensor-readings`, `weather-data`, `crop-alerts`, `agent-actions`, `feedback`, `dead-letter` | Topic describe output |
| Partitioning and consumer groups | Keyed by `field_id`; agent group scaled from 1 to 3 instances | Rebalance shown live |
| Window-based operation | 5-minute tumbling and 30-minute sliding windows | Window output in Grafana |
| Aggregation or summarisation | Per-window statistics and Crop Stress Index | Stored aggregates |
| Fault tolerance and recovery | Replication, checkpoints, offsets, dead-letter topic, LLM fallback | Kill-and-recover round |
| Database or time-series store | TimescaleDB | SQL query on results |
| Visualisation or alerts | Grafana dashboard, Telegram alerts | Live dashboard and phone |
| Agentic AI (added requirement) | Triage and advisor agents with guardrail and human approval | Fault versus stress classification on stage |

### Proposed timeline

&#91;embedded content: proposed timeline · 8 workstreams to Lab CIE\]

Build the core path first (Kafka, Spark windows, detectors), so the agent, the evaluation and the fault-tolerance demo get the most time. The technical paper is submitted at Phase II and updated for the Lab CIE.

## Risks, limitations and literature notes

The biggest risk right now is the literature review, not the engineering. Thirteen of the 30 references in the Phase I deck (numbers 1 to 11, 14 and 15) could not be traced, so they must be verified or removed before the paper.

### Literature actions

- Open every reference, and delete any you cannot find with a title, authors and DOI or URL.
- Replace removed papers with ones you have read, and reach at least 25 distinct verified papers.
- Remove the duplicate Ag 5.0 Frontiers entry, and fix the mismatched plant water stress rows.
- Rewrite the gap and existing-system slides around papers you actually opened, so the novelty claim stays consistent.

### Project risks

| Risk | Why it matters | Mitigation |
| --- | --- | --- |
| Modelled data, not physical sensors | Reviewers may question realism | State it openly; calibrate faults using WHIN or other real sensor data |
| Injected labels favour the method | The agent could look better than it is | Fix the scenario set and thresholds before testing; include hard and ambiguous cases |
| LLM cost, rate limits or downtime | The demo could stall | Rule-based fallback, response caching, a local Ollama model |
| Spark stream joins are hard to debug | Time loss late in the project | Build the join early; the fallback is detection on the sensor stream alone |
| Hallucinated or unsafe advice | Trust and safety | Retrieval with required citations, deterministic guardrail, human approval |
| Too much scope for 5 weeks | Unfinished evaluation | Build the core path first; treat multi-agent specialisation and extra datasets as optional |

### Limitations to state in the paper

- Results come from reanalysis data plus injected faults, not a field deployment.
- The agent recommends and never actuates; closed-loop control is out of scope.
- The gap claims hold "to the best of our search" and may need narrowing if a counterexample appears.
