# AgriKafka-Agent — Complete Antigravity Development Prompt Playbook

**Project:** AgriKafka-Agent: Fault-Tolerant, Real-Time Agricultural Risk Monitoring and Decision Support  
**Course:** AI372IA — Stream Processing and Analytics  
**IDE:** Google Antigravity  
**Operating environment:** Windows + WSL2 + Docker Desktop (verify current versions)  
**Execution model:** One stage at a time; inspect, implement, test, review, then continue.

---

## How to use this playbook

This document contains the ordered prompts to give Google Antigravity. Do not paste the entire playbook as one request. Start with Prompt 0, wait for its report, then give the next prompt only after the stated gate is satisfied.

**Before starting:** place the project handover file (`AgriKafka-Agent_Development_Handover(1).md`, or the latest canonical handover) inside the Antigravity project workspace, preferably at `docs/project/reference/`. Antigravity cannot automatically read a file that was uploaded only to a separate ChatGPT conversation. Also place the original project overview, synopsis, environment/setup document and historical dataset in the workspace if they are available; keep large datasets in their existing location and tell Antigravity where they are.

The project has four phases and 23 stages:

| Phase | Stages | Main outcome |
|---|---:|---|
| I. Foundation | 0–5 | Verified workstation, repository, Antigravity operating rules, selected skills/MCPs, architecture decisions |
| II. Data engineering | 6–13 | Verified live source, canonical event contract, Kafka, ingestion/replay, Spark, sensor health, risk engine, time-series storage |
| III. Intelligence and application | 14–19 | Observability, agronomy RAG, bounded investigator, backend API, farmer PWA, notifications and feedback |
| IV. Validation and delivery | 20–22 | B1/B2/B3 experiments, resilience drills, integration/performance validation, reproducible demo and documentation |

### Operating rules for every stage

1. Give Antigravity **one prompt at a time**. Do not ask it to execute later stages early.
2. Antigravity must inspect the repository and relevant documentation before changing files.
3. It must provide a plan before non-trivial implementation. For destructive changes, software installation, paid services, public exposure of ports, credential creation, or changes outside the workspace, it must stop and obtain explicit approval.
4. It must not overwrite, delete, rename, or restructure existing project files without explaining why and receiving approval.
5. It must prefer small, reversible changes over broad rewrites.
6. It must run relevant tests and show actual command output or a concise evidence summary. A successful build alone is not proof of correctness.
7. It must never invent test results, data-source availability, sensor measurements, agronomic thresholds, citations, benchmark numbers, or deployment status.
8. It must preserve the distinction between physical sensor readings, external station observations, weather-model/forecast values, historical reanalysis, derived features, and injected test data.
9. It must never send an LLM every raw reading. Kafka/Spark and deterministic services process the stream; the AI investigator is invoked only for selected candidate alerts.
10. No autonomous irrigation, chemical application, disease diagnosis, or physical actuation. Recommendations are advisory and require human review.
11. Use local-only service binding by default. Never commit secrets. Use environment variables or a local secret store and least-privilege credentials.
12. Keep a stage log in `docs/development/BUILD_LOG.md`, recording prompt/stage, files changed, commands run, test results, decisions, unresolved issues, and the gate status.

### Standard completion report required after every stage

Antigravity must end every stage with:

- **Implemented:** what actually changed.
- **Files changed:** exact paths.
- **Commands executed:** exact commands, with meaningful output summaries.
- **Tests:** passed/failed/not run, with reasons.
- **Evidence:** how the result was verified.
- **Risks and assumptions:** anything still uncertain.
- **Decisions made:** link to or identify ADRs where relevant.
- **Gate:** `PASS`, `PASS WITH EXPLICIT LIMITATIONS`, or `BLOCKED`.
- **Next prompt:** name the next stage, but do not execute it.

Proceed only when the gate is `PASS`, or when the user explicitly accepts a documented limitation.

---

# Phase I — Foundation

## Stage 0 — Establish the project context and Antigravity operating contract

**Purpose:** Load the handover into the workspace, establish a source of truth, and prevent architectural drift before any code is written.

### Prompt 0 — Project bootstrap and working agreement

```text
You are the lead engineer for the AgriKafka-Agent project. Locate the canonical project handover in this workspace, preferably `docs/project/reference/AgriKafka-Agent_Development_Handover(1).md`, and read it completely before acting. If it is not present, STOP and tell me exactly which file to copy into the workspace. Do not pretend you can access an attachment from a separate ChatGPT conversation. Do not proceed with architecture changes until the handover is available or I explicitly tell you to use only the project brief below.

Project identity:
AgriKafka-Agent: Fault-Tolerant, Real-Time Agricultural Risk Monitoring and Decision Support.
Course: AI372IA — Stream Processing and Analytics.
Team: Aanish Khan, Daksh Chauhan, Pranav Pratyush.
Faculty guides: Dr. Vijayalakshmi M N and Dr. S. Anupama Kumar.

First, inspect the current workspace. Do not create or modify application code yet.

Tasks:
1. Locate and read all available project documents, existing source code, datasets, diagrams, environment files, and README files. Do not assume the repository is empty.
2. Create `docs/project/PROJECT_BRIEF.md` as a concise, structured, workspace-level source of truth. Include product purpose, two user experiences (farmer PWA and operations dashboard), system architecture, data paths, technology preferences, open decisions, safety constraints, evaluation plan, and known limitations.
3. Create `docs/project/OPEN_DECISIONS.md` for unresolved choices. At minimum include: live source/station, first crop and soil context, Python/Java/Spark/Kafka/database versions, API framework, PWA framework, LLM provider/deployment mode, LangGraph versus direct tool calling, vector store/embedding model, event serialization/schema registry decision, and deployment target.
4. Create `docs/development/BUILD_LOG.md` with Stage 0 as the first entry. Future stages must append to it.
5. Create `docs/architecture/` and `docs/decisions/` directories if they do not exist.
6. Add a clear `README.md` only if one does not already exist. If it exists, propose targeted updates instead of replacing it.
7. Record all source-of-truth distinctions: physical sensors, external weather stations, modelled/reanalysis data, forecasts, derived features, historical replay, and injected scenarios.
8. Capture the following invariants prominently:
   - Kafka is the event backbone.
   - PySpark Structured Streaming performs stream processing and contextual feature work.
   - Data-quality, sensor-health, and crop-risk calculations are deterministic services.
   - The LLM/agent investigates only selected candidate alerts.
   - No LLM call per raw reading.
   - Farmer PWA is for field decisions; Grafana is for engineering/operations.
   - No autonomous physical actuation; human approval is required.
   - Never claim exactly-once end-to-end processing without evidence.

Do not install packages, connect MCP servers, download repositories, expose ports, or modify existing application logic in this stage.

Before editing, show a short inventory and proposed file changes. Then create only the documentation listed above. Finish with the standard completion report and a Stage 0 gate.
```

**Gate:** The project brief, open-decisions register, build log, and initial inventory exist. No application code or environment has been changed.

---

## Stage 1 — Audit the development environment

**Purpose:** Confirm compatibility before installing or upgrading anything. Python 3.13 and the previously reported Java/Spark versions must not be assumed compatible.

### Prompt 1 — Read-only workstation and toolchain audit

```text
Perform a READ-ONLY development environment audit for AgriKafka-Agent on this Windows + WSL2 + Docker Desktop workstation.

Do not install, upgrade, uninstall, or modify anything. Do not start containers or expose ports. Collect current evidence rather than relying on old notes.

Inspect and report:
1. Windows version/build and architecture.
2. WSL status, WSL version, installed distributions, distribution versions, and whether Docker Desktop WSL integration is enabled (report only what can be verified).
3. Docker Engine and Docker Compose versions; `docker info`; available resources if visible.
4. Git version and current global/local configuration relevant to line endings and identity (do not reveal credentials).
5. Python launcher, installed Python versions, active interpreter, pip, venv support, and whether `uv` or another package manager is present.
6. Java runtime and `JAVA_HOME`; identify all installed JDKs.
7. Node.js and npm/pnpm/yarn versions.
8. Available disk space and memory relevant to local Kafka, Spark, database, and frontend development.
9. Google Antigravity version/build, available CLI (`agy`) and its version if installed, and current project/workspace root.
10. Whether ports likely needed by the project are already occupied. Do not kill processes.
11. Existing project folder structure and any existing virtual environments.

Use official compatibility documentation for the proposed PySpark/Spark, Java, and Python versions. Do not recommend a version combination unless the compatibility is documented. Prefer a stable, mutually compatible Python/JDK/Spark combination over using the newest version automatically.

Create `docs/development/ENVIRONMENT_AUDIT.md` containing:
- detected values;
- command/evidence used for each value;
- compatibility matrix for candidate Python, Java, PySpark/Spark, Kafka, and Docker versions;
- blockers and risks;
- a proposed pinned toolchain;
- a minimal installation/change plan, but do not execute it.

If any value cannot be verified, mark it UNKNOWN. Do not guess.

Finish with the standard completion report. Stage gate is BLOCKED if a critical runtime compatibility question remains unresolved.
```

