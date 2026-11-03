---
name: "stream-resilience-benchmarking"
description: "Procedures and chaos test protocols for benchmarking stream fault tolerance, Kafka broker failover, Spark checkpoint recovery, agent worker termination, dead-letter queue routing, MTTR, and duplicate-action elimination."
---

# AgriKafka Skill: Stream Resilience Benchmarking

## Purpose
This skill defines the chaos engineering protocols, failure recovery drills, and resilience metrics required to prove AgriKafka-Agent's fault-tolerance claims for the course demo and technical paper.

---

## When to Use
- Running chaos testing drills in `tests/resilience/`.
- Measuring Mean Time to Recovery (MTTR) under broker, worker, or API failures.
- Verifying dead-letter queue (DLQ) routing, poison-pill isolation, and replay safety.
- Benchmarking throughput (messages/sec) and P99 latency under varying partition topologies.

## When NOT to Use
- Running daily non-destructive local feature development.
- Single-broker development environments where killing a broker intentionally halts the entire stack.

---

## Chaos Injection Drills & Verification Protocols

### Drill 1: Kafka Broker Termination & KRaft Failover
- **Action:** In a 3-broker KRaft cluster, forcibly kill the active partition leader for topic `sensor-readings`:
  ```bash
  docker compose stop kafka-1
  ```
- **Verification Target:**
  - Cluster performs Raft leader election within $\le 5$ seconds.
  - Producers with `acks=all` experience bounded retry delay without dropping records.
  - End-to-end data loss: **0 messages**.

### Drill 2: PySpark Streaming Worker Crash & Checkpoint Recovery
- **Action:** Forcibly kill an active Spark streaming worker during active micro-batch execution:
  ```bash
  docker compose kill spark-worker-1
  ```
- **Verification Target:**
  - Spark driver detects worker failure and reschedules micro-batch partitions.
  - Streaming query resumes state from persistent RocksDB/HDFS checkpoint.
  - State aggregations (tumbling/sliding windows) suffer **0 duplicate counts** or state corruption.

### Drill 3: External LLM Outage & Fallback Path
- **Action:** Simulate LLM provider outage by pointing `GEMINI_API_KEY` to an unreachable port or disabling network routing.
- **Verification Target:**
  - Agent worker times out at 8 seconds.
  - Invokes deterministic rule-based fallback without crashing the consumer group.
  - Records advisory with status `FALLBACK_RULE_ENGINE`.
  - Alert delivered to farmer without pipeline stall.

### Drill 4: Poison Pill Routing to Dead-Letter Queue (DLQ)
- **Action:** Publish malformed, unparseable JSON binary to `sensor-readings`.
- **Verification Target:**
  - Consumer catches deserialization failure.
  - Routes corrupt message envelope with error stack trace to topic `dead-letter`.
  - Consumer offset advances normally without head-of-line blocking.

---

## Benchmark Metrics & Targets

| Metric | Target Value | Measurement Method |
|---|---|---|
| **Message Loss** | Exactly 0 messages | Offset delta count vs producer log |
| **Duplicate Actions** | Exactly 0 duplicate farmer alerts | Alert-ID deduplication keying in notification worker |
| **Broker Failover MTTR** | $< 5.0\text{ seconds}$ | Timestamp delta from leader kill to next committed offset |
| **Spark Checkpoint Recovery MTTR** | $< 15.0\text{ seconds}$ | Timestamp delta from worker crash to next successful batch |
| **Sustained Throughput** | $\ge 2,500\text{ msg/sec}$ | Kafka producer performance tool benchmark |
| **End-to-End P99 Latency** | $< 2.0\text{ seconds}$ (stream layer) | Event time to TimescaleDB commit time |
