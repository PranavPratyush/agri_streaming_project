# Phase-I Dataset & EDA Fact-Check and Reproducibility Audit

**Audit Date:** 2026-10-05  
**Audited Target:** `EDA_REPORT.md` and Presentation Slide Blueprint  
**Source of Truth:** Files in `data/` and `eda_output/`  
**Overall Status:** **NEEDS CORRECTION** (Core distributions and dataset metrics confirmed; specific diurnal amplitudes, model attributions, and causal/extrapolated claims require correction).

---

## 1. Fact-Check Summary Table

| Claim | Current (Prior) Value | Verified Value | Status | Evidence File |
| :--- | :---: | :---: | :---: | :--- |
| **Row Count** | 175,200 | 175,200 | **PASS** | `data/open_meteo_karnataka_2024-10-05_to_2026-10-04.csv` |
| **Field Count** | 10 | 10 | **PASS** | `data/open_meteo_metadata.json` |
| **Rows per Field** | 17,520 | 17,520 (exactly equal for all 10 fields) | **PASS** | `data/open_meteo_karnataka_2024-10-05_to_2026-10-04.csv` |
| **Observation Window** | 2024-10-05 to 2026-10-04 | 2024-10-05 00:00:00 to 2026-10-04 23:00:00 | **PASS** | `data/open_meteo_metadata.json` |
| **Cadence / Sampling Interval** | 1-hour cadence | Exactly 1 hour (0 days 01:00:00 across all 175,190 consecutive step intervals) | **PASS** | `data/open_meteo_karnataka_2024-10-05_to_2026-10-04.csv` |
| **Data Source Attribution** | "ERA5 / ERA5-Land Reanalysis Backbone" | "Open-Meteo Historical Weather API" (ERA5/ERA5-Land is not reported in metadata) | **FAIL (CORRECTED)** | `data/open_meteo_metadata.json` |
| **Attribute Count** | 14 attributes | 14 total columns (7 analytical time-series variables + 7 structural/location metadata columns) | **CORRECTED** | `data/open_meteo_karnataka_2024-10-05_to_2026-10-04.csv` |
| **Total Missing Values** | 0 (0.00%) | 0 (0.00% across all 14 columns and all 10 fields) | **PASS** | `data/open_meteo_karnataka_2024-10-05_to_2026-10-04.csv` |
| **Duplicate Timestamps** | 0 | 0 `(field_id, timestamp)` duplicate tuples | **PASS** | `data/open_meteo_karnataka_2024-10-05_to_2026-10-04.csv` |
| **Gaps > 1 Hour** | 0 | 0 | **PASS** | `eda_output/gaps_over_1h.csv` |
| **RH Range** | 6.0% to 100.0% | Min: 6.0%, Max: 100.0%, 0 physical boundary violations | **PASS** | `eda_output/physical_plausibility.csv`, `eda_output/summary_statistics.csv` |
| **Soil Moisture Range** | 0.027 to 0.520 m³/m³ | Min: 0.027, Max: 0.520, 0 physical boundary violations | **PASS** | `eda_output/physical_plausibility.csv`, `eda_output/summary_statistics.csv` |
| **Precipitation Maximum** | 20.3 mm/h | Max: 20.30 mm/h, Min: 0.0 mm/h, 0 negative values | **PASS** | `eda_output/physical_plausibility.csv`, `eda_output/summary_statistics.csv` |
| **VPD Range** | 0.0 to 6.81 kPa | Min: 0.00 kPa, Max: 6.81 kPa, 0 negative values | **PASS** | `eda_output/physical_plausibility.csv`, `eda_output/summary_statistics.csv` |
| **Temperature Range** | 11.2°C to 41.2°C | Min: 11.20°C, Max: 41.20°C (Mean: 24.56°C, Median: 23.90°C) | **PASS** | `eda_output/summary_statistics.csv` |
| **Diurnal Temperature Trough** | ~20.0°C at 06:00 IST | 20.46°C at 05:00 IST (statewide mean); per-field troughs occur at 05:00 IST (9 fields) and 04:00 IST (Mysuru) | **CORRECTED** | `eda_output/diurnal_means.csv` |
| **Diurnal Temperature Peak** | ~30.5°C at 14:00–15:00 IST | 29.58°C at 14:00 IST (statewide mean); per-field peaks reach 27.29°C (Hassan) to 32.22°C (Ballari) at 13:00–14:00 IST | **CORRECTED** | `eda_output/diurnal_means.csv` |
| **Diurnal RH Maximum (Dawn)** | ~88% at dawn | 86.80% at 06:00 IST (statewide mean); per-field dawn peaks range from 74.17% (Kalaburagi) to 92.89% (Hassan) | **PASS (REFINED)** | `eda_output/diurnal_means.csv` |
| **Diurnal RH Minimum** | ~45% at 14:00 IST | 47.09% at 14:00 IST (statewide mean); per-field afternoon minimums range from 40.22% (Kalaburagi) to 52.85% (Hassan) | **PASS (REFINED)** | `eda_output/diurnal_means.csv` |
| **Soil Moisture Diurnal Amplitude** | "0.015 to 0.025 m³/m³ afternoon decrease" | 0.0030 m³/m³ statewide mean amplitude (min 0.2613 at 13:00 to max 0.2643 at 05:00); per-field range 0.00233 to 0.00613 m³/m³ | **FAIL (CORRECTED)** | `eda_output/diurnal_means.csv` |
| **ADF Test Statistic & p-value** | Statistic: -3.6943, p = 0.0042 | Statistic: -3.694319, p = 0.004194 (on KA_BALLARI daily mean soil moisture, N=730) | **PASS** | `eda_output/stationarity.txt` |
| **Stationarity Claim Scope** | "Series exhibits mean-reverting stationarity across 2-year cycle" | Qualified: ADF rejects unit-root null hypothesis ($p < 0.01$) specifically for the representative field daily mean soil moisture series | **CORRECTED** | `eda_output/stationarity.txt` |
| **VPD vs. RH Correlation** | -0.94 | -0.9393 (rounds to -0.94) | **PASS** | `eda_output/correlation_matrix.csv` |
| **VPD vs. Temp Correlation** | +0.87 | +0.8707 (rounds to +0.87) | **PASS** | `eda_output/correlation_matrix.csv` |
| **Rainfall Infiltration Lag Distribution** | Peak lag at 1h across 7/10 fields, 0–2h statewide | Peak cross-correlation at lag 1h (7 fields), lag 0h (2 fields: Mandya, Dharwad), lag 2h (1 field: Bengaluru) | **PASS** | `eda_output/rainfall_soil_moisture_lags.csv` |
| **Max Rainfall Lag Correlation** | r = 0.297 in Belagavi | r = 0.29667 (rounds to 0.297) at lag 1h in KA_BELAGAVI | **PASS** | `eda_output/rainfall_soil_moisture_lags.csv` |
| **Causal & Drainage Decay Claim** | "Rainfall causes moisture peak; 72-hour exponential drainage decay" | Statistical cross-correlation only; gradual correlation decay observed, no exponential mathematical model was fitted | **CORRECTED** | `eda_output/rainfall_soil_moisture_lags.csv` |
| **Temperature EWMA Anomaly Rate** | 0.000% | 0.0000% (0 of 175,200 excursions beyond 3σ residual) | **PASS** | `eda_output/natural_anomaly_rates.csv` |
| **Relative Humidity EWMA Anomaly Rate**| 0.037% | 0.0370% (65 of 175,200 excursions) | **PASS** | `eda_output/natural_anomaly_rates.csv` |
| **Soil Moisture EWMA Anomaly Rate** | 2.091% | 2.0908% (due to rapid step-up recharge events) | **PASS** | `eda_output/natural_anomaly_rates.csv` |
| **Precipitation EWMA Anomaly Rate** | 1.364% | 1.3636% (due to episodic rain bursts) | **PASS** | `eda_output/natural_anomaly_rates.csv` |
| **VPD EWMA Anomaly Rate** | 0.288% | 0.2882% | **PASS** | `eda_output/natural_anomaly_rates.csv` |
| **Temperature Max Flatline & 1h Jump** | Flatline $\le 7$ hours; Max jump 12.3°C | Flatlines range 4 to 7 hours; Max 1h jump ranges 7.9°C to 12.3°C across fields | **PASS** | `eda_output/repeated_value_health.csv` |
| **VPD Max Flatline & 1h Jump** | Flatline $\le 7$ hours; Max jump 3.87 kPa | Flatlines range 4 to 7 hours; Max 1h jump ranges 2.17 to 3.87 kPa across fields | **PASS** | `eda_output/repeated_value_health.csv` |
| **Precipitation Max Flatline** | Up to 2,107 hours | Min per field: 983h, Max: 2,107h (in Belagavi, reflecting dry season) | **PASS** | `eda_output/repeated_value_health.csv` |
| **Soil Moisture Max Flatline** | Up to 679 hours | Min per field: 149h, Max: 679h (in Bengaluru, prolonged dry spell) | **PASS** | `eda_output/repeated_value_health.csv` |
| **Nominal Replay Duration** | ~4.87 hours | 175,200 events / 10 events/sec = 17,520 seconds = 4.8667 hours ($\approx$ 4.87 hours) | **PASS** | `eda_output/streaming_readiness.txt` |
| **10× Replay Duration** | ~29 minutes | 175,200 events / 100 events/sec = 1,752 seconds = 29.2 minutes | **PASS** | `eda_output/streaming_readiness.txt` |
| **Streaming Window Recommendations** | "Proved optimal by EDA" | Proposed engineering window configurations motivated by EDA findings (not mathematical absolutes) | **CORRECTED** | `eda_output/streaming_readiness.txt` |