**Gate:** `ENVIRONMENT_AUDIT.md` contains verified versions and a documented compatible toolchain. Any required installation is a separate, approval-based action.

---

## Stage 2 — Create or stabilise the repository structure

**Purpose:** Establish a maintainable monorepo without prematurely generating services.

### Prompt 2 — Repository skeleton and developer workflow

```text
Using the Stage 0 project brief and Stage 1 environment audit, prepare the AgriKafka-Agent repository skeleton.

First inspect the current repository and preserve existing files. Propose the structure before creating it. Do not generate full service implementations.

Use a modular monorepo structure similar to the following, adapting only when the existing repository gives a good reason:

- `apps/farmer-pwa/`
- `services/api/`
- `services/ingestion/`
- `services/stream-processor/`
- `services/risk-engine/`
- `services/alert-investigator/`
- `services/notification-worker/`
- `packages/event-contracts/`
- `packages/shared-python/`
- `infra/docker/`
- `infra/kafka/`
- `infra/prometheus/`
- `infra/grafana/`
- `data/historical/` (do not move large datasets without approval)
- `data/scenarios/`
- `knowledge/` (documents and metadata; do not place copyrighted documents here unless permitted)
- `tests/unit/`, `tests/integration/`, `tests/contract/`, `tests/scenarios/`, `tests/resilience/`
- `docs/project/`, `docs/architecture/`, `docs/decisions/`, `docs/development/`, `docs/experiments/`
- `.agents/rules/`, `.agents/skills/`

Create only directories and minimal placeholder READMEs where helpful. Add or refine:
- root README with project purpose and setup status;
- `.gitignore` for Python, Node, Docker, IDE, datasets, secrets, generated artifacts, checkpoints and local model files;
- `.env.example` files containing names and safe placeholders only;
- a contribution/development note explaining tests and stage gates.

Choose a Python packaging/workspace approach based on the Stage 1 audit. Do not create conflicting dependency managers. Document the chosen approach before implementing it.

Do not create real credentials, API keys, empty fake service implementations, or unverified Docker images. Do not commit actual datasets unless their licensing and size are clear.

Add the repository skeleton and decisions to the build log. Run only structural checks and any safe formatting checks available. Finish with the standard completion report.
```

**Gate:** A clearly documented monorepo structure exists; no service logic is generated prematurely; existing files are preserved.

---

## Stage 3 — Verify and install external Antigravity skills

**Purpose:** Install a small, verified working set rather than the entire 20-skill shortlist. The handover's descriptive names are not guaranteed to match current repository folder names.

### Prompt 3 — Skill repository audit, selection, and controlled installation

```text
Audit the external Agent Skills proposed for AgriKafka-Agent. Do not install anything until you have verified the actual repository contents and shown me the selection.

Repositories to inspect:
1. https://github.com/addyosmani/agent-skills
2. https://github.com/vaquarkhan/data-engineering-agent-skills
3. https://github.com/lensesio/agentic-engineering-for-apache-kafka
4. https://github.com/sickn33/agentic-awesome-skills

For each repository:
- inspect the current default branch and latest commit/release;
- locate the actual skill directories and their `SKILL.md` files;
- verify the exact directory name, frontmatter, purpose, supported tools/agents, dependencies, scripts, and references;
- check license and any installation instructions;
- identify whether the skills are compatible with the current Google Antigravity IDE and its open Agent Skills format;
- flag shell scripts, network actions, or any installer that writes outside the workspace.

Treat the following as CANDIDATES, not guaranteed folder names:
- Software engineering: spec-driven-development, planning-and-task-breakdown, incremental-implementation, test-driven-development, code-review-and-quality.
- Data engineering: data-specification, data-quality-and-contract-testing, data-resiliency-testing-and-failure-injection, safe-backfill-and-replay-orchestration, kafka-resilience-and-schema-evolution, data-contract-testing-with-schema-registry.
- Kafka: kafka-python-client, kafka-topic-audit, kafka-consumer-lag, kafka-dlq-review.
- Agent/RAG: ai-agents-architect, rag-engineer.

Recommend a focused initial pack of 8–10 skills, including:
- specification/planning;
- incremental implementation and testing;
- Kafka Python/topic operations;
- data contracts/quality;
- replay/resilience;
- bounded agent/RAG design.

Prefer exact, currently existing skills with clear value for our next stages. Do not install overlapping skills just to increase the count. Defer skills that only become useful after a subsystem exists.

Before installation, produce `docs/development/EXTERNAL_SKILL_AUDIT.md` with repository URL, commit hash, exact skill folder, verified purpose, license, compatibility evidence, installation risk, and recommendation.

After I approve the proposed list, copy the complete selected skill folders into `.agents/skills/<exact-skill-folder>/`, preserving references, scripts, examples, and metadata. Do not flatten folders. Do not run untrusted installers. Do not install global skills. Do not overwrite an existing skill without approval.

After installation, verify every `SKILL.md`, list the installed skills, and explain how to invoke them in Antigravity. Finish with the standard completion report.
```

**Gate:** Exact skill folders and their `SKILL.md` files are verified; selected skills are installed locally under `.agents/skills/`; no unreviewed installer has run.

---

## Stage 4 — Create project rules and eight custom skills

**Purpose:** Make project-specific constraints reusable and version-controlled.

### Prompt 4 — Author AgriKafka rules and custom skills

```text
Create the AgriKafka-Agent project-specific Antigravity rules and custom Agent Skills. Use the current official Google Antigravity documentation for rule/skill format and locations. Do not assume plugin or CLI behaviour from old examples.

Create these five rules under `.agents/rules/`:

1. `architecture-guardrails.md`
   - Kafka is the event backbone.
   - PySpark Structured Streaming handles stream processing and contextual feature work.
   - Deterministic services handle data quality, sensor health, and numerical risk calculations.
   - The LLM/agent is only invoked for selected candidate alerts.
   - Never invoke an LLM for every raw reading.
   - Farmer PWA and engineering Grafana dashboard are separate interfaces.
   - No autonomous physical actuation.

2. `data-provenance.md`
   - Every event preserves source, source type, event time, ingestion time, units, field/sensor/station identifiers, location where available, and quality/provenance labels.
   - Never represent modelled/reanalysis soil moisture as a physical sensor measurement.
   - Never represent a remote station as a measurement from a farmer's field.
   - Preserve original payload/reference for audit where lawful and practical.

3. `agronomic-safety.md`
   - No unsupported disease diagnosis, invented crop thresholds, pesticide/chemical dosage, or autonomous physical action.
   - Crop recommendations must be grounded in verified agronomic sources and state uncertainty.
   - If field profile or evidence is incomplete/contradictory, abstain or request inspection.
   - Human approval is mandatory for recommendations/actions.

4. `security-and-secrets.md`
   - No credentials, tokens, passwords, or private endpoints in committed files.
   - Local-only service exposure by default.
   - Least privilege for service and MCP accounts.
   - Never run destructive commands or expose public ports without approval.
   - Do not send private data to hosted services unless explicitly approved.

5. `testing-and-evaluation.md`
   - Every component requires relevant tests.
   - Preserve reproducibility and log experiment parameters.
   - Distinguish synthetic/injected labels from real field ground truth.
   - Never fabricate performance or model results.
   - Do not claim exactly-once semantics without a proof and scoped definition.

Create eight custom skills under `.agents/skills/`, each with a valid `SKILL.md` and supporting examples/references as appropriate:

1. `agri-event-contracts` — canonical event schema, event IDs, units, timestamps, provenance, versioning and compatibility tests.
2. `live-sensor-ingestion` — live source connectors, polling/MQTT/webhooks, rate limits, retries, normalisation, freshness, idempotency and Kafka publishing.
3. `sensor-health-forensics` — stale/missing data, stuck values, spikes, drift, dropout, plausibility, natural flatlines and confidence/unknown states.
4. `crop-risk-modelling` — crop/variety/growth-stage/soil/sensor-depth context, water-balance features, explainable risk calculations and calibration limitations.
5. `agri-rag-grounded-advisory` — ICAR/FAO/regional source ingestion, provenance, chunking, embeddings, retrieval evaluation, citation integrity and abstention.
6. `bounded-alert-investigator` — permitted read-only tools, conditional investigation workflow, budgets/timeouts, evidence sufficiency, confidence, abstention and safety.
7. `agrikafka-evaluation-harness` — fixed scenarios and B1 rules/statistics, B2 single LLM + RAG, B3 bounded agent + RAG comparisons.
8. `stream-resilience-benchmarking` — broker/worker/agent failure, retry, DLQ, replay, checkpoint recovery, duplicate action, MTTR, throughput and P99 latency testing.

Every custom skill must:
- have correct YAML frontmatter with a concise name and description;
- state when to use it and when not to use it;
- give a step-by-step procedure;
- define inputs, outputs, invariants and failure cases;
- include concrete examples and verification criteria;
- link to supporting reference files without loading everything by default;
- avoid duplicating the entire project brief.

Do not make these skills claim a capability that has not been implemented. Mark future workflows as planned. Configure rule activation thoughtfully: global security, provenance, architecture and safety invariants should always apply; detailed skills should load when relevant.

Validate all files for correct syntax and internal consistency. If an Antigravity CLI validator exists, inspect its current help/version and use it only if supported. Do not package a plugin yet.

Finish with the standard completion report and list all created rule and skill files.
```

