# Verified Presentation Facts for Phase-I Evaluation

This document contains strictly audited, reproducible facts and statistics for the Phase-I presentation slides. Every numerical statement cites its direct evidence file.

---

## SLIDE 1 — DATASET ARCHITECTURE & INGESTION
- **Data Source:** Open-Meteo Historical Weather API (`https://archive-api.open-meteo.com/v1/archive`).
  - *Source file:* `data/open_meteo_metadata.json`
- **Total Rows / Observations:** Exactly **175,200 records**.
  - *Calculation:* 10 fields $\times$ 730 days $\times$ 24 hours = 175,200.
  - *Source file:* `data/open_meteo_karnataka_2024-10-05_to_2026-10-04.csv`
- **Field Locations:** Exactly **10 virtual field locations** in Karnataka:
  - `KA_BENGALURU` (12.9716°N, 77.5946°E, 910.0m)
  - `KA_MYSURU` (12.2958°N, 76.6394°E, 748.0m)
  - `KA_MANDYA` (12.5218°N, 76.8951°E, 677.0m)
  - `KA_TUMAKURU` (13.3392°N, 77.1130°E, 825.0m)
  - `KA_HASSAN` (13.0033°N, 76.1004°E, 948.0m)
  - `KA_SHIVAMOGGA` (13.9299°N, 75.5681°E, 588.0m)
  - `KA_BELAGAVI` (15.8497°N, 74.4977°E, 753.0m)
  - `KA_DHARWAD` (15.4589°N, 75.0078°E, 729.0m)
  - `KA_KALABURAGI` (17.3297°N, 76.8343°E, 461.0m)
  - `KA_BALLARI` (15.1394°N, 76.9214°E, 457.0m)
  - *Source file:* `data/open_meteo_metadata.json`
- **Records per Field:** Exactly **17,520 records per field** across all 10 locations.
  - *Source file:* `data/open_meteo_karnataka_2024-10-05_to_2026-10-04.csv`
- **Temporal Coverage:** 2 full years (730 days) from **2024-10-05 00:00:00 to 2026-10-04 23:00:00**.
  - *Source file:* `data/open_meteo_metadata.json`
- **Timezone:** `Asia/Kolkata` (UTC+05:30, `utc_offset_seconds: 19800`).
  - *Source file:* `data/open_meteo_metadata.json`
- **Schema Attributes:** Exactly **14 columns** total:
  - 1 Identifier: `field_id`
  - 1 Timestamp: `timestamp`
  - 5 Location Metadata: `latitude_requested`, `longitude_requested`, `latitude_grid`, `longitude_grid`, `elevation_m`
  - 6 Weather Variables: `temperature_2m` (°C), `relative_humidity_2m` (%), `dew_point_2m` (°C), `precipitation` (mm), `vapour_pressure_deficit` (kPa), `wind_speed_10m` (km/h)
  - 1 Soil Variable: `soil_moisture_0_to_7cm` ($\text{m}^3/\text{m}^3$)
  - *Analytical Time-Series Variables:* Exactly **7 variables**.
  - *Source file:* `data/open_meteo_karnataka_2024-10-05_to_2026-10-04.csv`

---

## SLIDE 2 — DATA QUALITY & PHYSICAL INTEGRITY
- **Missing Values:** Exactly **0 missing values** across all 14 columns (0.000%).
  - *Source file:* `data/open_meteo_karnataka_2024-10-05_to_2026-10-04.csv`
- **Sampling Cadence:** Strictly uniform **1-hour interval** (`0 days 01:00:00`) across all 175,190 consecutive step transitions.
  - *Source file:* `data/open_meteo_karnataka_2024-10-05_to_2026-10-04.csv`
- **Discontinuities / Gaps:** Exactly **0 gaps $> 1\text{ hour}$**.
  - *Source file:* `eda_output/gaps_over_1h.csv`
- **Duplicate Records:** Exactly **0 duplicate `(field_id, timestamp)` tuples**.
  - *Source file:* `data/open_meteo_karnataka_2024-10-05_to_2026-10-04.csv`
- **Physical Boundary Conformance (0 violations across all 175,200 rows):**
  - Relative Humidity $[0, 100]\%$: Min = **6.0%**, Max = **100.0%** (0 invalid, 0.00%).
  - Soil Moisture $[0.0, 1.0]\text{ m}^3/\text{m}^3$: Min = **0.027**, Max = **0.520** (0 invalid, 0.00%).
  - Precipitation $\ge 0.0\text{ mm}$: Min = **0.0 mm**, Max = **20.30 mm** (0 invalid, 0.00%).
  - VPD $\ge 0.0\text{ kPa}$: Min = **0.0 kPa**, Max = **6.81 kPa** (0 invalid, 0.00%).
  - Temperature: Min = **11.20°C**, Max = **41.20°C**, Mean = **24.56°C**, Median = **23.90°C**.
  - Dew Point: Min = **-8.50°C**, Max = **25.80°C**, Mean = **17.01°C**, Median = **18.80°C**.
  - Wind Speed $\ge 0.0\text{ km/h}$: Min = **0.0 km/h**, Max = **43.80 km/h**, Mean = **11.63 km/h**.
  - *Source files:* `eda_output/physical_plausibility.csv`, `eda_output/summary_statistics.csv`
