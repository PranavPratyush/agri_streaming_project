# AgriKafka-Agent — Development & Contribution Guide

**Project:** AgriKafka-Agent: Fault-Tolerant, Real-Time Agricultural Risk Monitoring and Decision Support  
**Course:** AI372IA — Stream Processing and Analytics  

---

## 1. Operating Rules & Stage Gates

Development proceeds strictly stage-by-stage following `AgriKafka-Agent_Antigravity_Development_Prompt_Playbook.md`.

1. **One Stage at a Time:** Never jump ahead or build components scheduled for later stages.
2. **Read-Before-Write:** Inspect repository state and relevant documentation prior to modifying files.
3. **Approval Gates:** Explicit approval is required for:
   - Installing software or system packages.
   - Starting containers or exposing ports.
   - Modifying or moving datasets.
   - Any destructive changes.
4. **Stage Gate Enforcement:** Each stage ends with a structured completion report and a gate outcome:
   - `PASS`: All criteria met, verified with evidence.
   - `PASS WITH EXPLICIT LIMITATIONS`: Minor non-blocking limitation accepted by the team.
   - `BLOCKED`: Critical failure or unresolved compatibility question.
5. **Audit Trail:** Every stage must append an entry to [`docs/development/BUILD_LOG.md`](docs/development/BUILD_LOG.md).

---

## 2. Core Architectural Invariants

Always preserve the following invariants:
- **Kafka is the Event Backbone:** All telemetry, detections, actions, feedback, and metrics flow through Kafka.
- **PySpark Structured Streaming:** Handles windowing, watermarking, stream-stream joins, and candidate detection.
- **Deterministic Services:** Sensor-health checks, physical limits, and agronomic risk math are deterministic code—not LLM inference.
- **Selective LLM Investigation:** The agent is only invoked for candidate alerts surviving windowed detection.
- **No LLM Call per Raw Reading:** Zero raw sensor readings trigger LLM inference directly.
- **UI Separation:** Farmer PWA is for field decisions and simple explanations; Grafana is for engineering telemetry and pipeline lag.
- **Human-in-the-Loop:** All advisories are pending recommendations until approved by the farmer. No autonomous physical actuation.
- **Empirical Claims:** Never claim end-to-end exactly-once semantics without test evidence.

---

## 3. Python Packaging Strategy (`uv`)

Following the Stage 1 environment audit:
- Host default Python is 3.13, while PySpark 3.5.3 requires Python 3.11/OpenJDK 17.
- We use **`uv`** (`uv 0.11.26`, pre-installed on the host) as the unified package and virtual environment manager.
- The existing `.venv` (Python 3.13) is preserved for Phase 1 EDA.
- Streaming and agent development uses a dedicated environment pinned to Python 3.11:
  ```bash
  uv venv --python 3.11 .venv-agri
  ```
- Modular packages under `packages/` are managed as workspace members in `pyproject.toml`.

---

## 4. Testing Hierarchy

Tests are categorized strictly by scope under `tests/`:
- `tests/unit/`: Fast, isolated tests for deterministic services, schemas, and math functions.
- `tests/contract/`: Event schema validation and Pydantic contract compliance.
- `tests/integration/`: Kafka producer/consumer flows and TimescaleDB read/write tests.
- `tests/scenarios/`: ~60 labeled fault and stress scenarios evaluating detector performance.
- `tests/resilience/`: Fault injection drills (broker kills, worker crashes, LLM timeouts, and recovery).

Run tests with:
```bash
pytest tests/unit
```