**Gate:** Five rules and eight custom skills exist, parse correctly, and do not contradict the project brief.

---

## Stage 5 — Select the implementation stack and freeze the first architecture

**Purpose:** Resolve open decisions through evidence and ADRs before code depends on them.

### Prompt 5 — Architecture decisions and ADRs

```text
Review `PROJECT_BRIEF.md`, `OPEN_DECISIONS.md`, `ENVIRONMENT_AUDIT.md`, and the current repository. Produce a decision proposal for the first working end-to-end prototype.

Decisions to evaluate:
1. Python version and package manager.
2. Java/JDK and PySpark/Spark version combination.
3. Kafka distribution/image and KRaft single-broker development profile.
4. Kafka client library.
5. Event format: JSON Schema initially versus Avro/Protobuf plus Schema Registry. Consider local setup complexity, evolution, validation, and course demonstration needs.
6. Backend API framework (FastAPI is a candidate, not a foregone conclusion).
7. Farmer PWA frontend framework and build tool.
8. TimescaleDB/PostgreSQL image and extension compatibility.
9. Chroma deployment mode and Sentence Transformers embedding model.
10. Agent implementation: LangGraph versus direct Python tool calling. Prefer the least complex design that provides observable conditional tool selection, bounded steps, and auditability.
11. LLM deployment: hosted API versus Ollama/local model. Compare privacy, latency, structured outputs, availability, cost, and reproducibility. Do not invoke a paid service or download a large model.
12. Authentication approach for local prototype and human approvals.
13. Docker Compose profiles and network exposure.

For every choice provide: options, compatibility evidence, operational cost, learning/setup complexity, failure modes, recommendation, and consequences. Use current primary documentation and Context7 where available. Pin exact versions only when verified.

Create separate ADRs in `docs/decisions/` for the decisions that materially affect interfaces or dependencies. Update `OPEN_DECISIONS.md` and a versioned architecture diagram in `docs/architecture/`.

Design two runtime profiles:
- `dev`: one Kafka broker, local database, and minimum required services.
- `resilience`: multi-broker Kafka configuration and additional components used for failure demonstrations.

Do not implement services or start paid/cloud resources in this stage. Ask me before any choice that implies paid usage, external data transfer, or a large local model download.

Finish with the standard completion report and a list of decisions that still need my approval.
```

**Gate:** Core stack decisions are documented in ADRs; critical compatibility issues are closed; paid/external decisions have explicit approval status.

---

# Phase II — Data engineering

## Stage 6 — Verify live data sources and select a demonstrable station

**Purpose:** Prove that a live feed is actually accessible and suitable before building ingestion around it.

### Prompt 6 — Live source reconnaissance and station verification

```text
Investigate and verify the live data-source candidates for the AgriKafka-Agent demonstration. Do not write production connectors yet.

Candidates:
1. IMD AWS/ARG observations and official API portal: https://api.imd.gov.in/
2. openSenseMap public sensor API: https://opensensemap.org/ and https://docs.opensensemap.org/
3. ThingSpeak public channels: https://thingspeak.com/
4. Open-Meteo current/forecast APIs: https://open-meteo.com/ (environmental context only; not a physical sensor source).

The previous handover records that the IMD candidate endpoint required access/registration and that some ThingSpeak channels were stale. Re-test rather than assuming either is currently available.

For every candidate:
- use official documentation and inspect API access/authentication requirements;
- identify an actual station/channel/device, not just a provider;
- verify last update, observed cadence, units, timestamp/time zone, coordinates, sensor type, variables, and terms/rate limits;
- make a small read-only request only if permitted;
- verify whether the returned record is a physical station measurement, model output, forecast, or user-published channel;
- assess whether the location is close enough to be useful as regional context for an initial Karnataka demonstration;
- record outages, missing variables, stale timestamps, or access barriers.

Do not publish credentials or scrape data against terms. Do not claim a source is live based on a static example response. Observe enough updates to assess its actual cadence where possible.

Select one primary live source and one fallback/context source only if evidence supports them. A weather-station feed may be used for real-time weather context, but it is not field soil-moisture telemetry. If no physical soil sensor feed is suitable, state that limitation honestly and keep field soil moisture on the historical/replay path until a real sensor is available.

Create `docs/project/LIVE_DATA_SOURCE_ASSESSMENT.md` with provider, endpoint/documentation, station ID, location, variables, units, last observation timestamp, observed cadence, authentication, rate limits, source classification, evidence, and limitations. Update `OPEN_DECISIONS.md`.

Do not create a connector or modify Kafka yet. Finish with the standard completion report.
```

**Gate:** At least one selected live feed has verified access, provenance, timestamp, units, and cadence. Otherwise the project proceeds only with the limitation clearly documented and an alternative approved.

---

## Stage 7 — Define canonical event contracts and provenance

**Purpose:** Establish one schema for live, historical replay, weather context, and injected scenarios without conflating their semantics.

### Prompt 7 — Canonical event schema and contract tests

```text
Design and implement the canonical AgriKafka-Agent event contracts. Read `agri-event-contracts` and the data-provenance rule first.

Inputs:
- live source assessment from Stage 6;
- existing historical Open-Meteo dataset, if present;
- approved technology decisions from Stage 5.

Design separate event types where appropriate, for example:
- environmental observation;
- weather context/forecast;
- sensor-health result;
- candidate crop-risk event;
- investigator action/result;
- human feedback/approval;
- dead-letter record.

The canonical observation contract must support:
- unique event ID and idempotency key;
- schema version;
- field ID, sensor/station ID where applicable;
- source provider and source type;
- observed variable, numeric value, unit;
- event timestamp and ingestion timestamp in UTC;
- latitude/longitude/elevation where legitimately available;
- sensor metadata and placement/depth when available;
- quality flags and validation status;
- provenance classification: `physical_sensor`, `external_station`, `modelled_reanalysis`, `forecast`, `derived`, `historical_replay`, or `injected_scenario` (refine names if justified, but keep semantics explicit);
- original source reference/payload hash where useful;
- optional correlation/trace ID.

Do not require a physical `sensor_id` for weather API/model observations. Do not fabricate sensor metadata. Use explicit null/unknown semantics.

Document units and canonical conversions. Validate timestamps, finite values, plausible data types, required identifiers, enum values, and versioning. Define how unknown variables and out-of-range values are handled. Keep invalid records available for diagnostics/DLQ rather than silently dropping them.

Implement schema definitions and unit/contract tests in `packages/event-contracts/`. Add representative JSON examples for each provenance class, including one historical soil-moisture record explicitly marked modelled/reanalysis and one physical station observation only if Stage 6 verified one.

Create `docs/architecture/EVENT_CONTRACTS.md` with field-level definitions, examples, compatibility policy, and provenance semantics. Do not create Kafka topics in this stage.

Finish with contract-test results and the standard completion report.
```

**Gate:** Contracts are versioned, tests pass, and sample records cannot silently confuse modelled data with physical readings.