- **Target Chart:** `eda_output/missingness_heatmap.png`.

---

## SLIDE 3 — TEMPORAL DYNAMICS & DIURNAL CYCLES
- **Temperature Diurnal Dynamics (Statewide Hourly Means):**
  - Mean trough: **20.46°C at 05:00 IST** (troughs occur at 05:00 IST in 9 fields and at 04:00 IST in Mysuru).
  - Mean peak: **29.58°C at 14:00 IST** (afternoon peaks range from 27.29°C in high-altitude Hassan to 32.22°C in northern Ballari).
  - *Source file:* `eda_output/diurnal_means.csv`
- **Relative Humidity Diurnal Dynamics (Statewide Hourly Means):**
  - Mean dawn peak: **86.80% at 06:00 IST** (peaks range from 74.17% in dry Kalaburagi to 92.89% in humid Hassan).
  - Mean afternoon minimum: **47.09% at 14:00 IST** (minimums range from 40.22% in Kalaburagi to 52.85% in Hassan).
  - *Source file:* `eda_output/diurnal_means.csv`
- **Topsoil Moisture Diurnal Respiration:**
  - Statewide mean diurnal amplitude: **0.0030 m³/m³** (mean minimum: 0.2613 at 13:00 IST, mean maximum: 0.2643 at 05:00 IST).
  - Per-field mean diurnal amplitudes range from **0.0023 m³/m³ (Ballari)** to **0.0061 m³/m³ (Bengaluru)**.
  - *Source file:* `eda_output/diurnal_means.csv`
- **Stationarity Testing (Augmented Dickey-Fuller):**
  - Evaluated on daily mean soil moisture for representative field `KA_BALLARI` (N = 730).
  - ADF Test Statistic: **-3.694319**.
  - p-value: **0.004194** ($p < 0.01$, critical 1% threshold: -3.4395).
  - *Technically verified statement:* For the selected representative field (KA_BALLARI) and daily mean soil-moisture series, the ADF test rejected the unit-root null hypothesis ($p = 0.0042$).
  - *Source file:* `eda_output/stationarity.txt`
- **STL Decomposition:**
  - Applied to daily mean soil moisture with weekly seasonal period (`period = 7`, `robust = True`).
  - Identifies distinct Kharif monsoonal recharge ($0.35\text{--}0.48\text{ m}^3/\text{m}^3$) versus dry summer desiccation ($0.08\text{--}0.16\text{ m}^3/\text{m}^3$).
  - *Source file:* `eda_output/stl_soil_moisture_representative_field.png`
- **Target Charts:** `eda_output/daily_cycle_combined.png`, `eda_output/stl_soil_moisture_representative_field.png`.

---

## SLIDE 4 — CROSS-VARIABLE RELATIONSHIPS & LAG
- **Pearson Correlation Coefficients (to 2 decimal places):**
  - VPD vs. Relative Humidity: **$r = -0.94$** (exact: -0.9393).
  - VPD vs. Temperature: **$r = +0.87$** (exact: +0.8707).
  - Temperature vs. Relative Humidity: **$r = -0.75$** (exact: -0.7468).
  - Dew Point vs. Soil Moisture: **$r = +0.54$** (exact: +0.5367).
  - Relative Humidity vs. Soil Moisture: **$r = +0.50$** (exact: +0.5034).
  - *Source file:* `eda_output/correlation_matrix.csv`
- **Rainfall-to-Topsoil Moisture Cross-Correlation Lag ($\tau \in [0, 72]\text{ hours}$):**
  - **Peak Cross-Correlation Lag Distribution:**
    - **1-hour lag across 7 of 10 fields:** KA_BALLARI ($r = 0.261$), KA_BELAGAVI ($r = 0.297$), KA_HASSAN ($r = 0.257$), KA_KALABURAGI ($r = 0.290$), KA_MYSURU ($r = 0.264$), KA_SHIVAMOGGA ($r = 0.265$), KA_TUMAKURU ($r = 0.264$).
    - **0-hour lag across 2 fields:** KA_DHARWAD ($r = 0.266$), KA_MANDYA ($r = 0.257$).
    - **2-hour lag across 1 field:** KA_BENGALURU ($r = 0.268$).
  - **Statewide Range:** Peak cross-correlation occurs within **0 to 2 hours** statewide.
  - **Highest Observed Cross-Correlation:** **$r = 0.297$ (0.29667) in KA_BELAGAVI at lag = 1 hour**.
  - *Technically verified statement:* The strongest observed cross-correlation between hourly rainfall and topsoil moisture occurs at a lag of approximately 1 hour across 7 of 10 fields (and between 0 and 2 hours statewide), followed by a progressive decay in correlation across the 72-hour lag horizon.
  - *Source file:* `eda_output/rainfall_soil_moisture_lags.csv`
