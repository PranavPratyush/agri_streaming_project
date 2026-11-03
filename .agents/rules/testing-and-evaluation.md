---
title: "Testing, Verification, and Evaluation Rigor"
description: "Rules mandating test coverage, reproducibility, separation of synthetic labels from field truth, prohibition of fabricated results, and evidence for streaming semantics."
always_apply: true
---

# Testing, Verification & Evaluation Rigor — AgriKafka-Agent

AgriKafka-Agent is a research-grade stream processing and decision-support project for course AI372IA. Academic and engineering credibility depends on rigorous, reproducible evaluation.

---

## 1. No Component Complete Without Tests
- No service, pipeline stage, or mathematical function is considered complete without accompanying automated tests in the appropriate `tests/` directory (`unit`, `contract`, `integration`, `scenarios`, `resilience`).
- A clean compilation or successful container startup does not constitute proof of correctness. Tests must assert behavioral outputs against expected baselines.

## 2. Experimental Reproducibility & Parameter Logging
- Every experimental benchmark run (detector comparison, agent triage, fault tolerance, scalability) must log its complete execution parameters:
  - Random seeds, sliding/tumbling window durations, detector thresholds ($\alpha, z, \text{contamination}$).
  - LLM model version, temperature, prompt template version, and timestamp.
  - Topic partition count, consumer group concurrency, and message batch sizes.
- Logs and raw test outputs must be saved to `docs/experiments/` before reporting summary tables in presentations or papers.

## 3. Strict Separation of Synthetic and In-Situ Ground Truth
- Clearly distinguish synthetic injected faults (stuck sensor, drift, spike) and injected stress events (drought dry-down, heatwave) from natural environmental fluctuations.
- Never claim an algorithm was tested on "real field crop failure" if the event was injected on top of gridded reanalysis weather data.

## 4. Absolute Prohibition Against Fabricating Results
- **NEVER invent or fabricate performance metrics, benchmark tables, F1 scores, latency figures, or citation rates.**
- If an experiment fails, crashes, or produces low scores (e.g. poor lag correlation between rain and soil moisture), report the actual empirical findings with an honest post-mortem analysis.

## 5. Scope Claims on Streaming Semantics
- **Never claim end-to-end "exactly-once" semantics without rigorous proof and scoped definitions.**
  - Kafka idempotent producers provide exactly-once delivery to a single topic partition.
  - Spark Structured Streaming provides at-least-once or effectively-once processing when coupled with idempotent downstream sinks and deterministic state checkpoints.
  - Downstream alerts and notifications must rely on alert-ID keyed deduplication rather than unverified global distributed transactions.
