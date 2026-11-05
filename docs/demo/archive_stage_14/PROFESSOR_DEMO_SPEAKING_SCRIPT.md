# Professor Demonstration Speaking Script
**Project:** AgriKafka-Agent (Autonomous Stream Analytics & Agronomic Risk Engine)  
**Crop / Variety:** Finger Millet (Eleusine coracana, Ragi GPU-28)  
**Location Context:** Kolar District, Karnataka, India (Red Sandy Loam Soil)  
**Duration:** 10–12 Minutes  

---

## Act 1: The Context & Agronomic Problem Statement (00:00 – 01:30)

### [What to Show on Screen]
Open your browser to `http://127.0.0.1:3001` (Grafana Dashboard: `01 - System Overview`) or display the architecture slide.

### [What to Say]
> "Respected Professors, welcome to the demonstration of **AgriKafka-Agent**.
>
> In precision agriculture, traditional batch analytics systems suffer from a high-latency blind spot. In semi-arid regions like Kolar, Karnataka, rainfed crops such as Finger Millet (Ragi GPU-28) face critical moisture stress windows during flowering and grain-filling stages. If soil-moisture depletion or acute vapor-pressure deficit isn't identified within hours, yield penalties can exceed 35%.
>
> Traditional cloud polling architectures fail here because they batch updates every 6 to 24 hours and fail silently when physical IoT sensors encounter drift, calibration errors, or communication dropouts.
>
> AgriKafka-Agent solves this by combining **distributed stream processing via Kafka and PySpark Structured Streaming** with deterministic agronomic validation and sensor forensics. Today, we will demonstrate the entire live data pipeline—from physical hardware telemetry in Kolar to real-time stream aggregation, dead-letter routing, and hypertable analytics."

---

## Act 2: Infrastructure as Code & Topics (01:30 – 03:00)

### [What to Show on Screen]
Switch to **Terminal 1**. Run:
```powershell
docker exec agrikafka-broker-dev /opt/kafka/bin/kafka-topics.sh --bootstrap-server 127.0.0.1:9092 --list
```

### [What to Say]
> "Here in Terminal 1, you can see our local cluster running **Apache Kafka 3.8 in KRaft mode**. We eliminated ZooKeeper entirely, reducing architectural complexity and failover latency.
>
> Notice our 9 canonical topics. We do not create topics dynamically or ad-hoc. All topics are provisioned as code with explicit partitioning:
> 1. `agri.sensor-readings`: High-throughput raw ingest partitioned across 3 partitions.
> 2. `agri.validated-observations`: Output of our PySpark validation engine.
> 3. `agri.dead-letter-queue`: Quarantined invalid records with full diagnostic error metadata.
> 4. `agri.candidate-alerts` & `agri.sensor-health-events`: Agronomic risk triggers.
>
> Critically, all raw sensor messages are partitioned using the composite key `field_id:observed_variable`. This guarantees that all chronological readings for any single physical sensor land on the exact same partition in strict temporal order."

---

## Act 3: Live Telemetry Ingestion (03:00 – 05:00)

### [What to Show on Screen]
Focus on **Terminal 3** (Kafka Console Consumer) and **Terminal 4** (Ingestion Runner).
In Terminal 4, run:
```powershell
python apps/ingestion-service/src/agri_ingestion/adapters/live_station.py
```

### [What to Say]
> "Now, we will pull live telemetry. Rather than relying on simulated mock data, our adapter connects to an active openSenseMap station—box ID `689b2bdc569c2d0007586ae9`, station name *Sarvamangalam* in Kolar district, Karnataka.
>
> In Terminal 4, the adapter has polled the HTTP API, extracted 5 physical sensor readings—Temperature, Relative Humidity, Precipitation, Wind Speed, and Barometric Pressure—and performed SI unit normalization.
>
> Look at Terminal 3: the messages have arrived on Kafka in real-time. Notice the dual timestamps:
> - `event_time`: The physical moment the sensor sampled the environment in Kolar.
> - `ingestion_time`: When our gateway accepted the packet.
>
> This separation is fundamental to handling clock skew and network backpressure."

---

## Act 4: PySpark Structured Streaming & Watermarking (05:00 – 07:00)

### [What to Show on Screen]
Switch to **Terminal 2** (`docker logs -f agrikafka-stream-processor`).

### [What to Say]
> "In Terminal 2, you are viewing the live logs of our containerized **PySpark Structured Streaming** engine.
>
> The streaming engine consumes micro-batches from `agri.sensor-readings`. Here is how we enforce stream safety:
> 1. **Explicit Watermarking**: We enforce a 10-minute event-time watermark. Any observation older than 10 minutes past the watermark is dropped from sliding window aggregations to prevent unbounded state growth in the memory state store.
> 2. **Sliding Windows**: We compute 15-minute sliding metrics (mean, min, max, rate of change) with a 5-minute slide to feed the agronomic risk formulas.
> 3. **Fault-Tolerant Checkpointing**: All offsets and state stores are persisted to a durable Docker volume at `/opt/spark/checkpoints`, allowing deterministic crash recovery without data loss."