---

## Stage 8 — Build the local Kafka KRaft infrastructure

**Purpose:** Stand up a reproducible, single-broker development environment, keeping the three-broker demonstration for the later resilience profile.

### Prompt 8 — Docker Compose and Kafka infrastructure

```text
Implement the local Kafka infrastructure using the approved Stage 5 ADRs and the event contracts from Stage 7.

First inspect the current Docker and Compose configuration. Preserve useful existing services. Create a minimal, pinned, single-broker Kafka KRaft development profile. Do not use ZooKeeper. Use a maintained image and verified configuration.

Requirements:
1. Kafka data must use a named persistent Docker volume.
2. Configure internal Docker-network listeners separately from any host listener.
3. Bind host ports to localhost only unless explicitly approved otherwise.
4. Add health checks and clear startup dependencies.
5. Keep credentials/secrets out of Compose literals and source control.
6. Provide an `.env.example` with safe placeholders only.
7. Define topic configuration as code or repeatable scripts, not undocumented manual setup.
8. Document partition count, replication factor, retention, cleanup policy, key strategy, and rationale for each topic.
9. Use one deliberate topic naming scheme; do not mix the earlier `sensor-readings` style and `agri.raw` style without a documented decision.
10. Include the approved core topics for raw observations, weather context, validated observations, sensor health, candidate risk events, agent actions, feedback, dead-letter records, and operational metrics as appropriate.
11. Use a replication factor compatible with the single-broker dev profile; do not pretend it proves broker redundancy.
12. Add scripts/commands for topic creation, inspection, and clean local shutdown. Never delete volumes automatically.

Test the profile with a small producer/consumer smoke test and verify persistence across a container restart. Do not create the multi-broker resilience profile yet.

Create `docs/architecture/KAFKA_TOPOLOGY.md` and update the root README. Do not implement production ingestion or Spark jobs in this stage.

If a software install, port conflict, volume deletion, or network exposure is required, stop and ask. Finish with the standard completion report.
```

**Gate:** Kafka starts locally, topics are reproducibly created, a message can be produced/consumed, and persistence is verified without deleting volumes.

---

## Stage 9 — Implement live ingestion and historical replay

**Purpose:** Create distinct source adapters that publish the same canonical event format while retaining source provenance.

### Prompt 9 — Python source connectors and replay producer

```text
Implement the Python ingestion layer using the `live-sensor-ingestion` skill and the verified source decision from Stage 6.

Build separate adapters for:
1. the approved live station/API source;
2. weather/forecast context if approved;
3. the existing historical Open-Meteo dataset replay path;
4. deterministic injected test scenarios (clearly marked as injected).

Requirements:
- all adapters emit Stage 7 canonical contracts;
- preserve provider timestamps and capture ingestion timestamps separately;
- normalise time zones to UTC without discarding the original time-zone context where relevant;
- normalise units only through documented conversions;
- include retry with bounded exponential backoff and jitter where appropriate;
- handle rate limits, transient HTTP errors, malformed records, authentication failures, and source outages;
- use timeouts and graceful shutdown;
- make Kafka publishing idempotent using event identity/keys and producer settings supported by the selected client;
- include structured logs and source-level metrics;
- route malformed/unrecoverable records to the approved DLQ contract with original payload reference and error metadata;
- do not publish secrets or raw credentials in logs;
- never label historical replay or injected test data as live telemetry.

Historical replay must support:
- normal-speed replay;
- configurable accelerated replay;
- deterministic ordering by event time where required;
- start/end range selection;
- repeatable run ID and replay metadata;
- safe restart/resume semantics that avoid duplicate downstream actions.

Create unit tests with mocked HTTP responses and integration tests against local Kafka. Do not rely on a public API for ordinary automated tests. Add a CLI entry point and configuration examples. Record source limits and expected cadence.

Before live requests, confirm that the source access method is permitted and does not require an unapproved paid service. Finish with actual smoke-test evidence and the standard report.
```

**Gate:** Live and replay producers work independently; provenance remains intact; retry/DLQ and idempotency tests pass.

---

## Stage 10 — Implement PySpark Structured Streaming

**Purpose:** Build the streaming computation over Kafka events with event-time semantics and recoverable checkpoints.

### Prompt 10 — Spark stream processor

```text
Implement the AgriKafka-Agent PySpark Structured Streaming service. Read the approved runtime ADR and use the compatible Java/Python/Spark versions verified in Stage 1 and Stage 5.

Responsibilities:
1. Consume the approved raw observation and weather topics.
2. Parse and validate canonical event contracts.
3. Separate valid and invalid events; preserve rejection reasons and send invalid records to the DLQ path.
4. Apply event-time processing, explicit watermark policy, and windowed aggregations.
5. Handle late/out-of-order events according to a documented policy.
6. Deduplicate using the canonical event identity and bounded state appropriate to the event-time policy.
7. Join weather/context streams only where keys and time semantics justify it.
8. Produce validated observation and feature outputs to Kafka.
9. Persist Spark checkpoints on a durable named volume/path, not ephemeral container storage.
10. Support graceful shutdown and restart from checkpoints.

Do not put crop-risk decisions or LLM calls inside the raw parsing loop. This service should produce reliable, inspectable streaming features for downstream deterministic logic.

Create:
- a small, modular Spark application;
- configuration separated from code;
- schemas and transformations;
- unit tests for pure transformations;
- integration tests using local Kafka and small controlled fixtures;
- checkpoint/restart test;
- metrics for input rows, processed rows, invalid rows, late rows, processing time, and batch duration.

Document trigger interval, window definitions, watermark duration, state retention, checkpoint behaviour, and known limitations. Avoid claiming exactly-once end-to-end semantics. Explain the guarantees of each source/sink and the boundaries where duplicates can occur.

Run a small end-to-end stream with controlled data. Do not run a large replay until the smoke test passes. Finish with the standard completion report.
```

**Gate:** Spark consumes Kafka, processes event-time windows, writes outputs, handles invalid/late records, and recovers from a tested checkpoint.

---

## Stage 11 — Data quality and sensor-health forensics

**Purpose:** Distinguish unreliable telemetry from genuine environmental changes. Natural flatlines must not automatically become sensor faults.

### Prompt 11 — Sensor health engine

```text
Implement the deterministic sensor-health and data-quality subsystem. Use the `sensor-health-forensics` skill and the project safety/provenance rules.

Detect and classify at least:
- stale observations / excessive age;
- missingness and dropout;
- repeated/stuck values;
- implausible values and abrupt spikes;
- drift or gradual bias where supported by history;
- timestamp reversals, clock skew, duplicate IDs and irregular cadence;
- source outage versus sensor outage where the evidence allows distinction.

Important:
- Do not treat a long precipitation zero sequence as a faulty sensor by itself.
- Do not treat modelled soil-moisture flatlines as a physical sensor fault.
- A naturally stable environmental value is not sufficient proof of a stuck sensor.
- Use sensor type, measurement resolution, sampling cadence, operating range, location, and corroborating variables when available.
- Where there is insufficient context, return `unknown` or `suspect`, not a confident `faulty` label.

Define an explicit health state model such as `healthy`, `stale`, `suspect`, `faulty`, and `unknown`, plus reason codes and evidence fields. Keep numeric checks deterministic and independently testable.

For each detection rule, document:
- rule definition and formula;
- required context;
- configurable parameters and their evidence/source;
- false-positive risks;
- handling of missing/insufficient evidence;
- expected computational cost.

Do not invent universal thresholds. Store configurable thresholds with units, provenance, and rationale. Include synthetic fixtures for known faults and normal environmental patterns. Include tests for the handover's known risk: a long natural flatline should not be labelled faulty without corroboration.

Publish health events to the approved Kafka topic and make them queryable downstream. Ensure health status can block crop recommendations when the underlying measurement is unreliable.

Finish with confusion-matrix-style tests for labelled fixtures and the standard completion report.
```

**Gate:** Sensor-health states include reason/evidence, normal flatlines are protected by tests, and unhealthy/unknown inputs cannot silently drive recommendations.

---

## Stage 12 — Crop-context-aware deterministic risk engine

**Purpose:** Generate candidate agricultural risk events without pretending that arbitrary scores are validated crop-damage probabilities.

### Prompt 12 — Crop profile and risk detection engine