---

## 2. In-Depth Verification of Audit Requirements

### Item 1: Dataset Verification
- **Total Rows:** 175,200
- **Total Columns:** 14
- **Column Names:** `field_id`, `latitude_requested`, `longitude_requested`, `temperature_2m`, `relative_humidity_2m`, `dew_point_2m`, `precipitation`, `vapour_pressure_deficit`, `soil_moisture_0_to_7cm`, `wind_speed_10m`, `timestamp`, `latitude_grid`, `longitude_grid`, `elevation_m`
- **Unique Field IDs (10):** `KA_BALLARI`, `KA_BELAGAVI`, `KA_BENGALURU`, `KA_DHARWAD`, `KA_HASSAN`, `KA_KALABURAGI`, `KA_MANDYA`, `KA_MYSURU`, `KA_SHIVAMOGGA`, `KA_TUMAKURU`
- **Rows per Field:** Exactly 17,520 for each field
- **Timestamp Minimum:** `2024-10-05 00:00:00`
- **Timestamp Maximum:** `2026-10-04 23:00:00`
- **Timestamp Timezone:** `Asia/Kolkata` (UTC+05:30) per `open_meteo_metadata.json`
- **Sampling Cadence:** Uniform 1-hour interval (`0 days 01:00:00`), 0 gaps $>1$h across 175,190 consecutive step intervals.

