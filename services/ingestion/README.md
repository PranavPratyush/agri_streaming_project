# AgriKafka-Agent: Ingestion Service (`services/ingestion`)

## 1. Overview & Architecture

The **Ingestion Service** (`agri-ingestion`) is the multi-source telemetry intake layer for the AgriKafka-Agent platform. It standardizes disparate physical IoT observations, regional numerical weather forecasts, historical reanalysis archives, and synthetic evaluation scenarios into **Stage 7 Canonical Event Contracts** (`packages/event-contracts`) and publishes them to local Kafka topics with strict idempotency and partitioned ordering.

```
+----------------------------------------------------------------------------------------------------+
|                                    INGESTION ADAPTER LAYER                                         |
+--------------------+---------------------+----------------------+----------------------------------+
| 1. Live openSense  | 2. Open-Meteo       | 3. Historical Replay | 4. Injected Scenarios            |
|    Map Station     |    Context & Fcst   |    Open-Meteo 2-Yr   |    Harness (~60 Scenarios)       |
|  [PHYSICAL_SENSOR] | [MODELLED_REANALYSIS| [HISTORICAL_REPLAY]  |   [INJECTED_SCENARIO]            |
|                    |     / FORECAST]     |                      |   (is_synthetic: true)           |
+---------+----------+----------+----------+----------+-----------+----------------+-----------------+
          |                     |                     |                            |
          +---------------------+---------------------+----------------------------+
                                |
                                v
               +----------------------------------+
               | Canonical Pydantic v2 Contracts  |
               | - AgriObservationEvent           |
               | - WeatherContextEvent            |
               | - DeadLetterRecordEvent          |
               +----------------+-----------------+
                                |
                                v
               +----------------------------------+
               | AgriKafkaProducer (Idempotent)   |
               | - acks=all, enable.idempotence   |
               | - key: field_id (Causal Order)   |
               | - DLQ fallback on failure        |
               +----------------+-----------------+
                                |
             +------------------+------------------+
             |                                     |
             v                                     v
+-----------------------------+       +-----------------------------+
|    agri.sensor-readings     |       |      agri.weather-data      |
|    (Partitions = 3)         |       |      (Partitions = 3)       |
+-----------------------------+       +-----------------------------+
```

---

## 2. Ingestion Adapters

### Adapter 1: Live openSenseMap Physical Station (`OpenSenseMapAdapter`)
- **Target Topic:** `agri.sensor-readings` (Key: `field_id`)
- **Station ID:** `689b2bdc569c2d0007586ae9` (`Sarvamangalam`, Lat=11.995°N, Lon=79.804°E)
- **Fallback Station ID:** `68a93536e035980007f6036b` (`Aurovanam`)
- **Cadence & Limits:** Sub-minute cadence (~15–45s updates), rate limit ~1 req/sec. Open citizen science REST API (0 credentials, 0 cost).
- **Physical Variables:** Temperature (°C), Relative Humidity (%), Rainfall (mm), Wind Speed (m/s), Barometric Pressure (hPa).
- **Freshness Assertion:** Calculates `freshness_latency = ingestion_time - event_time`. If latency > 90s (3 × poll interval), tags record with `sensor_health_flag: DROPOUT` and `validation_status: STALE`.
- **Provenance:** `provenance_class: physical_sensor`, `is_synthetic: false`.

### Adapter 2: Open-Meteo Environmental Context (`OpenMeteoContextAdapter`)
- **Target Topic:** `agri.weather-data` (Key: `field_id`)
- **Coordinates:** Regional agro-climatic corridor for Kolar, Karnataka (`13.137°N, 78.129°E`, Elevation 822m).
- **Cadence & Limits:** 15-minute reanalysis updates; limit 10,000 calls/day (0 credentials, 0 cost).
- **Context Variables:** `temperature_2m_c`, `relative_humidity_2m_pct`, `dew_point_2m_c`, `precipitation_mm`, `wind_speed_10m_mps`, `solar_radiation_w_m2`, `reanalysis_soil_moisture_0_7cm`.
- **Data Provenance Invariant:** Open-Meteo topsoil moisture (0–7 cm) is derived from the ERA5-Land numerical model. It is **strictly labelled** with `provenance_class: modelled_reanalysis` (or `forecast` for future horizons) and **never conflated with in-situ field probes**.