```text
Implement the deterministic crop-context-aware risk engine. Read `crop-risk-modelling` and `agronomic-safety.md` first.

Begin by proposing the smallest defensible initial crop and field context for the prototype. Use verified regional ICAR/agricultural-university/FAO material where available. Do not assume a crop, soil type, variety, sowing date, irrigation method, root depth, or growth stage when it has not been supplied.

Define a field profile model that can represent:
- field ID and location;
- crop and variety;
- sowing/transplanting date and growth stage;
- soil type and known properties;
- irrigation method;
- sensor type, placement and depth;
- crop-specific metadata with source/provenance.

Build an explainable deterministic risk engine using defensible inputs such as:
- validated temperature, humidity, rainfall, wind and vapour-pressure-deficit observations;
- soil-moisture values only with their correct provenance;
- crop growth stage and soil context;
- ET / crop-water indicators where FAO-56 or other verified methods are applicable;
- sensor-health status and data freshness.

Evaluate EWMA, rolling Z-score and Isolation Forest as detector candidates. Keep algorithms modular and compare their outputs on controlled fixtures. Do not force Isolation Forest into the streaming path if its deployment/maintenance cost is not justified.

A candidate event must include:
- alert ID and event time;
- field/profile reference;
- candidate category;
- contributing features and measurements;
- data-quality and sensor-health status;
- rule/model version;
- explanation/reason codes;
- confidence/uncertainty representation that is not falsely calibrated;
- provenance of input variables;
- conditions that caused suppression or abstention.

Do not call an arbitrary 0–100 score a probability of crop damage. If a composite index is proposed, document its formula, scale, calibration status, uncertainty and limitations. Use `candidate`, `watch`, or equivalent neutral semantics until validated.

A faulty or untrusted sensor must suppress or qualify recommendations based on that sensor. Incomplete crop context must result in an explicit limitation/abstention rather than fabricated field values.

Create unit and scenario tests for heat, dry-down, rainfall, recovery, conflicting signals, sensor faults, stale data and missing crop profile. Publish candidate alert events to Kafka.

Finish with formulas, evidence, test outcomes and the standard completion report.
```

**Gate:** Risk events are explainable and provenance-aware; unknown conditions cause abstention; no ungrounded crop thresholds or pseudo-probabilities are presented as validated.

---

## Stage 13 — TimescaleDB persistence and query layer

**Purpose:** Persist observations, features, health events, alerts, investigation results and feedback for history and analysis.

### Prompt 13 — TimescaleDB schema, sinks and data access

```text
Implement the TimescaleDB/PostgreSQL persistence layer using the approved ADR. Read current TimescaleDB compatibility documentation for the selected PostgreSQL image and pin compatible versions.

Design a migration-managed schema for:
- field and crop profiles;
- source/station/sensor metadata;
- raw or canonical observations (with provenance);
- validated observations and features;
- sensor-health events;
- candidate alerts;
- investigator reports/evidence references;
- recommendation/approval state;
- user feedback and audit history;
- ingestion/replay run metadata.

Requirements:
1. Choose hypertables only for time-series tables where their query/write profile justifies them.
2. Define unique constraints/idempotency keys to make reprocessing safe.
3. Index by field, time, variable, source, alert status, and other demonstrated query patterns.
4. Preserve the distinction between event time and ingestion time.
5. Define retention/compression policy only after documenting expected data volume and research needs; do not delete historical data automatically.
6. Use migrations and rollback guidance.
7. Use connection pooling and bounded retries.
8. Avoid storing secrets or unnecessary personal data.
9. Create a restricted, read-only database account for the coding agent/MCP inspection; do not grant schema modification or write access to that account.
10. Add integration tests for idempotent writes, duplicate events, time-range queries and schema migrations.

Implement Kafka-to-database sinks or service consumers with safe offset/commit handling and documented delivery semantics. Avoid claiming end-to-end exactly-once delivery. Show how database uniqueness and idempotent upserts prevent duplicate persisted records.

Create representative queries for field timeline, sensor freshness, recent alerts and alert evidence. Do not build the farmer UI yet.

Finish with migration/test evidence and the standard completion report.
```

**Gate:** Migrations apply cleanly, records persist with provenance, duplicate ingestion is safe, time-range queries are tested, and read-only access is configured separately.

---

# Phase III — Intelligence and application

## Stage 14 — Operational observability with Prometheus and Grafana

**Purpose:** Give the team visibility into pipeline health and research metrics without making Grafana the farmer interface.

### Prompt 14 — Prometheus metrics and Grafana dashboards

```text
Implement operational observability for AgriKafka-Agent. Grafana is the engineering/operations dashboard, not the farmer-facing product.

Instrument and expose metrics for:
- ingestion request success/failure, latency, records received and source freshness;
- Kafka broker health, topic throughput, consumer lag, under-replicated partitions where relevant, and DLQ volume;
- Spark input/processed/late/invalid rows, batch duration, processing latency and checkpoint/restart events;
- data-quality and sensor-health states;
- risk-engine candidate counts, suppressed alerts and processing latency;
- investigator invocation count, tool calls, timeouts, fallback rate, latency and token/cost metrics if available;
- API latency, error rate and database connection/query health;
- notification delivery attempts, deduplication and approval feedback counts.

Use Prometheus scraping and Grafana dashboards with version-controlled provisioning/configuration. Do not expose admin interfaces publicly. Use local-only bindings and secure default credentials via local environment configuration.

Create separate dashboards:
1. System overview.
2. Kafka and consumer groups.
3. Spark streaming and checkpoint health.
4. Ingestion/source freshness.
5. Data quality and sensor health.
6. Candidate alerts and investigator outcomes.
7. Reliability/evaluation metrics.

Use explicit units, labels and metric descriptions. Avoid high-cardinality labels such as unique event IDs. Add a small set of actionable alert rules for service down, stale source, sustained consumer lag, repeated Spark failures and DLQ growth.

Add tests or configuration validation where available. Create dashboard screenshots only after a working local deployment. Update the operations runbook.

Do not configure Grafana MCP yet unless the service is operational and a read-only account is available. Finish with the standard completion report.
```

**Gate:** Key components export metrics; dashboards load from version-controlled configuration; no secret or admin endpoint is exposed.

---

## Stage 15 — Build the agronomy knowledge base and RAG pipeline

**Purpose:** Retrieve verified agricultural guidance with provenance and citations; do not generate recommendations from unsupported web snippets.

### Prompt 15 — Agronomy corpus ingestion, Chroma and retrieval evaluation

```text
Build the AgriKafka-Agent agronomy knowledge-base and retrieval pipeline. Use `agri-rag-grounded-advisory` and the safety/provenance rules.

Approved source classes:
- FAO guidance, including FAO-56 where relevant;
- ICAR publications and advisories;
- relevant Indian state agricultural university material;
- verified crop-specific extension guidance.

First create a source register before downloading or ingesting documents. For every source record title, author/institution, publication date/version, canonical URL, access date, document type, crop/region applicability, rights/licence/usage note, and whether the document was actually retrieved and parsed.

Do not fabricate citations, publication metadata, document content, or retrieval results. Do not ingest paywalled or restricted documents without permission. If a source is not obtainable, record it as a candidate, not as evidence in the knowledge base.

Implement:
1. Document ingestion with format detection and text extraction.
2. Chunking that preserves section headings and document/page references.
3. Metadata and stable citation IDs.
4. Embeddings using the approved Sentence Transformers model or approved alternative.
5. Chroma persistence with collection/version metadata.
6. Retrieval with metadata filters for crop, region, document type and topic where available.
7. A retrieval interface returning text, source ID, title, page/section, URL and relevance score.
8. A citation validation function that rejects unknown IDs and unsupported references.

Create a small gold retrieval set with queries and expected source passages. Evaluate retrieval precision/recall or ranking metrics appropriate to the set; document sample size and limitations. Do not claim RAG quality from a few arbitrary examples.

Create a clear separation between retrieved agronomy guidance and live field measurements. Retrieval must never turn a modelled environmental input into a physical measurement.

Add tests for citation integrity, missing source metadata, chunk boundaries and no-result retrieval. Do not call the LLM for every ingestion item or sensor reading.

Finish with source register, corpus inventory, retrieval results, limitations and the standard completion report.
```

**Gate:** Corpus contains verified, traceable documents; citation IDs resolve; retrieval tests pass; missing evidence results in no-result/abstention rather than invented citations.

---

## Stage 16 — Implement the bounded Alert Investigator agent

**Purpose:** Demonstrate a genuine, controlled conditional investigation process while keeping numerical and safety logic deterministic.

### Prompt 16 — Bounded investigator agent and guardrails