### Item 2: Data Source Verification
- `data/open_meteo_metadata.json` explicitly states:
  - `"source": "Open-Meteo Historical Weather API"`
  - `"api": "https://archive-api.open-meteo.com/v1/archive"`
- The terms `ERA5`, `ERA5-Land`, or `ECMWF` **do not appear** in the metadata JSON or API call parameters.
- **Rule:** The source must be stated as **"Open-Meteo Historical Weather API"**. Claims attributing the underlying model to ERA5/ERA5-Land were unverified assumptions and have been removed.

### Item 3: Schema Classification
The dataset contains **14 total columns**, categorized into:
1. **Identifier (1):** `field_id`
2. **Temporal (1):** `timestamp`
3. **Spatial & Location Metadata (5):** `latitude_requested`, `longitude_requested`, `latitude_grid`, `longitude_grid`, `elevation_m`
4. **Meteorological Analytical Variables (6):** `temperature_2m`, `relative_humidity_2m`, `dew_point_2m`, `precipitation`, `vapour_pressure_deficit`, `wind_speed_10m`
5. **Agronomic/Soil Analytical Variable (1):** `soil_moisture_0_to_7cm`
- **Conclusion:** There are **7 core time-series analytical variables** and **7 structural/metadata attributes**.

### Item 4: Missingness & Quality Audit
- Total missing values: **0** across all 14 columns and 175,200 rows.
- Missing percentage per column: **0.000%**.
- Missing percentage per field: **0.000%**.
- Gaps $>1$ hour: **0**.
- Duplicate `(field_id, timestamp)` tuples: **0**.
- Verification: **PASS**.