- **Target Charts:** `eda_output/correlation_heatmap.png`, `eda_output/rainfall_to_moisture_lag.png`.

---

## SLIDE 5 — NATURAL ANOMALY BASELINE & SENSOR CONSTANCY
- **Natural EWMA Outlier Rates ($> 3\sigma_{\text{resid}}$, span = 24h, statewide mean):**
  - `temperature_2m`: **0.0000%** (0 out of 175,200).
  - `relative_humidity_2m`: **0.0370%** (65 out of 175,200).
  - `vapour_pressure_deficit`: **0.2882%** (505 out of 175,200).
  - `wind_speed_10m`: **0.4470%** (783 out of 175,200).
  - `precipitation`: **1.3636%** (2,389 out of 175,200).
  - `dew_point_2m`: **1.7865%** (3,130 out of 175,200).
  - `soil_moisture_0_to_7cm`: **2.0908%** (3,663 out of 175,200).
  - *Source file:* `eda_output/natural_anomaly_rates.csv`
- **Global Z-Score Outlier Rates ($|z| > 3$, statewide mean):**
  - `temperature_2m`: **0.1165%**
  - `precipitation`: **1.4760%**
  - `vapour_pressure_deficit`: **1.3099%**
  - `soil_moisture_0_to_7cm`: **0.0000%**
  - *Source file:* `eda_output/natural_anomaly_rates.csv`
- **Observed Signal Constancy & Repeated Values across Fields:**
  - `temperature_2m`: Longest identical run = **4 to 7 hours**; Max 1h step change = **7.9°C to 12.3°C**; Flatlines $\ge 6\text{h}$ = **0 to 1 occurrence in 2 years**.
  - `vapour_pressure_deficit`: Longest identical run = **4 to 7 hours**; Max 1h step change = **2.17 to 3.87 kPa**; Flatlines $\ge 6\text{h}$ = **0 to 2 occurrences in 2 years**.
  - `precipitation`: Longest identical run = **983 to 2,107 hours** (dry season zero plateaus); Flatlines $\ge 6\text{h}$ = 322 to 420.
  - `soil_moisture_0_to_7cm`: Longest identical run = **149 to 679 hours** (prolonged drought desiccation plateaus); Flatlines $\ge 6\text{h}$ = 433 to 548.
  - *Source file:* `eda_output/repeated_value_health.csv`
- **Methodology Distinction:**
  - *Natural Baseline:* Continuous atmospheric variables (temperature, VPD, wind) never flatline for $\ge 8$ hours naturally.
  - *Proposed Fault-Injection Parameter:* Constant temperature held $\ge 18$ hours represents an unambiguous artificial stuck-sensor fault.
  - *Future Detection Threshold:* Streaming rules must separate natural zero-rain and desiccation plateaus from sensor hardware freeze by multi-sensor cross-validation.
- **Target Chart:** `eda_output/natural_anomaly_example.png`.

---

## SLIDE 6 — STREAMING REPLAY & WINDOWING READINESS
- **Replay Ingestion Calculations:**
  - Total records: **175,200 events**.
  - Partitions: **10 parallel field streams** (keyed by `field_id`).
  - Nominal replay (1 source hour = 1 real second): **10 events / second**.
  - Nominal run duration: $175,200 / 10 = 17,520\text{ seconds} = \mathbf{4.87\text{ hours}}$ (292 minutes).
  - Accelerated replay ($10\times$, 1 source hour = 100 ms): **100 events / second** ($1,752\text{ seconds} = \mathbf{29.2\text{ minutes}}$).
  - Accelerated replay ($60\times$, 1 source min = 1 sec): **600 events / second** ($292\text{ seconds} \approx \mathbf{4.87\text{ minutes}}$).
  - *Source file:* `eda_output/streaming_readiness.txt`
- **Proposed Stream Windowing Topology (Engineering Recommendations):**
  - **Tumbling 1-Hour Window:** Schema parsing, physical limit verification ($0 \le RH \le 100$), watermark alignment.
  - **Sliding 6-Hour Window (slide = 1h):** Rapid rate-of-change and sudden environmental shock detection.
  - **Tumbling 24-Hour Window:** Diurnal minimum/maximum temperature capture, daily cumulative rainfall ($P_{24h}$), EWMA reference updates.
  - **Sliding 72-Hour Window (slide = 6h):** Antecedent rainfall-to-soil moisture memory tracking and persistent drought stress evaluation.
  - *Source file:* `eda_output/streaming_readiness.txt`