```text
Implement the AgriKafka-Agent bounded alert investigator. Use `bounded-alert-investigator`, the approved Stage 5 agent/LLM ADR, and all safety rules.

The agent is invoked only after the deterministic risk engine emits a candidate alert. It must never consume every raw sensor reading.

Implement a narrowly scoped, auditable, read-only tool set:
- `get_sensor_health(field_id, time_range)`
- `get_field_history(field_id, time_range, variables)`
- `get_neighbouring_field_context(field_id, time_range)` only if valid comparable data exists
- `get_weather_observations(location, time_range)`
- `get_weather_forecast(location, horizon)`
- `get_crop_profile(field_id)`
- `calculate_crop_water_status(field_id, time_range)` as a deterministic tool
- `retrieve_agronomy_guidance(query, crop, region)`

Tool outputs must be typed, validated and auditable. The model cannot invent tool results or alter records. It cannot execute SQL directly, write to the database, publish arbitrary Kafka messages, send notifications, or actuate devices.

Investigation workflow:
1. Load candidate alert and validate required IDs.
2. Check source freshness, data quality and sensor health first.
3. If underlying data is faulty/stale, classify as a sensor/data issue and do not issue crop-water advice from those readings.
4. If data is trustworthy, inspect field history, crop profile and relevant weather context.
5. Use deterministic water-status calculations where supported.
6. Retrieve agronomy guidance only where needed.
7. If evidence conflicts or is incomplete, conditionally fetch additional allowed context or abstain.
8. Produce a structured investigation report with conclusion, evidence IDs, source citations, uncertainty, limitations, and suggested next step for human review.

Hard limits:
- maximum tool-call count and maximum investigation steps;
- per-tool timeout and overall deadline;
- bounded retries;
- LLM timeout and rule-based fallback;
- structured output schema validation;
- citation ID validation against retrieved results;
- no unsupported disease diagnosis or pesticide/chemical dosage;
- no physical actuation or autonomous approval;
- no recommendations when source quality is inadequate.

Add deterministic guardrails outside the LLM for schema validation, citation validation, policy checks, confidence/abstention and alert deduplication. Log prompts/model version/configuration and tool inputs/outputs safely, without logging secrets or unnecessary personal data.

Create scenario tests proving that:
- faulty sensor -> sensor issue, no irrigation advice;
- valid dry-down context -> evidence-gathering path;
- contradictory inputs -> more context or abstention;
- missing crop profile -> qualified response/abstention;
- no source citation -> reject recommendation;
- LLM timeout -> deterministic fallback;
- duplicate candidate alert -> no duplicate side effect.

Do not claim the agent is superior to a single LLM or rules baseline. That is tested in Stage 20. Finish with the standard completion report.
```

**Gate:** Tool calls are read-only, bounded and logged; guardrails operate outside the LLM; unsafe/incomplete evidence leads to abstention; all scenarios pass.

---

## Stage 17 — Backend API and application integration boundary

**Purpose:** Expose typed, authenticated application functions without letting the frontend access Kafka, database credentials, or the LLM directly.

### Prompt 17 — Backend API implementation

```text
Implement the backend API according to the approved Stage 5 ADR. FastAPI may be used only if selected in that ADR.

The API is the controlled boundary between the farmer PWA and backend services. The frontend must not connect directly to Kafka, TimescaleDB, Chroma or the LLM provider.

Design and implement versioned endpoints for:
- farm/field profile management;
- field current status and data freshness;
- time-series observations and trends;
- sensor-health status and history;
- alerts and alert evidence;
- investigator report and source citations;
- recommendation review/approve/reject/acknowledge;
- alert history;
- user feedback;
- service health/readiness for local operations.

Requirements:
1. Validate all request/response models.
2. Enforce authentication/authorization appropriate to the approved prototype scope.
3. Enforce field/user ownership boundaries; do not rely on frontend filtering.
4. Use pagination and bounded time windows.
5. Add idempotency keys for approval/feedback mutations.
6. Maintain an audit trail for human decisions.
7. Do not expose arbitrary SQL, filesystem, shell, Kafka administration or unrestricted agent tools.
8. Use structured errors and consistent status codes.
9. Add rate limits where appropriate.
10. Keep credentials in environment/secret configuration.
11. Use deterministic service layer boundaries and dependency injection for testability.
12. Return evidence/citation references that can be opened or inspected from the UI.

Create API contract documentation, OpenAPI output, unit tests, authorization tests, and integration tests against local services. Do not wire real notification delivery yet.

Finish with endpoint inventory, auth boundary, tests and the standard completion report.
```

**Gate:** API contracts and authorization are tested; frontend can retrieve real backend data without direct infrastructure access.

---

## Stage 18 — Build the farmer-facing mobile-first PWA

**Purpose:** Build the farmer experience as a separate, understandable application—not a Kafka/Spark monitoring screen.

### Prompt 18 — Farmer PWA implementation

```text
Build the AgriKafka-Agent farmer-facing responsive Progressive Web App using the approved frontend framework and UI decisions.

The target user is a farmer, not a data engineer. Do not expose Kafka topics, Spark batch IDs, consumer lag, stack traces or ML terminology in normal farmer workflows.

Core screens:
1. Sign-in/onboarding appropriate to the approved prototype.
2. Farm and field list.
3. Field profile setup: location, crop, variety, sowing date, growth stage, soil type, irrigation method, and sensor metadata/placement where known.
4. Field overview: latest conditions, source type, last updated time, data freshness and quality indicator.
5. Environmental trend view with clear units and time ranges.
6. Sensor health notice, with simple explanation when data are stale/unreliable.
7. Alert inbox and alert detail: what was observed, when, severity/category, evidence and why it matters.
8. Recommendation card with plain-language next step, supporting evidence, sources, uncertainty and limitations.
9. Human review controls: approve/accept, reject, acknowledge or request inspection, as appropriate to the API contract.
10. Alert and decision history.

UX rules:
- mobile-first and responsive;
- accessible contrast, typography, touch targets and keyboard/screen-reader semantics;
- low-bandwidth-friendly loading and clear empty/error/stale states;
- do not fabricate readings or demo values in production screens;
- visibly distinguish physical observations, external station context, modelled/reanalysis values, forecasts and derived indicators;
- show timestamps and units;
- explain uncertainty without technical jargon;
- no implication that an advisory is a guaranteed outcome;
- Kannada/English localisation should be designed for, even if only one language is implemented initially.

Use the backend API only. Do not embed service secrets or connect directly to databases/Kafka. Add component, route, accessibility and browser tests. Use Chrome DevTools/available browser testing only after checking the current marketplace and installing an extension/plugin only with approval.

Create a small set of realistic UI fixtures clearly marked as test data. Keep demo fixtures separate from real data. Capture screenshots of the running local PWA after successful tests.

Finish with route inventory, accessibility checks, test results and the standard completion report.
```

**Gate:** PWA works at mobile and desktop sizes; farmer workflows use real API contracts; demo fixtures are clearly separated; key accessibility checks pass.

---

## Stage 19 — Notifications, Telegram and human approval/feedback

**Purpose:** Add notification delivery without making Telegram the only interface or allowing notifications to trigger physical actions.

### Prompt 19 — Notification and feedback workflow

```text
Implement the notification and human feedback workflow. The PWA remains the primary farmer interface. Telegram may be included as an initial optional notification/approval channel if the team approves the bot setup.

Requirements:
1. Define which alert categories qualify for notification and how urgency is determined.
2. Use alert ID and recipient/channel as an idempotency key to prevent duplicate notifications.
3. Maintain notification attempts, delivery status, retry count and provider response without leaking tokens.
4. Implement bounded retries/backoff and a dead-letter/failure state for repeated delivery errors.
5. Include a concise alert summary and a deep link to the PWA alert detail where supported.
6. Include clear source/freshness caveats when relevant.
7. Approval/rejection/acknowledgement must be explicit human actions.
8. Record user, timestamp, decision and optional reason in an audit trail.
9. Treat duplicate or stale approval requests safely.
10. Notifications must never initiate irrigation, chemical application or other physical actions.
11. Do not include sensitive data or unsupported agronomic claims in messages.
12. Provide a local mock-notification provider for automated tests.

If Telegram is selected, ask for explicit approval before creating/configuring a bot or using any external messaging service. Store the token locally and never print it. Do not send a real notification during tests unless explicitly requested.

Add tests for duplicate suppression, retry limits, invalid/stale approval, rejected recommendation, notification outage and audit history. Update the farmer workflow documentation.

Finish with the standard completion report.
```