### Item 5: Physical Plausibility Bounds
- `relative_humidity_2m`: Min = 6.0%, Max = 100.0%, 0 invalid (Boundary $[0, 100]\%$)
- `soil_moisture_0_to_7cm`: Min = 0.027 m³/m³, Max = 0.520 m³/m³, 0 invalid (Boundary $[0.0, 1.0]$)
- `precipitation`: Min = 0.0 mm, Max = 20.30 mm, 0 invalid (Boundary $\ge 0.0$)
- `vapour_pressure_deficit`: Min = 0.0 kPa, Max = 6.81 kPa, 0 invalid (Boundary $\ge 0.0$)
- `temperature_2m`: Min = 11.20°C, Max = 41.20°C
- `dew_point_2m`: Min = -8.50°C, Max = 25.80°C
- `wind_speed_10m`: Min = 0.0 km/h, Max = 43.80 km/h
- Verification: **PASS**.

### Item 6: Diurnal Dynamics Audit
- **Temperature:** Statewide hourly mean minimum is **20.46°C at 05:00 IST** (troughs occur at 05:00 IST for 9 fields, 04:00 IST in Mysuru). Statewide hourly mean maximum is **29.58°C at 14:00 IST** (afternoon peaks range from 27.29°C in Hassan to 32.22°C in Ballari).
- **Relative Humidity:** Statewide hourly mean maximum is **86.80% at 06:00 IST** (dawn peaks range from 74.17% in Kalaburagi to 92.89% in Hassan). Statewide hourly mean minimum is **47.09% at 14:00 IST** (afternoon minimums range from 40.22% in Kalaburagi to 52.85% in Hassan).
- **Soil Moisture Amplitude Correction:** In hourly diurnal averages, soil moisture ranges from a statewide mean minimum of $0.2613\text{ m}^3/\text{m}^3$ at 13:00 IST to a maximum of $0.2643\text{ m}^3/\text{m}^3$ at 05:00 IST. The true mean diurnal amplitude is subtle: **$0.0030\text{ m}^3/\text{m}^3$ statewide** ($0.0023$ to $0.0061\text{ m}^3/\text{m}^3$ across fields). The prior text claiming a decrease of "0.015 to 0.025 m³/m³" was inaccurate for average diurnal cycles and has been corrected.
- **Wording:** Replaced "exact mirror anti-phase" with "inverse diurnal oscillation ($r = -0.75$) with peak solar heating at 14:00 IST coinciding with relative humidity minimums".

### Item 7: Stationarity & Time-Series Modeling
- Variable tested: `soil_moisture_0_to_7cm` aggregated to daily means (`series_daily`, N = 730).
- Field tested: `KA_BALLARI`.
- ADF Test Statistic: `-3.694319`.
- ADF p-value: `0.004194` (Significant at $p < 0.01$, 1% critical value: `-3.4395`).
- STL Parameters: `period = 7` (weekly seasonal window on daily means), `robust = True`.
- **Wording Standard:** *"For the selected representative field (KA_BALLARI) and daily mean soil-moisture series, the ADF test rejected the unit-root null hypothesis ($p = 0.0042 < 0.01$)."*

### Item 8: Correlation Matrix
- `vapour_pressure_deficit` vs. `relative_humidity_2m`: **$-0.9393$** (reported as **$-0.94$**).
- `vapour_pressure_deficit` vs. `temperature_2m`: **$+0.8707$** (reported as **$+0.87$**).
- `temperature_2m` vs. `relative_humidity_2m`: **$-0.7468$** (reported as **$-0.75$**).
- `dew_point_2m` vs. `soil_moisture_0_to_7cm`: **$+0.5367$** (reported as **$+0.54$**).
- `relative_humidity_2m` vs. `soil_moisture_0_to_7cm`: **$+0.5034$** (reported as **$+0.50$**).
- Verification: **PASS**. All correlations reflect statistical associations, not established direct physical causality.

### Item 9: Rainfall $\rightarrow$ Soil Moisture Lag
- Analyzed cross-correlation of hourly series across lags $\tau \in [0, 72]\text{ hours}$.
- **Best Lag Distribution:**
  - **1 hour (7 fields):** Ballari ($r = 0.261$), Belagavi ($r = 0.297$), Hassan ($r = 0.257$), Kalaburagi ($r = 0.290$), Mysuru ($r = 0.264$), Shivamogga ($r = 0.265$), Tumakuru ($r = 0.264$).
  - **0 hours (2 fields):** Dharwad ($r = 0.266$), Mandya ($r = 0.257$).
  - **2 hours (1 field):** Bengaluru ($r = 0.268$).
