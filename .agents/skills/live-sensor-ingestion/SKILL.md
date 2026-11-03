---
name: "live-sensor-ingestion"
description: "Guidelines and patterns for implementing reliable, rate-limited live telemetry connectors (openSenseMap, IMD, MQTT/HTTP webhooks) with timestamp normalisation, freshness checks, idempotency, and Kafka publishing."
---

# AgriKafka Skill: Live Sensor Ingestion

## Purpose
This skill provides the architectural pattern, error handling, rate-limiting, and serialization workflow for ingesting live physical sensor feeds and weather station observations into Kafka.

---

## When to Use
- Implementing or modifying live API connectors in `services/ingestion/` (e.g. openSenseMap poller or IMD fetcher).
- Setting up MQTT subscribers or HTTP webhook endpoints for farm gateways.
- Handling API connection failures, backoff retries, and rate-limit preservation.
- Partition keying and publishing to Kafka topic `sensor-readings` or `weather-data`.

## When NOT to Use
- Replaying historical Open-Meteo datasets (use `safe-backfill-and-replay-orchestration`).
- Performing in-stream windowed joins and aggregations (use PySpark stream processor).
- Evaluating sensor health anomalies (use `sensor-health-forensics`).

---

## Step-by-Step Procedure
1. **Source Discovery & Verification:** Inspect station metadata before polling (verify GPS coordinates, sensor model, measurement units, reporting frequency, and active timestamp).
2. **Rate-Limiting & Backoff:** Wrap external HTTP calls with bounded exponential backoff (`tenacity` or `urllib3` retry). Adhere strictly to provider rate limits (e.g. max 1 request per minute for openSenseMap/IMD).
3. **Payload Normalization:** Convert provider-specific response payloads into the canonical Pydantic model (`AgriKafkaCanonicalObservationEvent`).
4. **Timestamp & Freshness Assertion:**
   - Parse provider timestamp as `event_time` in UTC.
   - Record system time as `ingestion_time`.
   - Compute `freshness_latency = ingestion_time - event_time`.
   - If `freshness_latency > 3 * polling_interval`, tag record with `quality_flags.sensor_health_flag: STALE`.
5. **Idempotent Kafka Publishing:**
   - Key messages by `field_id` to guarantee per-field partition ordering.
   - Set producer configs: `acks=all`, `enable.idempotence=true`, `max.in.flight.requests.per.connection=5`.
   - Handle publish timeouts by writing unroutable payloads to dead-letter queue.

---

## Invariants & Failure Handling
- Never block the ingestion loop indefinitely on network timeouts (enforce 5-second socket timeout).
- Never publish data with missing timestamps or unknown units without fallback flags.
- Source provenance must explicitly state `source_type: physical_sensor` or `weather_station`—never conflate with reanalysis models.
