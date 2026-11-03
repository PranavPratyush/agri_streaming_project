# ADR-0002: Kafka Broker Topology & Client Library Selection

- **Status:** Proposed (Pending User Approval)
- **Date:** 2026-11-01
- **Deciders:** Lead Engineer, Team (Aanish Khan, Daksh Chauhan, Pranav Pratyush)
- **Technical Domain:** Event Messaging Backbone, Cluster Topology, Python Client

---

## 1. Context & Problem Statement
Apache Kafka serves as the central event streaming backbone for AgriKafka-Agent. Course AI372IA requires a multi-broker fault-tolerance demonstration with partition rebalancing, while daily feature engineering on a developer laptop requires minimal resource consumption. Additionally, we need a high-performance Python client that supports partition keying, idempotent delivery, and consumer group rebalancing.

---

## 2. Options Considered

### Kafka Distribution & Image
- **Option 1: Official Apache Kafka KRaft (`apache/kafka:3.8.0`)**
  - Native Apache Kafka image; pure KRaft consensus (ZooKeeper-free); lightweight (~350 MB image); officially maintained by the Apache Kafka project.
- **Option 2: Confluent Community Platform (`confluentinc/cp-kafka:7.7.x`)**
  - Feature-rich, includes Confluent enterprise extras, but heavier image size (~1.2 GB) and slower startup.

### Cluster Topology Strategy
- **Option A: Static 3-Broker Cluster at all times**
  - Requires ~3 GB RAM continuously; slow local iteration during simple frontend/API debugging.
- **Option B: Dual-Profile Topology (`dev` vs `resilience`) (Recommended)**
  - `dev` profile: 1 KRaft broker (`localhost:9092`), single partition per topic, minimal memory footprint (~700 MB).
  - `resilience` profile: 3 KRaft brokers (`kafka-1:9092`, `kafka-2:9093`, `kafka-3:9094`), replication factor = 3, min in-sync replicas = 2, 3 partitions per topic for chaos drills.

### Python Client Library
- **Option X: `confluent-kafka` (librdkafka C-wrapper) (Recommended)**
  - Industry benchmark for throughput; true asynchronous librdkafka engine; full support for idempotent producers (`acks=all`), transaction states, and exact rebalance callbacks.
- **Option Y: `kafka-python-ng` (Pure Python)**
  - Easy pure Python install, but significantly lower throughput, lacks true librdkafka resilience under network partitions, and has community maintenance lag.
- **Option Z: `aiokafka` (Asyncio pure Python)**
  - Useful for FastAPI async endpoints, but less suitable for batch worker loops and PySpark integration.

---

## 3. Decision
1. **Distribution:** Standardize on official **`apache/kafka:3.8.0` in KRaft mode**.
2. **Topology Profiles:**
   - Default daily development: **`dev` profile** (1 broker, ports `9092/9093`).
   - Academic demonstration & chaos testing: **`resilience` profile** (3 KRaft brokers, replication factor 3).
3. **Client Library:** Standardize on **`confluent-kafka` $\ge 2.5.0$** for all Python producers and consumers, encapsulated in `packages/shared-python`.

---

## 4. Consequences

### Positive
- Zero ZooKeeper daemon overhead.
- Fast, low-memory local engineering in `dev` mode (~700 MB RAM).
- Full failover demonstration capability in `resilience` mode.
- High-throughput, battle-tested client with prebuilt Windows wheels.

### Negative
- Running the 3-broker `resilience` profile requires ~2.5–3.0 GB RAM.

### Neutral
- Docker Compose configuration must maintain two target compose profiles (`docker-compose.dev.yml` and `docker-compose.yml`).
