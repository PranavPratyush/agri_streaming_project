# AgriKafka Stream Processor Service

**Module:** `services/stream-processor`  
**Runtime:** Apache Spark Structured Streaming 3.5.3, Python 3.11, OpenJDK 17 (per ADR-0001)  
**Package:** `agri_stream_processor`

---

## 1. Overview & Architecture

The Stream Processor consumes raw agricultural observation telemetry (`agri.sensor-readings`) and numerical weather forecasts (`agri.weather-data`), enforces canonical contract validation, separates malformed payloads to the Dead-Letter Queue (`agri.dead-letter-queue`), and computes windowed aggregations and derived agronomic features (VPD, Leaf Wetness Proxy, Soil Moisture Deficit Rates) to publish onto `agri.validated-observations`.

### Core Architectural Guardrails
1. **No LLMs in the Streaming Loop:** LLM reasoning and alerts are strictly downstream in the agent layer (Stage 12). The streaming layer is purely deterministic, high-throughput feature engineering.
2. **Data Provenance Preservation:** Weather context streams are joined on `field_id` within a temporal window ($\pm 15$ min) for feature derivation, but never overwrite physical ground-truth sensor telemetry.
3. **Event-Time Processing & Watermarking:** Handled through an explicit 10-minute watermark (`withWatermark("event_time", "10 minutes")`), allowing late-arriving IoT packets while bounding RocksDB/filesystem state stores.
4. **State-Bounded Deduplication:** Deduplicated across network retries using the canonical `idempotency_key` and `event_time`.
5. **Durable Checkpointing:** Checkpoints are stored in persistent Docker volume `spark_checkpoints` (`/opt/spark/checkpoints`), surviving container rebuilds and worker restarts.

---

## 2. Directory Structure

```
services/stream-processor/
├── Dockerfile                  # Container definition using bitnami/spark:3.5.3 (Python 3.11 / OpenJDK 17)
├── pyproject.toml              # UV workspace project definition
├── README.md                   # This documentation
└── src/
    └── agri_stream_processor/
        ├── __init__.py         # Package export
        ├── app.py              # CLI and spark-submit entrypoint
        ├── config.py           # Typed configuration management
        ├── features.py         # Agronomic math (VPD, Dew Point, Leaf Wetness, Depletion)
        ├── metrics.py          # PySpark StreamingQueryListener for latency/throughput
        ├── pipeline.py         # Streaming pipeline builder & query runner
        ├── schemas.py          # PySpark StructType schemas matching canonical contracts
        └── validation.py       # Plausible range assertions and DLQ payload generation
```

---

## 3. Streaming Windows & Feature Formulations

### 3.1 Windowing Policy
- **Tumbling Window:** 5 minutes (`window(event_time, "5 minutes")`). Computes min, max, mean, count, and stddev per `field_id` and `variable`.
- **Sliding Window:** 30 minutes with 5-minute slide (`window(event_time, "30 minutes", "5 minutes")`). Detects medium-term stress trends.
- **Watermark:** 10 minutes (`"10 minutes"`). Late events arriving $> 10$ minutes behind the highest observed watermark are discarded to prevent state exhaustion.

### 3.2 Derived Agronomic Features
- **Vapor Pressure Deficit (VPD, in kPa):**
  $$e_s(T) = 0.61078 \times \exp\left(\frac{17.27 \times T}{T + 237.3}\right)$$
  $$VPD = \max\left(0.0, e_s(T) \times \left(1 - \frac{RH}{100}\right)\right)$$
- **Dew Point ($T_{\text{dew}}$, in °C):**
  Calculated using the Magnus-Tetens formula.
- **Leaf Wetness Proxy (Fraction 0.0 to 1.0):**
  Continuous index indicating conditions favorable for dew formation and blast fungal spore germination ($RH \ge 80\%$, $T - T_{\text{dew}} \le 2.0^\circ\text{C}$).
- **Soil Moisture Depletion Rate:**
  Calculates drying/wetting velocity ($\Delta SM / \Delta t$) across consecutive aggregation windows.

---

## 4. Execution & Usage

### 4.1 Dry-Run Configuration Audit (Host)
```bash
uv run python -m agri_stream_processor.app --mode dry-run
```

### 4.2 Local Streaming Execution (via Docker)
```bash
docker compose up -d kafka stream-processor
```

### 4.3 Direct spark-submit (Container or Linux Cluster)
```bash
spark-submit \
  --master local[*] \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3 \
  --conf spark.sql.session.timeZone=UTC \
  services/stream-processor/src/agri_stream_processor/app.py \
  --mode run \
  --bootstrap-servers kafka:29092 \
  --checkpoint-dir /opt/spark/checkpoints
```

---

## 5. Delivery Guarantees & Fault-Tolerance

- **Delivery Guarantee:** **At-least-once** with deterministic idempotency keys. End-to-end exactly-once is not claimed for external Kafka sinks without transactional two-phase commit, but consumer idempotency prevents duplicate state accumulation downstream.
- **Worker Crash Recovery:** When a Spark worker restarts, it recovers state offsets and running aggregates from `/opt/spark/checkpoints/query_validated_observations` and `/opt/spark/checkpoints/query_dead_letter_queue`.