---

## Act 5: Fault Injection & Dead-Letter Queue (07:00 – 09:00)

### [What to Show on Screen]
In Terminal 4, run the fault injection script:
```powershell
python scripts/demo/inject_fault.py --scenario corrupt_payload
```

### [What to Say]
> "In real-world agricultural IoT, corrupt packets and malformed payloads are inevitable. A robust stream processor must never crash or silently drop records.
>
> We have just injected a corrupted payload containing a null numeric value and an invalid schema contract.
>
> Notice what happened:
> 1. In Terminal 2, PySpark caught the contract violation via our Pydantic validation layer.
> 2. The pipeline did **not** crash; the streaming query continued running.
> 3. The invalid record was routed immediately to `agri.dead-letter-queue`.
> 4. Attached to the DLQ message is the exact error classification: `StreamValidationError: Non-finite or null numeric value` along with the original raw payload.
> This allows operations engineers to inspect faulty sensor hardware without interrupting downstream decision-making."

---

## Act 6: TimescaleDB Hypertables & Analytical Persistence (09:00 – 10:30)

### [What to Show on Screen]
Switch to **Terminal 5** (psql session) and execute:
```sql
SELECT observed_variable, numeric_value, unit, event_time, source_provider 
FROM observations 
ORDER BY event_time DESC 
LIMIT 5;
```

### [What to Say]
> "Now let us inspect persistent storage in Terminal 5. We utilize **TimescaleDB** on PostgreSQL 16.
>
> The `observations` table is configured as a native hypertable partitioned along the `event_time` dimension into 1-day chunks.
>
> Every write is strictly idempotent via `ON CONFLICT (idempotency_key, event_time) DO NOTHING`. If a network retry occurs or an offset is replayed from Kafka, no duplicate observations are inserted.
>
> Furthermore, because TimescaleDB is standard PostgreSQL, we can perform SQL joins directly against field profiles, crop stages, and sensor calibration history without maintaining a separate data warehouse."

---

## Act 7: Operational Observability & Conclusion (10:30 – 12:00)

### [What to Show on Screen]
Open Grafana (`http://127.0.0.1:3001`) and switch between:
1. `03 - Spark Streaming & Checkpoint Health`
2. `05 - Data Quality & Sensor Health`

### [What to Say]
> "Finally, let us review our operations console in Grafana.
>
> Prometheus scrapes metrics every 15 seconds from our broker, Spark stream processor, and ingestion gateway. Here on the Spark dashboard, we can monitor micro-batch processing duration, input rows per second, and watermark progression.
>
> On the Data Quality dashboard, we monitor sensor health: out-of-bounds spikes, stuck values, and DLQ drop rates.
>
> To summarize: AgriKafka-Agent delivers an end-to-end, fault-tolerant stream processing architecture capable of turning raw physical IoT telemetry into verified agronomic insights in sub-second time.
>
> Thank you, Professors. We are now ready for your questions."

---

## Anticipated Professor Questions & Technical Answers (Defense Guide)

### Q1: "Why did you choose PySpark Structured Streaming instead of Apache Flink for this workload?"
**Answer:**  
> "While Apache Flink offers true event-by-event processing with sub-millisecond latency, our agricultural domain operates on sensor sampling cadences of 1 to 15 minutes. PySpark Structured Streaming's micro-batch model (configured with a 10–15 second trigger) provides latency well within our SLA while offering seamless integration with complex Python scientific libraries (such as FAO-56 Penman-Monteith evapotranspiration calculations and NumPy/Pydantic validation) which are native to agronomic research."

### Q2: "How do you prevent unbounded state memory growth in Spark when calculating sliding windows?"
**Answer:**  
> "We enforce an explicit event-time watermark using `withWatermark('event_time', '10 minutes')`. This instructs Spark's state store that any late-arriving event with a timestamp older than 10 minutes behind the current max event time can be safely discarded, allowing Spark to drop closed state slices from RocksDB/HDFS state store memory."

### Q3: "What prevents duplicate records from being written to the database during network reconnects?"
**Answer:**  
> "We implement end-to-end idempotency across two layers:
> 1. At the Kafka producer level, we enable `enable.idempotence=true`, which assigns a producer ID (PID) and sequence number to eliminate network duplicate batches.
> 2. At the database persistence sink, we calculate a deterministic SHA-256 `idempotency_key` based on `field_id`, `sensor_id`, `observed_variable`, and `event_time`. The SQL insert uses `ON CONFLICT (idempotency_key, event_time) DO NOTHING`."

