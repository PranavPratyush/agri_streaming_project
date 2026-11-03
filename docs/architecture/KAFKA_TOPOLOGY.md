# AgriKafka-Agent: Kafka KRaft Topology Specification

## 1. Executive Summary & Architecture Context

AgriKafka-Agent is a real-time agricultural risk monitoring and decision-support streaming system for smallholder finger millet (*Eleusine coracana*, Ragi) farmers in the red sandy loam soils of Karnataka (Kolar district). The event streaming backbone serves as the fault-tolerant, decoupled communication fabric interconnecting physical IoT gateways, IMD/openSenseMap weather sources, PySpark Structured Streaming engines, deterministic health/risk filters, LLM-based agricultural alert investigators, and the farmer progressive web app (PWA).

This document formalizes the **Stage 8 Kafka Topology**, implementing the approved architecture decisions from **ADR-0002** (Apache Kafka with KRaft consensus mode) and the canonical event contracts established in Stage 7 (`agri_contracts`).

---

## 2. Broker Architecture & Development Profile

### 2.1 Single-Broker KRaft Profile

In accordance with ADR-0002 and the Stage 8 requirements:
- **Distribution & Version:** Apache Kafka `3.8.0` official container image (`apache/kafka:3.8.0`).
- **Consensus Protocol:** Kafka Raft metadata mode (**KRaft**). ZooKeeper is strictly eliminated.
- **Node Role:** Combined broker and controller (`KAFKA_NODE_ID=1`, `KAFKA_PROCESS_ROLES=broker,controller`).
- **Cluster ID:** `4L622nShTUiT8YCdQ3vtwg` (static, deterministically initialized cluster UUID).
- **Log Segment Size:** `1073741824` bytes (1 GB).

### 2.2 Replication Factor & Single-Broker Reality Check

> [!WARNING]
> **Single-Broker Dev Profile Limitation:**
> All topics are configured with `replication_factor=1`. This configuration is chosen strictly to enable lightweight, resource-conscious development on local Windows/WSL2 workstations without running a heavy 3-broker cluster.
> 
> **Zero Hardware/Node Redundancy:** A replication factor of 1 provides zero data redundancy across brokers. If the single broker container or node crashes during an uncommitted disk write, log corruption or loss of in-flight records can occur.
> 
> True fault-tolerance, broker failover, `min.insync.replicas=2`, and partition leader re-election are validated in the dedicated **Stage 14: Multi-Broker Resilience Profile**.

---

## 3. Network Listeners & Security Isolation

To satisfy enterprise isolation principles and local development safety, internal Docker network traffic is separated from host loopback access:

| Listener Name | Protocol | Binding Address | Port | Intended Clients | Security & Exposure |
|---|---|---|---|---|---|
| `PLAINTEXT` | PLAINTEXT | `0.0.0.0` (internal network) | `29092` | Containerized services: Spark streaming jobs, ingestion gateways, API backend, Prom/Grafana exporters | Isolated to Docker bridge network `agrikafka-network` |
| `PLAINTEXT_HOST` | PLAINTEXT | `127.0.0.1` | `9092` | Host development tools, IDE debuggers, test runners (`uv run pytest`, `smoke_test.py`) | **Strictly bound to localhost loopback (`127.0.0.1:9092`)**. Never exposed to `0.0.0.0` or external LAN |
| `CONTROLLER` | PLAINTEXT | `0.0.0.0` (internal network) | `9093` | KRaft internal controller quorum communication | Internal broker/controller metadata listener |

### 3.1 Advertised Listeners Configuration

```properties
KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:29092,PLAINTEXT_HOST://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:29092,PLAINTEXT_HOST://127.0.0.1:9092
KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER
```

---

## 4. Persistent Storage Architecture

Kafka commit logs must survive container stopping, restart, rebuilding, and host reboots without data loss.

- **Named Docker Volume:** `kafka_dev_data` (mapped in root `docker-compose.yml` to internal path `/var/lib/kafka/data`).
- **Volume Policy:** Explicit named volume lifecycle. The volume is never tied to container ephemeral storage.
- **Safety Directive:** Project scripts (`manage.ps1`, `manage.sh`) execute clean `docker compose down` and explicitly prohibit `-v` (volume deletion) flags. Pruning or deleting Kafka data requires deliberate manual operator intervention.

---

## 5. Topic Naming Scheme Decision

### 5.1 Evaluated Alternatives