- **Statewide Maximum:** KA_BELAGAVI at lag 1h ($r = 0.29667$).
- **Corrections Applied:**
  - Removed causal claims ("rainfall causes soil moisture to peak").
  - Removed unsubstantiated "exponential drainage decay" claims (no exponential decay equation was fitted).
  - Adopted verified phrasing: *"The strongest observed cross-correlation between hourly rainfall and topsoil moisture occurred at a lag of approximately 1 hour across 7 of 10 fields (and between 0 and 2 hours statewide), followed by a progressive decay in correlation across the 72-hour lag horizon."*

### Item 10: Natural Anomaly Baseline & Sensor Constancy
- **Mean EWMA Anomaly Rates ($>3\sigma_{\text{resid}}$, span=24h):**
  - `temperature_2m`: **0.0000%** (0 / 175,200)
  - `relative_humidity_2m`: **0.0370%** (65 / 175,200)
  - `vapour_pressure_deficit`: **0.2882%** (505 / 175,200)
  - `wind_speed_10m`: **0.4470%** (783 / 175,200)
  - `precipitation`: **1.3636%** (2,389 / 175,200)
  - `dew_point_2m`: **1.7865%** (3,130 / 175,200)
  - `soil_moisture_0_to_7cm`: **2.0908%** (3,663 / 175,200)
- **Sensor Constancy Range across Fields:**
  - `temperature_2m`: Longest identical run = 4–7 hours; Max 1h jump = 7.9°C to 12.3°C; 99.9th percentile jump = 5.2°C to 6.6°C; Flatlines $\ge 6\text{h}$ = 0 to 1 across 2 years.
  - `vapour_pressure_deficit`: Longest identical run = 4–7 hours; Max 1h jump = 2.17 to 3.87 kPa; Flatlines $\ge 6\text{h}$ = 0 to 2 across 2 years.
  - `soil_moisture_0_to_7cm`: Longest identical run = 149–679 hours; Flatlines $\ge 6\text{h}$ = 433 to 548 (natural dry-season plateau).
  - `precipitation`: Longest identical run = 983–2,107 hours; Flatlines $\ge 6\text{h}$ = 322 to 420 (natural prolonged zero-rain periods).
- **Methodological Distinction Enforced:**
  - *Observed Natural Baseline:* Temperature never naturally repeats for $\ge 8$ hours in 175,200 observations.
  - *Proposed Fault-Injection Parameter:* Repeated values exceeding 8 hours can be synthesized to model sensor freeze.
  - *Future Detection Threshold:* Downstream rule-based or streaming operators can flag runs $\ge 8$ hours as potential frozen sensor candidates.

### Item 11: Streaming Replay Ingestion Calculations
- Total payload: 175,200 events.
- Stream sources: 10 parallel fields.
- Production rate: 10 events / hour.
- **Nominal replay (1 source hour = 1 real second):**
  - Rate = 10 events / second.
  - Duration = $175,200 / 10 = 17,520\text{ seconds} = 292\text{ minutes} = 4.8667\text{ hours} \approx \mathbf{4.87\text{ hours}}$.
- **Accelerated replay ($10\times$, 1 source hour = 100 ms):**
  - Rate = 100 events / second.
  - Duration = $175,200 / 100 = 1,752\text{ seconds} = \mathbf{29.2\text{ minutes}}$.
- Verification: **PASS**.

### Item 12: Stream Windowing Recommendations
- Classified clearly as **proposed engineering design configurations** informed by EDA insights (rather than EDA "proof"):
  - **1-Hour Tumbling Window:** Aligned with native 1-hour sampling interval for schema validation and physical boundary checks.
  - **6-Hour Sliding Window:** Proposed for short-term rate-of-change and sudden desiccation / thermal shock detection.
  - **24-Hour Tumbling Window:** Aligned with the 24-hour diurnal cycle for daily cumulative precipitation ($P_{24h}$) and EWMA baseline updates.
  - **72-Hour Sliding Window:** Motivated by the 72-hour soil infiltration memory horizon for multi-day drought and cumulative moisture tracking.