**Gate:** Notifications are optional and idempotent; human decisions are auditable; no notification path can cause physical actuation.

---

# Phase IV — Validation and delivery

## Stage 20 — Experimental evaluation: B1 vs B2 vs B3

**Purpose:** Test whether the agentic layer adds measurable value rather than assuming that more AI is better.

### Prompt 20 — Reproducible experimental harness

```text
Build the AgriKafka-Agent experimental evaluation harness. Use `agrikafka-evaluation-harness` and `testing-and-evaluation.md`.

Compare three variants on the same fixed scenario set:

B1 — Deterministic rules/statistical detection only.
B2 — Single LLM with preassembled context plus RAG; no conditional tool-selection loop.
B3 — Bounded tool-using investigator agent plus RAG and deterministic guardrails.

Use the same candidate alerts, evidence availability, knowledge corpus version, and evaluation labels for each variant. Keep prompts, models, temperatures, tool limits, thresholds and software versions recorded.

Create a scenario set with explicit labels for:
- genuine stress-like environmental scenarios;
- sensor faults;
- ordinary environmental variability/noise;
- stale/missing/contradictory evidence;
- natural flatlines;
- mixed source provenance;
- incomplete crop profiles;
- LLM/tool failure cases.

Synthetic/injected scenarios must be labelled as such. Do not claim that the existing Open-Meteo reanalysis dataset provides physical sensor ground truth or independently verified crop-damage labels. State what is simulated, derived, observed and manually labelled.

Measure as applicable:
- macro-F1 for `real_stress`, `sensor_fault`, `noise` where defensible labels exist;
- precision, recall and false-alert rate;
- false-alert reduction at comparable genuine-stress recall;
- evidence completeness;
- citation-grounding rate;
- unsupported/unsafe recommendation rate;
- abstention rate and correctness of abstentions;
- end-to-end and per-stage latency, including P50/P95/P99 where sample volume allows;
- LLM calls and tokens per alert;
- tool-call count, tool failure rate and timeout rate;
- fallback rate;
- cost per investigated alert if provider pricing is known and approved.

Use confidence intervals or repeated runs where appropriate. Do not compare results if the evaluation data or labels are not comparable. Report small sample limitations.

Implement a reproducible command that runs all variants on the same scenario manifest and writes machine-readable results plus a human-readable report under `docs/experiments/` or an approved results directory. Preserve run IDs and configuration snapshots.

Do not tune on the final test set. Separate development/calibration scenarios from held-out evaluation scenarios where dataset size permits. Do not invent results to fill missing metrics.

Finish with actual result tables/plots, methodology, threats to validity and the standard completion report.
```

**Gate:** All variants run on comparable scenarios; metrics are reproducible; ground-truth limitations and uncertainty are explicit; no claim of agent superiority without evidence.

---

## Stage 21 — Fault injection and reliability benchmarking

**Purpose:** Demonstrate safe operation, recovery and duplicate protection under component failures.

### Prompt 21 — Resilience profile, failure injection and recovery tests

```text
Implement the AgriKafka-Agent resilience test profile and fault-injection harness. Use `stream-resilience-benchmarking` and `data-resiliency-testing-and-failure-injection` where installed.

First inspect current Compose profiles and document the safe failure-test procedure. Never delete persistent volumes as part of a normal test. Run disruptive tests only in the dedicated local resilience profile and only after I approve the test plan.

Create a three-broker Kafka KRaft resilience profile if supported by the selected Kafka distribution and verified configuration. Configure replication factor/minimum in-sync replicas appropriate to the test. Do not claim high availability from a single-broker profile.

Test at least:
1. Kafka broker/container failure and recovery.
2. Producer retry during broker unavailability.
3. Consumer restart and offset recovery.
4. Spark process restart from persistent checkpoint.
5. Late and duplicate event delivery.
6. Database temporarily unavailable.
7. Ingestion source timeout/rate limit/outage.
8. LLM provider timeout/unavailability.
9. Investigator tool failure and bounded retry.
10. Notification provider failure and retry exhaustion.
11. DLQ routing, inspection and safe replay.
12. Duplicate alert and duplicate human-action request.
13. Backlog catch-up after downtime.

For every drill record:
- initial conditions and injected failure;
- commands/actions used;
- expected result;
- observed result;
- message loss, if any;
- duplicate messages/actions, if any;
- recovery time / MTTR;
- throughput and P99 latency where measurable;
- checkpoint/offset behaviour;
- residual data inconsistency or manual repair needed.

Build a replay procedure with safeguards: dry-run, explicit source range, run ID, idempotency, rate limits, and no uncontrolled notification resend. Replay must never bypass provenance.

Do not claim exactly-once end-to-end delivery. State the actual guarantees and residual duplicate/loss windows. Do not run production/cloud fault drills.

Create `docs/experiments/RESILIENCE_BENCHMARK.md` and an operator runbook. Finish with the standard completion report.
```

**Gate:** Failure drills are reproducible and isolated; recovery and duplicate behaviour are measured; DLQ/replay are safe; actual guarantees are accurately stated.

---

## Stage 22 — Final end-to-end integration, performance validation and demo handover

**Purpose:** Produce a reproducible local demonstration and a truthful technical handover for the course evaluation.

### Prompt 22 — Full-system verification and delivery candidate

```text
Perform the final AgriKafka-Agent end-to-end integration and release-candidate verification. Do not add new features unless needed to fix a demonstrated defect.

Verify the full path:
1. Live environmental source or approved live feed is ingested with correct source classification.
2. Historical Open-Meteo data can be replayed at configurable speed with provenance intact.
3. Injected scenarios are distinguishable from real observations.
4. Python producers publish canonical events to Kafka.
5. Spark validates, windows, deduplicates and writes checkpointed outputs.
6. Sensor-health service detects faults and avoids false fault labels for natural flatlines.
7. Deterministic risk engine emits explainable candidate alerts.
8. TimescaleDB persists observations, features, health, alerts and feedback idempotently.
9. Prometheus/Grafana expose operational status.
10. RAG retrieval returns verified documents and citations.
11. Bounded investigator checks sensor health first, conditionally gathers evidence, and abstains when evidence is insufficient.
12. Backend API authorises and exposes field/alert/evidence/feedback data.
13. Farmer PWA displays understandable conditions, freshness, alerts and recommendation evidence.
14. Human approval/rejection/acknowledgement is recorded and idempotent.
15. Optional Telegram notifications do not replace the PWA and do not trigger physical actuation.

Execute:
- unit tests;
- contract tests;
- integration tests;
- end-to-end scenario tests;
- frontend/browser tests;
- security and secret scans;
- dependency/version checks;
- database migration checks;
- resilience smoke tests;
- performance tests at documented, realistic local load levels.

For performance, report workload size, hardware, concurrency, duration, warm-up, versions and measurement method. Provide throughput and P50/P95/P99 latency where statistically meaningful. Do not compare results across different configurations without explaining the difference.

Verify:
- no committed secrets;
- no unnecessary host port exposure;
- no default admin credentials in deliverable configuration;
- no fabricated sensor values or agronomic citations;
- no LLM call per raw reading;
- no unsupported disease/pesticide guidance;
- no physical actuation route;
- no misleading exactly-once claim;
- no test-only mock data leaking into live screens.

Create/update:
- root README with installation, startup, demo, shutdown and troubleshooting steps;
- architecture overview and data-flow diagrams;
- component-level READMEs;
- environment/version lock documentation;
- `.env.example` files;
- operations runbook;
- data-source and provenance disclosures;
- experiment methodology and results;
- known limitations and future work;
- a 5–10 minute demo script with exact commands, expected screens and fallback plan;
- final `docs/development/RELEASE_CANDIDATE_REPORT.md`.

The release report must clearly separate implemented, tested, partially implemented and planned capabilities. Do not claim physical field deployment or agronomic validation unless evidence exists. Do not claim a live soil-moisture sensor if only modelled/reanalysis data is available.

Do not publish/deploy externally or incur paid service usage without explicit approval. Finish with the standard completion report and a final PASS/BLOCKED recommendation.
```

**Gate:** End-to-end workflow is reproducible locally; limitations and evidence are documented; release candidate is safe to demonstrate.

---

# After the core project works

These tasks are intentionally deferred. They are not prerequisites for the first working prototype.

## Optional Stage A — Add subsystem-specific MCP integrations

Give this prompt only after the corresponding local service is functioning.