1. **Alternative A (Flat Snake Case):** `sensor_readings`, `weather_data`, `candidate_alerts`.
   - *Weakness:* High collision probability in shared multi-tenant Kafka clusters; lacks domain grouping.
2. **Alternative B (Deep Hierarchical Dot Notation):** `agri.raw.telemetry.observation.sensor.v1`.
   - *Weakness:* Overly verbose; difficult to scan in metrics; complicates JMX metric MBean names.
3. **Alternative C (Deliberate Domain-Slug Hierarchy - Selected):** `agri.<domain-slug>`.
   - *Strengths:* Standard prefix `agri.` cleanly isolates the project namespace. Uniform kebab-case slugs (`sensor-readings`, `weather-data`, `dead-letter-queue`) align with Prometheus exporter label conventions and PySpark regex pattern matching (`agri\..*`).

### 5.2 Naming Standard

All production and development topics follow the canonical pattern:
```
agri.<domain-entity-or-stream>
```
No un-prefixed or mixed-notation topics (e.g. `sensor-readings` vs `agri.raw`) are permitted.

---

## 6. Topic Topology Specifications

The following table details the 9 canonical Kafka topics implemented in `infra/kafka/init_topics.py`:

| # | Topic Name | Partitions | Replication Factor | Retention Period | Cleanup Policy | Key Strategy | Primary Contract / Payload | Architectural Rationale |
|---|---|:---:|:---:|:---:|:---:|:---:|---|---|
| 1 | `agri.sensor-readings` | 3 | 1 | 7 days (`604800000 ms`) | `delete` | `field_id` | `AgriObservationEvent` (physical IoT) | Causal ordering of IoT observations per field; 7-day retention allows stream replay during pipeline development. |
| 2 | `agri.weather-data` | 3 | 1 | 7 days (`604800000 ms`) | `delete` | `field_id` | `AgriObservationEvent` (external weather/IMD) | External weather observations (temp, RH, wind, solar, rainfall). Partitioned by field for temporal joining with soil metrics. |
| 3 | `agri.validated-observations` | 3 | 1 | 14 days (`1209600000 ms`) | `delete` | `field_id` | `AgriObservationEvent` (validated) | Cleaned, deduplicated, calibrated observations emitted by stream preprocessor. Primary input to feature store and risk models. |
| 4 | `agri.sensor-health-events` | 3 | 1 | 30 days (`2592000000 ms`) | `compact,delete` | `sensor_id` | `SensorHealthResultEvent` | Keyed by sensor to track current health status (HEALTHY, DEGRADED, DRIFTING, OFFLINE). Log compaction preserves latest health state. |
| 5 | `agri.candidate-alerts` | 3 | 1 | 30 days (`2592000000 ms`) | `delete` | `field_id` | `CandidateCropRiskEvent` | Evaluated risks (drought stress, blast disease, heat shock) emitted by deterministic rules engine before LLM invocation. |
| 6 | `agri.investigation-results` | 3 | 1 | 30 days (`2592000000 ms`) | `delete` | `alert_id` | `AlertInvestigationResultEvent` | Actionable farmer recommendations, agronomic rationales, and tool audit trails produced by bounded LLM investigator. |
| 7 | `agri.human-feedback` | 3 | 1 | 90 days (`7776000000 ms`) | `delete` | `alert_id` | `HumanFeedbackEvent` | Farmer/agronomist feedback (ACCEPT, REJECT, OVERRIDE, DEFER) for closing the human-in-the-loop governance cycle. |
| 8 | `agri.dead-letter-queue` | 3 | 1 | 30 days (`2592000000 ms`) | `delete` | `original_topic` or `event_id` | `DeadLetterRecord` | Malformed JSON, schema contract violations, or corrupt payloads. Preserves failure diagnostics without blocking pipelines. |
| 9 | `agri.operational-metrics` | 3 | 1 | 3 days (`259200000 ms`) | `delete` | `service_name` | Operational telemetry / lag / throughput | Internal microservice heartbeats, consumer lag checkpoints, and processing latency for Prometheus scraping. |

---

## 7. Partitioning & Keying Mechanics

### 7.1 Per-Field Causal Ordering

In precision agriculture, the temporal sequence of environmental readings for a specific field is critical. For example, soil moisture depletion must be processed in chronological order to compute soil moisture deficit rate ($\Delta \text{SM} / \Delta t$).

