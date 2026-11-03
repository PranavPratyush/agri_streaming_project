---
name: "agri-event-contracts"
description: "Governs canonical event schemas, UUIDv4 event IDs, unit standards, timestamps, source provenance, schema versioning, and compatibility validation across all AgriKafka-Agent Kafka topics."
---

# AgriKafka Skill: Event Contracts & Schema Governance

## Purpose
This skill establishes and validates canonical event contracts for all data flowing through AgriKafka-Agent's Kafka topics (`sensor-readings`, `weather-data`, `validated-observations`, `crop-alerts`, `agent-actions`, `feedback`).

---

## When to Use
- Designing or modifying Pydantic models in `packages/event-contracts`.
- Implementing serialization/deserialization logic in ingestion producers or PySpark streaming jobs.
- Adding new variables or provenance tags to the streaming pipeline.
- Writing contract compatibility tests in `tests/contract/`.

## When NOT to Use
- Writing business-level risk calculation algorithms (use `crop-risk-modelling`).
- Performing sensor health forensic checks (use `sensor-health-forensics`).
- Configuring Kafka broker hardware/infrastructure (use `kafka-topic-audit`).

---

## Step-by-Step Procedure
1. **Schema Definition:** Define models using Pydantic v2 in `packages/event-contracts`. Every event must inherit from the base contract.
2. **Metadata Enforcement:** Ensure every event carries `event_id`, `source`, `source_type`, `event_time`, `ingestion_time`, `field_id`, `sensor_id`, `units`, and `provenance`.
3. **Provenance Validation:** Map the `source_type` strictly to the 8 allowed provenance types (`physical_sensor`, `weather_station`, `reanalysis_model`, `numerical_forecast`, `derived_calculation`, `historical_replay`, `injected_fault`, `injected_stress`).
4. **Unit Normalization:** Ensure variables adhere to standardized SI units:
   - Temperature: `celsius`
   - Relative Humidity: `percent` (0.0 to 100.0)
   - Precipitation: `mm_per_hour`
   - Vapour Pressure Deficit: `kpa`
   - Soil Moisture: `m3_per_m3` (volumetric fraction) or `fraction_0_to_1`
   - Wind Speed: `m_per_s`
5. **Schema Compatibility Assertion:** Execute contract tests verifying backwards compatibility:
   ```bash
   pytest tests/contract/test_event_contracts.py
   ```

---

## Invariants & Guardrails
- `event_id` must be a cryptographically random UUIDv4 string.
- `event_time` must be formatted in ISO-8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`).
- Non-breaking schema evolution only (new fields must have default values).
- Never serialize raw unvalidated JSON without Pydantic schema validation at ingestion boundaries.

---

## References & Examples
- Canonical JSON Schema: [`references/canonical_event_schema.json`](references/canonical_event_schema.json)
- Implementation package: `packages/event-contracts/`
