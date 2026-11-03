# ADR-0003: Event Serialization & Schema Governance

- **Status:** Proposed (Pending User Approval)
- **Date:** 2026-11-01
- **Deciders:** Lead Engineer, Team (Aanish Khan, Daksh Chauhan, Pranav Pratyush)
- **Technical Domain:** Data Contracts, Serialization Format, Schema Governance

---

## 1. Context & Problem Statement
Data flowing through AgriKafka-Agent's Kafka topics must be strongly typed, versioned, and validated to prevent poison pills from corrupting PySpark streaming jobs or agent workers. We need to choose between:
1. Strict JSON Schema validated via Pydantic v2.
2. Binary Apache Avro / Protobuf backed by an external Schema Registry (Confluent / Karapace).

---

## 2. Options Considered

### Option 1: Strict JSON Schema with Pydantic v2 (Recommended for V1)
- **Mechanism:** Events are serialized as UTF-8 JSON. Every producer and consumer validates payloads against strict Pydantic v2 models in `packages/event-contracts`.
- **Pros:**
  - Zero external container dependency (saves ~600 MB RAM and container startup latency).
  - Human-readable on standard Kafka CLI tools (`kafka-console-consumer`), web UIs, and Grafana.
  - Native integration with Python types, FastAPI, and PySpark `from_json(schema)`.
  - Non-breaking evolution enforced via Pydantic model defaults.
- **Cons:**
  - JSON payload size is larger than binary Avro/Protobuf (~30% overhead).

### Option 2: Apache Avro with Confluent Schema Registry
- **Mechanism:** Binary encoding with schemas registered in an HTTP Schema Registry.
- **Pros:**
  - Highly compact binary wire format.
  - Formal schema compatibility enforcement at broker ingress.
- **Cons:**
  - Requires deploying and maintaining an extra Schema Registry container.
  - Debugging requires specialized deserialization tooling.
  - Increases setup complexity for course evaluation.

---

## 3. Decision
Adopt **Option 1 (Strict JSON Schema via Pydantic v2)** for the initial prototype:
1. Models defined centrally in `packages/event-contracts`.
2. Producers validate before publishing; unparseable records are quarantined immediately.
3. PySpark Structured Streaming uses explicit Spark `StructType` schemas matching the Pydantic models.
4. Schema evolution follows strict non-breaking rules: new fields must have default values; existing fields may not be renamed or deleted.

---

## 4. Consequences

### Positive
- Streamlined local developer setup (no Schema Registry container needed).
- Effortless debugging on Kafka CLI and Grafana.
- Full type safety in Python.

### Negative
- Higher wire bandwidth compared to binary Avro (negligible for 10 virtual fields at 1-hour/1-second simulation cadences).

### Neutral
- If binary efficiency is required for future scalability benchmarks (1,000+ fields), an Avro serializer can be introduced under `packages/event-contracts` without changing business logic.
