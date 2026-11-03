---
name: "bounded-alert-investigator"
description: "Architecture and execution constraints for the bounded, read-only AI investigator agent: allowed tools, conditional investigation sequence, timeouts, token budgets, confidence scoring, and fallback policies."
---

# AgriKafka Skill: Bounded Alert Investigator Agent

## Purpose
This skill defines the operational boundaries, tool interfaces, decision trees, and safety rules for the AI investigator agent in `services/alert-investigator/`. The agent is bounded, inspectable, and strictly read-only.

---

## When to Use
- Implementing or modifying the alert investigation workflow in `services/alert-investigator/`.
- Adding or updating read-only inspection tools.
- Defining the agent's conditional investigation state graph.
- Managing LLM token budgets, invocation timeouts, and rule-based fallbacks.

## When NOT to Use
- Implementing streaming data pipelines (use `spark-and-distributed-processing`).
- Calculating mathematical crop stress indices (use `crop-risk-modelling`).
- Performing hardware actuation or direct database mutations.

---

## Allowed Read-Only Toolset
The agent is restricted to calling these deterministic tools and **no others**:

1. `get_sensor_health(field_id: str, sensor_id: str) -> dict`
   - Returns recent sensor status: `HEALTHY`, `STUCK`, `DRIFT`, `SPIKE`, `STALE`.
2. `get_field_history(field_id: str, hours: int = 48) -> list[dict]`
   - Returns time-series observations and trends for the field over the past 48 hours.
3. `get_neighbouring_field_context(field_id: str, radius_km: float = 25.0) -> dict`
   - Returns aggregated readings from adjacent fields to cross-verify micro-climatic patterns.
4. `get_weather_observations(field_id: str) -> dict`
   - Returns recent ground weather station observations (rainfall, humidity, wind).
5. `get_weather_forecast(field_id: str, days: int = 3) -> list[dict]`
   - Returns 3-day weather forecast (impending precipitation or severe heatwave).
6. `get_crop_profile(field_id: str) -> dict`
   - Returns crop name, variety, sowing date, current growth stage, soil type, and root depth.
7. `calculate_crop_water_status(field_id: str) -> dict`
   - Invokes the deterministic water-balance engine for current depletion percentage.
8. `retrieve_agronomy_guidance(query: str, crop: str) -> list[dict]`
   - Queries Chroma vector store for verified ICAR/FAO reference passages with citation IDs.

---

## Conditional Investigation Sequence

```text
[Candidate Alert Received from 'crop-alerts']
                  │
                  ▼
         Step 1: Check Sensor Health via get_sensor_health()
                  │
        ┌─────────┴─────────┐
        │                   │
   [FAULTY / STUCK]     [HEALTHY]
        │                   │
        ▼                   ▼
Classify as:         Step 2: Fetch Field History & Crop Profile
"sensor_fault"              │
(Do NOT advise       Step 3: Check Weather & Forecast
 irrigation!)               │
        │            Step 4: Check Neighboring Fields
        │                   │
        │            Step 5: Query Agronomy Guidance via RAG
        │                   │
        │                   ▼
        │            Step 6: Classify Alert:
        │                    - "real_stress" (High confidence)
        │                    - "noise" (Transient spike)
        │                    - "uncertain" (Conflicting evidence)
        │                   │
        └─────────┬─────────┘
                  │
                  ▼
        Step 7: Draft Structured JSON Output
                  │
                  ▼
   Deterministic Guardrail Validation (Citation & Safety Check)
                  │
                  ▼
        Publish to 'agent-actions'
```

---

## Budgets, Timeouts & Fallback Policy
- **Maximum Tool Calls:** Hard cap of 6 tool calls per alert.
- **Latency Budget:** Max 15 seconds end-to-end investigation time.
- **LLM Call Timeout:** 8 seconds per inference call.
- **Rule-Based Fallback:** If the LLM call times out, returns malformed JSON, or exceeds token budgets, the system immediately routes the alert to a deterministic fallback module:
  - Generates a pre-approved template alert with raw metrics.
  - Flags `investigation_status: FALLBACK_RULE_ENGINE`.
  - Increments fallback operational counter in Prometheus.
