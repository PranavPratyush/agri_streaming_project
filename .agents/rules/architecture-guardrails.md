---
title: "Architecture Guardrails"
description: "Non-negotiable architectural boundaries: Kafka event backbone, PySpark streaming, deterministic triage, selective LLM invocation, UI separation, and no autonomous actuation."
always_apply: true
---

# Architecture Guardrails — AgriKafka-Agent

These architectural guardrails govern all design, code, review, and execution decisions in the AgriKafka-Agent repository. They are always active.

---

## 1. Kafka is the Event Backbone
- All data moving between ingestion, stream processing, deterministic risk detection, agent investigation, notification workers, and persistence must flow through partitioned Apache Kafka topics.
- Direct peer-to-peer HTTP or RPC connections between streaming pipeline stages are prohibited.
- Topics must be partitioned by `field_id` to maintain strict per-field causal event ordering within each partition.

## 2. PySpark Structured Streaming for High-Volume Processing
- High-frequency data handling, micro-batch windowing (5-minute tumbling, 30-minute sliding), event-time watermarking, and stream-stream joins (sensor telemetry ⨝ weather context) must be executed by PySpark Structured Streaming.
- Processing state must be backed by durable, persistent checkpoints for failure recovery.

## 3. Deterministic Services for Data Quality & Risk
- Data-quality validation, missingness detection, sensor-health forensics (stuck value, spike, drift, dropout), and agronomic risk math (e.g. FAO-56 Penman-Monteith, Crop Stress Index) are **deterministic services**.
- These calculations must be implemented as deterministic mathematical code (Python/PySpark/NumPy/SciPy)—**never** delegated to an LLM or probabilistic reasoning agent.

## 4. Selective LLM Investigation (Candidate Alerts Only)
- The LLM/AI investigator agent is invoked **only** for candidate alerts that survive windowed detection and deterministic filtering.
- **NEVER invoke an LLM for every raw sensor reading.** Calling an LLM on raw telemetry streams violates latency, cost, and architectural boundaries.

## 5. Strict Separation of User Interfaces
- **Farmer PWA:** Designed for field decisions, plain-language explanations, transparent evidence, Kannada/English language support, low bandwidth, and simple Approve/Reject actions. The farmer must never see Kafka offsets, Spark micro-batch stats, or anomaly mathematics.
- **Grafana Dashboard:** Reserved for engineering operations, infrastructure telemetry, broker health, consumer lag, detector diagnostic traces, and research benchmarks.

## 6. No Autonomous Physical Actuation
- AgriKafka-Agent is a **decision-support** system.
- The system must never directly control irrigation hardware, pump relays, or chemical application equipment.
- All recommendations require explicit human review and authorization before any action or feedback is recorded.
