# Bounded Alert Investigator Agent

**Module:** `services/alert-investigator`  
**Purpose:** Bounded, read-only AI agent that investigates candidate alerts and produces evidence-grounded advisories.  
**Scheduled Stage:** Stage 16  

## Invariants & Guardrails
- **Selective Triggering:** Invoked ONLY for alerts that survive stream detection filters. Never called on raw sensor readings.
- **Read-Only Tools:** Has access to strictly read-only inspection tools:
  - `get_sensor_health()`
  - `get_field_history()`
  - `get_neighbouring_field_context()`
  - `get_weather_observations()`
  - `get_weather_forecast()`
  - `get_crop_profile()`
  - `calculate_crop_water_status()`
  - `retrieve_agronomy_guidance()`
- **Triage Classification:** Classifies alert as `real_stress`, `sensor_fault`, or `noise`.
- **Deterministic Guardrails:** Strict output schema validation, mandatory citation verification, and safety filter blocking autonomous actuation or chemical dosage advice.