### Adapter 3: Historical Dataset Replay (`HistoricalReplayAdapter`)
- **Target Topic:** `agri.sensor-readings` (Key: `field_id`)
- **Source File:** `data/open_meteo_karnataka_2024-10-05_to_2026-10-04.csv` (175,200 hourly rows across 10 Karnataka virtual fields).
- **Replay Features:**
  - **Speed Multiplier:** Configurable from `1.0x` (real-time 1hr wait per row) to `3600.0x` (1hr simulated per wall-clock second), or `0.0` (instant burst).
  - **Deterministic Ordering:** Pre-sorts rows by `[dt, field_id]` to guarantee causal temporal sequence.
  - **Range & Field Filtering:** Filter by `--fields KA_BENGALURU KA_BALLARI`, `--start-date`, and `--end-date`.
  - **Safe Resume Checkpoints:** Saves progress atomically to `.replay_checkpoint_<run_id>.json`. Restarting resumes from the exact next row without duplicate publishes.
  - **Provenance:** `provenance_class: historical_replay`, `is_synthetic: false`.

### Adapter 4: Deterministic Scenario Injection (`InjectedScenarioAdapter`)
- **Target Topic:** `agri.sensor-readings` (Key: `field_id`)
- **Benchmark Scenarios Supported:**
  - `sensor_stuck_value`: Constant flatline reading across days (`SensorHealthFlag.STUCK_VALUE`).
  - `sensor_spike_out_of_bounds`: Extreme physiological spike (`95.0 °C`, `SensorHealthFlag.OUT_OF_BOUNDS`).
  - `sensor_linear_drift`: Artificially ascending calibration drift (+0.02 m³/m³ per step, `SensorHealthFlag.DRIFT_ANOMALY`).
  - `sensor_intermittent_dropout`: Periodic dropouts to zero (`SensorHealthFlag.DROPOUT`).
  - `drought_drydown_ragi`: Severe soil moisture depletion below Permanent Wilting Point (<0.09 m³/m³).
  - `heat_shock_flowering`: Sustained air temperatures > 38.0 °C.
  - `fungal_blast_window`: High humidity (>90%) with warm temperatures (24 °C) triggering blast infection alerts.
  - `transient_natural_noise`: Micro-fluctuations within physiological thresholds.
- **Provenance Invariant:** Every record strictly carries `provenance_class: injected_scenario`, `is_synthetic: true`, and explicit `scenario_id`.

---

## 3. CLI Usage & Operations

The service provides a unified CLI entrypoint:

```powershell
# Show service status, broker endpoints, topic names, and source limits
uv run --no-sync python -m agri_ingestion.cli status

# 1. Poll live openSenseMap station once (dry-run preview)
uv run --no-sync python -m agri_ingestion.cli live-osm --once --dry-run

# 2. Continuous openSenseMap ingestion into Kafka (every 30 seconds)
uv run --no-sync python -m agri_ingestion.cli live-osm --interval 30.0

# 3. Poll Open-Meteo weather context once (dry-run preview)
uv run --no-sync python -m agri_ingestion.cli weather-context --once --dry-run

# 4. Replay historical dataset at 3600x speed for Kolar/Bengaluru
uv run --no-sync python -m agri_ingestion.cli replay --speed 3600 --fields KA_BENGALURU --max-rows 100

# 5. Inject drought dry-down benchmark scenario (10 hourly steps)
uv run --no-sync python -m agri_ingestion.cli inject --scenario drought_drydown_ragi --steps 10 --dry-run
```

---

## 4. Failure Handling, Retry & Dead-Letter Queue (DLQ)

- **Exponential Backoff with Jitter:** HTTP requests to public APIs use bounded exponential backoff (`max_retries=3`, initial backoff `1.0s`, max backoff `30.0s`, with full random jitter).
- **Socket Timeouts:** Enforces strict 5.0s connection and read timeouts; ingestion loops never block indefinitely.
- **Dead-Letter Routing:** Any malformed response, schema violation, or unrecoverable error wraps the original raw payload, exception class, and stack trace in a `DeadLetterRecordEvent` and publishes it to `agri.dead-letter-queue`.
- **Zero Secret Leakage:** HTTP request logs sanitize tokens and authentication headers.

---

## 5. Automated Tests

The ingestion service includes 18 unit tests and 3 integration tests:

```powershell
# Run ingestion adapter unit tests (mocked HTTP, zero network calls)
uv run --no-sync pytest tests/unit/test_ingestion_adapters.py

# Run Kafka integration tests (gracefully skips if local broker is offline)
uv run --no-sync pytest tests/integration/test_ingestion_kafka.py

# Run all test suites across the monorepo (37 passed)
uv run --no-sync pytest tests/unit/ tests/contract/ tests/integration/
```