- By keying observation topics (`agri.sensor-readings`, `agri.weather-data`, `agri.validated-observations`) by `field_id` (e.g. `FIELD-KA-KOLAR-001`), Kafka guarantees that all events for a given field are routed to the **same partition**.
- This guarantees **strict per-field causal ordering** while allowing parallel consumers to distribute the load across partitions 0, 1, and 2.

### 7.2 Per-Sensor Compaction

For `agri.sensor-health-events`:
- Key: `sensor_id` (e.g. `SENSOR-SM-001`).
- Cleanup Policy: `compact,delete`.
- Kafka's log cleaner retains the latest health status record for each sensor indefinitely (or until the 30-day deletion retention expires), allowing fast state reconstruction for newly started microservices without scanning historical logs.

### 7.3 Per-Alert Causal Chain

For `agri.candidate-alerts`, `agri.investigation-results`, and `agri.human-feedback`:
- Key: `alert_id` (UUIDv4).
- Ensures that the candidate risk, the AI investigation report, and the farmer's subsequent feedback record share the same partition key, enabling direct event-sourced tracing of an alert's complete lifecycle.

---

## 8. Topic Provisioning as Code

Topics are never provisioned through ad-hoc manual console commands. Provisioning is codified in Python using the official `confluent-kafka` AdminClient:

- **Source File:** [`infra/kafka/init_topics.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/infra/kafka/init_topics.py)
- **Execution:**
  ```powershell
  uv run python infra/kafka/init_topics.py --bootstrap-server 127.0.0.1:9092
  ```
- **Idempotency:** The script queries existing topics. If a topic already exists, it verifies partition count and retention parameters without recreating or corrupting existing partition logs.

---

## 9. Verification & Operational Testing

### 9.1 Health Check Probe

The Kafka container health check is configured directly in `docker-compose.yml`:
```yaml
healthcheck:
  test: ["CMD-SHELL", "/opt/kafka/bin/kafka-cluster.sh cluster-id --bootstrap-server localhost:9092 || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 20s
```

### 9.2 End-to-End Smoke Test

The smoke test validates producer publishing, topic routing, and consumer retrieval using an authentic `AgriObservationEvent`:
- **Source File:** [`infra/kafka/smoke_test.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/infra/kafka/smoke_test.py)
- **Execution:**
  ```powershell
  uv run python infra/kafka/smoke_test.py 127.0.0.1:9092
  ```

### 9.3 Persistence Verification Drill

The persistence test proves data survival across container restart:
1. Writes a uniquely tagged observation record to `agri.sensor-readings`.
2. Restarts the Kafka container via Docker API / CLI (`docker compose restart kafka`).
3. Waits for broker recovery and re-connects.
4. Consumes from beginning with a new consumer group and asserts that the unique marker record is recovered intact from disk.
- **Source File:** [`infra/kafka/verify_persistence.py`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/infra/kafka/verify_persistence.py)
- **Execution:**
  ```powershell
  uv run python infra/kafka/verify_persistence.py 127.0.0.1:9092
  ```

---

## 10. Operational Management Scripts

To guarantee safe operator usage, cross-platform scripts are provided in `infra/kafka/`:

- **Windows PowerShell:** [`infra/kafka/manage.ps1`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/infra/kafka/manage.ps1)
  - `.\infra\kafka\manage.ps1 start` — Starts Kafka container and waits for healthy status.
  - `.\infra\kafka\manage.ps1 init` — Idempotently provisions all 9 canonical topics.
  - `.\infra\kafka\manage.ps1 list` — Displays metadata and partition details for all topics.
  - `.\infra\kafka\manage.ps1 smoke` — Runs producer/consumer smoke test.
  - `.\infra\kafka\manage.ps1 persist` — Runs container restart persistence drill.
  - `.\infra\kafka\manage.ps1 stop` — Gracefully stops Kafka without deleting the data volume.
- **Linux/macOS Bash:** [`infra/kafka/manage.sh`](file:///c:/Users/prana/OneDrive/Desktop/spa_pbl/agri_streaming_project/infra/kafka/manage.sh)

---

## 11. Security & Secrets Management

- Zero plaintext credentials or tokens are stored in `docker-compose.yml` or topology scripts.
- Development access uses unauthenticated `PLAINTEXT` restricted to `127.0.0.1` and the internal Docker network.
- Environment variables and connection endpoints are loaded via safe template `.env.example`.
- Secrets for external cloud or weather APIs remain in local uncommitted `.env` files per `.agents/rules/security-and-secrets.md`.