```text
Review the current Google Antigravity MCP documentation and the official documentation for each proposed MCP server. Add MCP integrations progressively and with least privilege.

Candidates:
1. Context7 — first, for retrieving current library documentation.
2. Lenses MCP — only after our local Kafka cluster is operational; configure it against our actual local cluster, not a hosted demo cluster.
3. PostgreSQL MCP (`crystaldba/postgres-mcp`) — only after TimescaleDB is running; use the dedicated read-only database account.
4. Grafana MCP — only after Prometheus/Grafana is operating; use read-only permissions.
5. GitHub MCP — optional; begin read-only and enable only the specific repository toolsets required.
6. Open-Meteo MCP — optional IDE investigation tool only; it does not replace our independent Python-to-Kafka ingestion service.

For each MCP:
- verify current repository, official setup instructions, compatibility and license;
- inspect required tools and permissions;
- configure secrets via environment variables/secret storage, never committed JSON or plaintext files;
- restrict network endpoints to local/approved hosts;
- document which project task it assists;
- test a harmless read-only query;
- remove/disable it if it adds no clear value.

Do not install all MCPs at once. Do not provide a database write-capable MCP to the coding agent. Do not expose local Kafka/database/Grafana publicly. Report exact config paths, permissions, tested operations and unresolved risks.
```

## Optional Stage B — Install marketplace extensions/plugins only when useful

```text
Inspect the current Antigravity Marketplace/Customizations catalog and official plugin documentation. Do not assume a plugin name from the project handover is currently available.

Potential candidates:
- Chrome DevTools/browser debugging for PWA development;
- Modern Web Guidance for accessibility/performance/security guidance;
- Gemini API skills/plugin only if Gemini is selected as the deployed advisory model;
- Google Cloud plugin only if deployment to GCP is explicitly selected.

For each candidate, verify its publisher, exact name, current availability, permissions, cost implications, supported Antigravity version and concrete benefit to the current stage. Recommend only what is needed now. Ask before installing or enabling any extension that requests broad permissions or external access.
```

## Optional Stage C — Package AgriKafka DevKit

Do this after custom skills and rules have stabilised.

```text
Package the stable AgriKafka-Agent rules, eight custom skills, bounded investigator agent definition, verification prompts, and optional validation scripts as a private project plugin named `AgriKafka DevKit`.

Before implementation, read current official Antigravity plugin and build-plugin documentation. Verify CLI support and exact manifest format for the installed version. Do not rely on stale examples.

Requirements:
- include only stable project assets;
- preserve each skill's supporting references and scripts;
- document permissions and external dependencies;
- keep secrets and local MCP credentials out of the plugin;
- provide a minimal installation/update/uninstall guide;
- validate with the supported strict validator if available (for example, `agy plugin validate --strict` only if confirmed by the installed CLI help/docs);
- test plugin installation in a clean temporary workspace before using it in the main repository.

Do not block development on plugin packaging.
```

---

# Recovery prompts for common Antigravity failure modes

## Recovery 1 — Antigravity is making too many changes

```text
Stop implementation immediately. Do not make further edits. Summarise the current git diff, untracked files, commands run, and any running processes/containers. Compare the changes against the current stage's scope. Identify unrelated changes and propose the smallest safe rollback or correction. Do not revert user work or delete files without showing the exact paths and receiving approval. Wait for my decision.
```

## Recovery 2 — A stage fails its tests

```text
Do not continue to the next stage and do not weaken, delete, skip, or rewrite tests merely to get a green result. Reproduce the failure, identify the root cause, distinguish code defects from environment/configuration problems, and propose the smallest fix. Add a regression test where appropriate. Apply the fix only within the current stage scope, rerun the relevant test suite, and report the evidence. Keep the stage gate BLOCKED until the cause is resolved or I accept a clearly documented limitation.
```

## Recovery 3 — Antigravity wants to install or upgrade software

```text
Do not install or upgrade anything yet. Show the exact package/software, current and proposed versions, official source, compatibility reason, download size if known, system-wide versus workspace scope, permissions required, possible conflicts, rollback plan, and whether this introduces a paid service. Prefer a project-local environment. Wait for explicit approval.
```

## Recovery 4 — A live source stops responding

```text
Do not silently switch to a different source or replay data while labelling it live. Capture the failure status, last successful observation timestamp, error type, retry history and source documentation. Mark the source stale/unavailable. Preserve all existing records and provenance. Propose a fallback source and explain whether it is a physical observation, external station, model output, forecast, or historical replay. Wait for approval before changing the source configuration.
```

## Recovery 5 — The agent invents evidence or gives unsafe advice

```text
Treat this as a safety defect. Preserve the failed prompt, model output, tool trace, retrieved source IDs and input event. Do not patch the output text alone. Identify which deterministic guardrail failed or was missing. Add a regression scenario that reproduces the failure. Enforce schema/citation validation and abstention outside the LLM. Confirm that faulty/stale sensor data cannot generate irrigation advice and that no path can cause physical actuation. Keep the feature blocked until the regression test passes.
```

## Recovery 6 — The agent is overengineering or using too many frameworks

```text
Pause new dependencies and architecture expansion. List each framework/service/MCP/plugin currently proposed, the specific requirement it satisfies, its operational cost, and whether an existing component can already meet that requirement. Recommend the smallest architecture that satisfies the approved project brief and experiments. Do not add multi-agent orchestration, another database, another message broker, or an additional frontend framework without a demonstrated need and an ADR.
```

---

# Final stage tracker

Use this checklist to track the sequence. Mark a stage complete only after its gate passes.

- [ ] Stage 0 — Project context and operating contract
- [ ] Stage 1 — Environment audit
- [ ] Stage 2 — Repository skeleton
- [ ] Stage 3 — External skills audit and installation
- [ ] Stage 4 — Five rules and eight custom skills
- [ ] Stage 5 — Technology decisions and ADRs
- [ ] Stage 6 — Live data-source verification
- [ ] Stage 7 — Canonical event contracts
- [ ] Stage 8 — Kafka KRaft infrastructure
- [ ] Stage 9 — Live ingestion and historical replay
- [ ] Stage 10 — PySpark Structured Streaming
- [ ] Stage 11 — Data quality and sensor health
- [ ] Stage 12 — Crop-context-aware risk engine
- [ ] Stage 13 — TimescaleDB persistence
- [ ] Stage 14 — Prometheus and Grafana
- [ ] Stage 15 — Agronomy RAG knowledge base
- [ ] Stage 16 — Bounded Alert Investigator
- [ ] Stage 17 — Backend API
- [ ] Stage 18 — Farmer PWA
- [ ] Stage 19 — Notifications and feedback
- [ ] Stage 20 — B1/B2/B3 evaluation
- [ ] Stage 21 — Fault injection and resilience benchmark
- [ ] Stage 22 — End-to-end integration and demo handover
- [ ] Optional A — MCP integrations
- [ ] Optional B — Marketplace plugins/extensions
- [ ] Optional C — AgriKafka DevKit plugin packaging

---

# Reference links

These are starting points for Antigravity to re-check at execution time; documentation and repositories can change.

- [Google Antigravity — Agent Skills](https://antigravity.google/docs/skills)
- [Google Antigravity — MCP](https://antigravity.google/docs/mcp)
- [Google Antigravity — Plugins](https://antigravity.google/docs/plugins)
- [Google Antigravity — Build Plugins](https://antigravity.google/docs/build-plugins)
- [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills)
- [vaquarkhan/data-engineering-agent-skills](https://github.com/vaquarkhan/data-engineering-agent-skills)
- [lensesio/agentic-engineering-for-apache-kafka](https://github.com/lensesio/agentic-engineering-for-apache-kafka)
- [sickn33/agentic-awesome-skills](https://github.com/sickn33/agentic-awesome-skills)
- [Context7](https://context7.com/)
- [Lenses MCP](https://github.com/lensesio/lenses-mcp)
- [PostgreSQL MCP](https://github.com/crystaldba/postgres-mcp)
- [Grafana MCP](https://github.com/grafana/mcp-grafana)
- [GitHub MCP Server](https://github.com/github/github-mcp-server)
- [Open-Meteo](https://open-meteo.com/)
- [IMD API Portal](https://api.imd.gov.in/)
- [openSenseMap API documentation](https://docs.opensensemap.org/)

**Execution principle:** Build a small, correct, observable end-to-end path first. Expand only when a stage has passed its verification gate and the next capability is justified by the project requirements.
