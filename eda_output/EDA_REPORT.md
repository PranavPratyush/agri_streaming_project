# Smart Agriculture Crop Health Monitoring — Phase-I Dataset Acquisition & Baseline EDA Report

**Semester Project:** Stream Processing and Analytics  
**Component:** Phase-I Data Ingestion, Integrity Validation, and Baseline Characterization  
**Backbone:** Open-Meteo Historical Weather API (`https://archive-api.open-meteo.com/v1/archive`)  
**Target Region:** Karnataka, India (10 Virtual Field Locations)  
**Observation Window:** 2024-10-05 00:00:00 to 2026-10-04 23:00:00 (730 Days / 2 Full Agricultural Years)  

---

## 1. Dataset Overview

### 1.1 Ingestion Provenance & Methodology
The baseline streaming replay backbone was acquired directly from the Open-Meteo Historical Weather API. In accordance with strict project constraints, no synthetic data generator was used, no row counts were artificially synthesized, and no fault/stress models were injected into this raw baseline dataset.

The dataset models 10 representative agricultural clusters across Karnataka:
1. **KA_BENGALURU** (Lat: 12.9716, Lon: 77.5946, Grid Elevation: 910.0m)
2. **KA_MYSURU** (Lat: 12.2958, Lon: 76.6394, Grid Elevation: 748.0m)
3. **KA_MANDYA** (Lat: 12.5218, Lon: 76.8951, Grid Elevation: 677.0m)
4. **KA_TUMAKURU** (Lat: 13.3392, Lon: 77.1130, Grid Elevation: 825.0m)
5. **KA_HASSAN** (Lat: 13.0033, Lon: 76.1004, Grid Elevation: 948.0m)
6. **KA_SHIVAMOGGA** (Lat: 13.9299, Lon: 75.5681, Grid Elevation: 588.0m)
7. **KA_BELAGAVI** (Lat: 15.8497, Lon: 74.4977, Grid Elevation: 753.0m)
8. **KA_DHARWAD** (Lat: 15.4589, Lon: 75.0078, Grid Elevation: 729.0m)
9. **KA_KALABURAGI** (Lat: 17.3297, Lon: 76.8343, Grid Elevation: 461.0m)
10. **KA_BALLARI** (Lat: 15.1394, Lon: 76.9214, Grid Elevation: 457.0m)

### 1.2 Dimension & Schema Metrics
- **Total Record Count:** 175,200 rows ($10 \text{ fields} \times 730 \text{ days} \times 24 \text{ hours}$)
- **Per-Field Record Count:** Exactly 17,520 observations per virtual field
- **Total Attributes:** 14 columns (7 analytical time-series variables: 6 meteorological + 1 soil moisture; and 7 structural/location metadata columns)
- **Timezone:** `Asia/Kolkata` (UTC+05:30)

| Column Name | Schema Role | Native Type | Measurement Unit | Description / Role |
| :--- | :--- | :--- | :--- | :--- |
| `field_id` | Identifier | String / Object | N/A | Categorical identifier for the 10 virtual field locations |
| `timestamp` | Temporal | Datetime64 / String | ISO 8601 | Hourly observation timestamp for stream replay order |
| `latitude_requested` | Location Metadata | Float64 | Decimal Degrees | Field query latitude |
| `longitude_requested`| Location Metadata | Float64 | Decimal Degrees | Field query longitude |
| `latitude_grid` | Location Metadata | Float64 | Decimal Degrees | Grid-cell center latitude |
| `longitude_grid` | Location Metadata | Float64 | Decimal Degrees | Grid-cell center longitude |
| `elevation_m` | Location Metadata | Float64 | meters (m) | Terrain elevation of grid cell above sea level |
| `temperature_2m` | Weather Variable | Float64 | °C | Ambient 2-meter air temperature |
| `relative_humidity_2m`| Weather Variable | Int64 / Float64 | % | Relative humidity percentage (0–100%) |
| `dew_point_2m` | Weather Variable | Float64 | °C | 2-meter dew point temperature |
| `precipitation` | Weather Variable | Float64 | mm | Total liquid water equivalent per hour |
| `vapour_pressure_deficit`| Weather Variable| Float64 | kPa | Atmospheric evaporative demand (VPD) |
| `wind_speed_10m` | Weather Variable | Float64 | km/h | 10-meter horizontal wind velocity |
| `soil_moisture_0_to_7cm`| Soil Variable | Float64 | m³/m³ | Volumetric water content in topsoil layer (0–7 cm) |

*Note on exclusions:* Soil NPK, pH, and direct leaf wetness were intentionally excluded from the primary weather pipeline per project guidelines. Leaf wetness will be derived downstream as an explicit proxy from relative humidity and dew-point depression.

---

## 2. Data Quality & Integrity Validation

Comprehensive validation checks were conducted prior to exploratory statistical modeling:

```text
Missing Values across all 14 columns: 0 (0.000%)
Duplicate (field_id, timestamp) rows: 0
Sampling Interval Consistency: Exactly 1 hour (0 days 01:00:00) across 100% of observations
Discontinuities / Gaps > 1 Hour: 0
```

### 2.1 Physical Plausibility Audits
Boundary checks were applied against physical domain limits for agricultural and meteorological phenomena:

| Variable Check | Plausibility Boundary | Observed Range | Violations Detected | Violation Rate |
| :--- | :--- | :--- | :--- | :--- |
| `relative_humidity_2m` | $[0, 100]\,\%$ | $[6.0, 100.0]\,\%$ | 0 | 0.00% |
| `soil_moisture_0_to_7cm` | $[0.0, 1.0]\,\text{m}^3/\text{m}^3$ | $[0.027, 0.520]\,\text{m}^3/\text{m}^3$ | 0 | 0.00% |
| `precipitation` | $\ge 0.0\,\text{mm}$ | $[0.0, 20.30]\,\text{mm}$ | 0 | 0.00% |
| `vapour_pressure_deficit`| $\ge 0.0\,\text{kPa}$ | $[0.0, 6.81]\,\text{kPa}$ | 0 | 0.00% |
| `wind_speed_10m` | $\ge 0.0\,\text{km/h}$ | $[0.0, 43.80]\,\text{km/h}$ | 0 | 0.00% |
| `temperature_2m` | Terrestrial Limits | $[11.20, 41.20]\,^\circ\text{C}$ | 0 | 0.00% |
| `dew_point_2m` | Terrestrial Limits | $[-8.50, 25.80]\,^\circ\text{C}$ | 0 | 0.00% |

All observed variables adhere strictly to physical constraints. The dataset exhibits pristine structural continuity suitable for deterministic event-time streaming replay.

---

## 3. Distributional Findings

Summary statistics computed across the entire 175,200-sample dataset:

| Variable | Count | Mean | Std Dev | Min | 25% | Median | 75% | Max |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`temperature_2m` (°C)** | 175,200 | 24.56 | 4.43 | 11.20 | 21.40 | 23.90 | 27.40 | 41.20 |
| **`relative_humidity_2m` (%)** | 175,200 | 67.84 | 23.06 | 6.00 | 51.00 | 71.00 | 89.00 | 100.00 |
| **`dew_point_2m` (°C)** | 175,200 | 17.01 | 4.50 | -8.50 | 14.30 | 18.80 | 20.40 | 25.80 |
| **`precipitation` (mm)** | 175,200 | 0.110 | 0.532 | 0.00 | 0.00 | 0.00 | 0.00 | 20.30 |
| **`vapour_pressure_deficit` (kPa)** | 175,200 | 1.18 | 1.13 | 0.00 | 0.29 | 0.82 | 1.73 | 6.81 |
| **`soil_moisture_0_to_7cm` (m³/m³)**| 175,200 | 0.263 | 0.117 | 0.027 | 0.166 | 0.240 | 0.357 | 0.520 |
| **`wind_speed_10m` (km/h)** | 175,200 | 11.63 | 5.76 | 0.00 | 7.50 | 11.10 | 14.90 | 43.80 |

### Key Characteristic Insights:
- **Temperature:** Bounded between 11.20°C (winter minimums in high-elevation Hassan/Bengaluru) and 41.20°C (summer maximums in Kalaburagi/Ballari in northern dry zones). The interquartile range (IQR) spans 21.40°C to 27.40°C with a unimodal, slightly right-skewed profile.
- **Relative Humidity:** Shows high variance ($\sigma = 23.06\%$) reflecting Karnataka's distinct monsoonal wet versus post-monsoon dry seasons. Over 25% of readings exceed 89% humidity (frequent nighttime saturation during Kharif).
- **Precipitation:** Extremely zero-inflated (over 85% of hours have 0.0 mm). Peak hourly precipitation reached 20.30 mm during heavy convective monsoonal cloudbursts.
- **Soil Moisture:** Spans $0.027\,\text{m}^3/\text{m}^3$ (severe dry desiccation at wilting point in un-irrigated dry zones) to $0.520\,\text{m}^3/\text{m}^3$ (saturation capacity post-monsoon).
- **Vapour Pressure Deficit:** Spans 0.0 kPa (saturated conditions during fog/rain) to a peak of 6.81 kPa (extreme atmospheric evaporative thirst in Kalaburagi during April/May heatwaves).

---

## 4. Temporal Dynamics & Time-Series Structure

### 4.1 Diurnal Hourly Cycles (00:00–23:00 IST)
- **Temperature & Humidity Dynamics:** Consistent diurnal oscillation across all 10 virtual fields. Ambient temperature reaches its statewide hourly mean trough at **05:00 IST ($20.46^\circ\text{C}$)** (with 9 of 10 fields dipping at 05:00 IST and Mysuru at 04:00 IST), climbs after sunrise, peaks at **14:00 IST ($29.58^\circ\text{C}$ mean)** (ranging from $27.29^\circ\text{C}$ in Hassan to $32.22^\circ\text{C}$ in Ballari), and cools steadily overnight. Relative humidity exhibits an inverse diurnal pattern ($r = -0.75$), reaching its statewide hourly mean peak at **06:00 IST ($86.80\%$)** (ranging from $74.17\%$ in Kalaburagi to $92.89\%$ in Hassan) and dipping to its minimum at **14:00 IST ($47.09\%$)** (ranging from $40.22\%$ in Kalaburagi to $52.85\%$ in Hassan).
- **Topsoil Moisture Diurnal Cycle:** Soil moisture exhibits a subtle mean diurnal amplitude of **$0.0030\,\text{m}^3/\text{m}^3$** across all fields (statewide mean dipping from $0.2643\,\text{m}^3/\text{m}^3$ at 05:00 IST to $0.2613\,\text{m}^3/\text{m}^3$ at 13:00 IST, with per-field diurnal ranges between $0.0023$ and $0.0061\,\text{m}^3/\text{m}^3$).

### 4.2 Seasonality & STL Decomposition
STL decomposition ($period = 7\,\text{days}$, robust LOESS) on daily aggregated soil moisture reveals:
1. **Seasonal Component:** Governed by the South-West Monsoon (June–September) and North-East retreating monsoon (October–November). During July–October, soil moisture sustains levels of $0.35\text{--}0.48\,\text{m}^3/\text{m}^3$.
2. **Trend Component:** Shows gradual desiccation throughout the dry post-monsoon winter (December–February) and pre-monsoon summer (March–May), dropping to baseline residual levels ($0.08\text{--}0.16\,\text{m}^3/\text{m}^3$).
3. **Remainder / Residuals:** Small random shocks aligned with intermittent convective rainfall events.

### 4.3 Stationarity & Autocorrelation Testing
- **Augmented Dickey-Fuller (ADF) Test (Daily Mean Soil Moisture, Representative Field KA_BALLARI, N=730):**
  - ADF Test Statistic: $-3.694319$
  - p-value: $0.004194$ (Significant at $p < 0.01$, critical 1% value: $-3.4395$)
  - **Conclusion:** For the selected representative field (KA_BALLARI) and daily mean soil-moisture series, the ADF test rejected the unit-root null hypothesis ($p < 0.01$).
- **Autocorrelation Structure (ACF):**
  - **Soil Moisture:** High short-term inertia: $\text{lag}_{1h} = 0.9964$, $\text{lag}_{6h} = 0.9784$, $\text{lag}_{24h} = 0.9414$, and $\text{lag}_{72h} = 0.8423$. Even after 1 week (168 hours), soil moisture retains an autocorrelation of $0.6906$.
  - **Air Temperature:** Dominated by a strong 24-hour diurnal harmonic: $\text{lag}_{1h} = 0.9699$, $\text{lag}_{12h} = -0.0450$ (anti-correlated midday vs midnight), $\text{lag}_{24h} = 0.9645$, $\text{lag}_{48h} = 0.9499$, $\text{lag}_{72h} = 0.9386$, $\text{lag}_{168h} = 0.9104$.

---

## 5. Relationship & Cross-Variable Dynamics

### 5.1 Correlation Matrix
Pearson correlation coefficients ($r$) among core variables (rounded to 2 decimal places):

| Variable | `temp` | `RH` | `dew` | `precip` | `VPD` | `soil_m` | `wind` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `temperature_2m` | **1.00** | -0.75 | -0.20 | -0.04 | **0.87** | -0.17 | 0.07 |
| `relative_humidity_2m` | -0.75 | **1.00** | **0.76** | 0.15 | **-0.94** | **0.50** | 0.07 |
| `dew_point_2m` | -0.20 | **0.76** | **1.00** | 0.17 | -0.64 | **0.54** | 0.19 |
| `precipitation` | -0.04 | 0.15 | 0.17 | **1.00** | -0.12 | 0.23 | 0.09 |
| `vapour_pressure_deficit`| **0.87** | **-0.94** | -0.64 | -0.12 | **1.00** | -0.41 | -0.06 |
| `soil_moisture_0_to_7cm`| -0.17 | **0.50** | **0.54** | 0.23 | -0.41 | **1.00** | 0.30 |
| `wind_speed_10m` | 0.07 | 0.07 | 0.19 | 0.09 | -0.06 | 0.30 | **1.00** |

*Key Statistical Associations (non-causal):*
- **Strongest Inverse Association:** $\text{VPD}$ vs $\text{Relative Humidity}$ ($r = -0.94$).
- **Strongest Positive Association:** $\text{VPD}$ vs $\text{Temperature}$ ($r = +0.87$).
- Soil moisture associates positively with ambient dew point ($r = 0.54$) and relative humidity ($r = 0.50$), reflecting seasonal monsoon co-occurrence.

### 5.2 Rainfall-to-Soil-Moisture Cross-Correlation Lag Analysis
To evaluate topsoil wetting latency, cross-correlation between hourly precipitation (shifted by lag $\tau \in [0, 72]\,\text{hours}$) and topsoil moisture ($0\text{--}7\,\text{cm}$) was computed:

| Field ID | Peak Lag ($\tau^*$) | Peak Pearson $r$ | Description / Context |
| :--- | :--- | :--- | :--- |
| **KA_DHARWAD** | 0 hours | 0.2657 | Immediate surface wetting |
| **KA_MANDYA** | 0 hours | 0.2573 | Immediate surface wetting |
| **KA_BALLARI** | 1 hour | 0.2607 | Rapid infiltration in dry soil |
| **KA_BELAGAVI** | 1 hour | 0.2967 | Strongest observed coupling |
| **KA_HASSAN** | 1 hour | 0.2568 | Rapid porous percolation |
| **KA_KALABURAGI** | 1 hour | 0.2900 | High-contrast northern zone |
| **KA_MYSURU** | 1 hour | 0.2635 | Rapid surface absorption |
| **KA_SHIVAMOGGA** | 1 hour | 0.2655 | Fast saturated response |
| **KA_TUMAKURU** | 1 hour | 0.2642 | Rapid absorption |
| **KA_BENGALURU** | 2 hours | 0.2684 | Moderate runoff / slight delay |

**Finding Statement:**  
> *"The strongest observed cross-correlation between hourly rainfall and topsoil moisture occurs at a lag of approximately 1 hour across 7 of 10 fields (and between 0 and 2 hours statewide), peaking at $r = 0.297$ in Belagavi, followed by a progressive decay in correlation across the 72-hour lag horizon."*

### 5.3 Vapour Pressure Deficit (VPD) Dynamics
- **VPD vs Temperature:** Demonstrates an upward accelerating relationship. Below 20°C, VPD remains predominantly $< 1.0\,\text{kPa}$. Beyond 30°C, VPD accelerates toward $3.0\text{--}6.8\,\text{kPa}$.
- **VPD vs Soil Moisture:** Shows clustering into two agricultural regimes:
  1. *Moist/Low-Stress Regime:* Soil moisture $> 0.30\,\text{m}^3/\text{m}^3$, VPD $< 1.2\,\text{kPa}$ (favorable transpiration conditions).
  2. *Atmospheric/Hydrologic Stress Regime:* Soil moisture $< 0.15\,\text{m}^3/\text{m}^3$, VPD $> 2.5\,\text{kPa}$ (elevated evaporative demand coupled with depleted root-zone water).

---

## 6. Sensor-Health & Signal Constancy Analysis

To characterize natural signal stability across the uncorrupted baseline series, identical consecutive value runs, flatlines, and 1-hour step changes were audited:

| Variable | Longest Run Across Fields | Typical Median Run | Max 1-Hour Jump | 99.9th %ile 1-Hour Jump | Natural Flatlines $\ge 6\text{h}$ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `temperature_2m` | 4–7 hours | 2.0 hours | 7.9°C – 12.3°C | 5.2°C – 6.6°C | 0 to 1 occurrence in 2 years |
| `relative_humidity_2m`| 7–14 hours | 2.0 hours | 41.0% – 63.0% | 27.5% – 39.0% | 4 to 26 occurrences (night saturation) |
| `dew_point_2m` | 6–8 hours | 2.0 hours | 9.1°C – 19.7°C | 5.2°C – 9.8°C | 1 to 8 occurrences |
| `precipitation` | 983–2,107 hours | 3.0–4.0 hours | 10.1 mm – 20.2 mm | 6.0 mm – 8.2 mm | 322 to 420 prolonged dry blocks |
| `vapour_pressure_deficit`| 4–7 hours | 2.0 hours | 2.17 kPa – 3.87 kPa | 1.34 kPa – 2.50 kPa | 0 to 2 occurrences |
| `soil_moisture_0_to_7cm` | 149–679 hours | 3.0 hours | 0.137 – 0.276 m³/m³| 0.054 – 0.105 m³/m³ | 433 to 548 seasonal plateaus |
| `wind_speed_10m` | 3–4 hours | 2.0 hours | 16.4 – 28.6 km/h | 10.5 – 17.1 km/h | 0 occurrences |

### Physical Interpretation & Methodology Distinction:
- **Observed Natural Baseline:** Dynamic atmospheric parameters (`temperature_2m`, `wind_speed_10m`, `vapour_pressure_deficit`) never naturally flatline for $\ge 8$ hours in the 175,200-sample baseline. Conversely, `precipitation` naturally holds $0.0\,\text{mm}$ for weeks during dry seasons (up to 2,107 hours), and `soil_moisture` can plateau for extended durations (up to 679 hours) at residual dry levels.
- **Proposed Fault-Injection Parameters:** For stuck sensor simulations, holding temperature or VPD constant for $\ge 18$ hours represents an artificial fault clearly distinct from the natural 4–7 hour maximum.
- **Future Streaming Detection Thresholds:** Downstream streaming operators must avoid flagging dry-season zero-rain or desiccation plateaus as frozen sensors without cross-referencing multi-sensor state.

---

## 7. Natural Anomaly Baseline (Pre-Injection Characterization)

Before introducing artificial faults, natural anomaly rates were evaluated using two statistical baselines:
1. **Global Z-score ($|z| > 3$):** Values outside 3 standard deviations of the entire 2-year field distribution.
2. **Local EWMA Residual ($\text{span} = 24\,\text{hours}, |\text{residual}| > 3\sigma_{\text{resid}}$):** Values deviating abruptly from the 24-hour diurnal tracking baseline.

### Natural Anomaly Summary Rates (Mean Across 10 Fields):

| Variable | Natural Z-Score $> 3\sigma$ Rate (%) | Natural EWMA $> 3\sigma$ Rate (%) | Physical Interpretation |
| :--- | :--- | :--- | :--- |
| **`temperature_2m`** | 0.116% | **0.000%** | Diurnal tracking accommodates smooth temperature swings; no abrupt outliers. |
| **`relative_humidity_2m`** | 0.000% | 0.037% | Extreme monsoonal cold-front microbursts cause minor step changes. |
| **`dew_point_2m`** | 0.797% | 1.787% | Transient dry-line passages and localized storm fronts. |
| **`precipitation`** | **1.476%** | **1.364%** | Convective episodic rain bursts naturally exceed 3 standard deviations. |
| **`vapour_pressure_deficit`**| 1.310% | 0.288% | Heatwave peaks in Northern dry zones (Kalaburagi/Ballari). |
| **`soil_moisture_0_to_7cm`**| 0.000% | **2.091%** | Heavy downpours cause sharp step-up recharge events departing from EWMA. |
| **`wind_speed_10m`** | 0.700% | 0.447% | Episodic convective thunderstorm gusts. |

**Key Baseline Finding:**  
Under smooth natural conditions, temperature has a **0.000% EWMA anomaly rate**, and relative humidity has only **0.037%**. Consequently, any streaming anomaly detector that flags $> 0.5\%$ temperature anomalies under baseline operation is over-triggering. Conversely, natural precipitation and topsoil recharge naturally produce 1.3% to 2.1% EWMA excursions during storms.

---

## 8. Streaming Processing Architecture Readiness

### 8.1 Replay Ingestion Characteristics
- **Total Payload Records:** 175,200 events
- **Virtual Field Partitions:** 10 parallel stream sources
- **Nominal Replay Assumption:** $1 \text{ source hour} = 1 \text{ real second}$
  - Real-world production rate: 10 events / hour
  - Nominal stream ingestion rate: **10 events / second**
  - Dataset replay run duration: $175,200 / 10 = 17,520 \text{ seconds} \approx \mathbf{4.87 \text{ hours}}$
- **Accelerated Replay Configurations:**
  - $10\times$ Accelerated Replay ($1 \text{ source hour} = 100\,\text{ms}$): **100 events / second** (Replay run: $175,200 / 100 = 1,752\text{ s} \approx \mathbf{29.2 \text{ minutes}}$)
  - $60\times$ Accelerated Replay ($1 \text{ source minute} = 1\,\text{second}$): **600 events / second** (Replay run: ~4.9 minutes)

### 8.2 Proposed Streaming Window Configurations (Engineering Recommendations)
Informed by EDA observations of sampling frequency, diurnal cycle, and lag horizons:
1. **Tumbling 1-Hour Window (`TumblingEventTimeWindows.of(Time.hours(1))`):**
   - *Rationale:* Matches the native 1-hour sampling interval for schema conformance, packet validation, and physical limit enforcement.
2. **Sliding 6-Hour Window (`SlidingEventTimeWindows.of(Time.hours(6), Time.hours(1))`):**
   - *Rationale:* Proposed for short-term rate-of-change monitoring (e.g., sudden thermal shock or rapid moisture desiccation).
3. **Hopping / Tumbling 24-Hour Window (`TumblingEventTimeWindows.of(Time.days(1))`):**
   - *Rationale:* Aligned with the 24-hour diurnal harmonic for daily cumulative precipitation ($P_{24h} = \sum \text{precip}$), min/max temperatures, and EWMA tracking.
4. **Hopping / Tumbling 72-Hour Window (`SlidingEventTimeWindows.of(Time.hours(72), Time.hours(6))`):**
   - *Rationale:* Motivated by the 72-hour soil infiltration memory horizon for multi-day drought stress and sustained water balance monitoring.

### 8.3 Canonical Event Streaming Payload Specification (JSON)
```json
{
  "field_id": "KA_BENGALURU",
  "timestamp": "2024-10-05T00:00:00",
  "temperature_2m": 22.4,
  "relative_humidity_2m": 88,
  "dew_point_2m": 20.3,
  "precipitation": 0.0,
  "vapour_pressure_deficit": 0.33,
  "soil_moisture_0_to_7cm": 0.342,
  "wind_speed_10m": 8.5,
  "latitude_grid": 12.9701,
  "longitude_grid": 77.5636,
  "elevation_m": 910.0
}
```

---

## 9. Baseline-Calibrated Fault-Injection Recommendations

*Distinction: Empirical baseline observations provide the grounding for synthesizing realistic artificial faults without setting arbitrary thresholds.*

| Fault Class | Target Sensor(s) | Recommended Injection Parameter | Empirical EDA Justification |
| :--- | :--- | :--- | :--- |
| **1. Stuck Sensor** | `temperature_2m`, `vapour_pressure_deficit` | Hold previous reading constant for **$\ge 18$ consecutive hours** (e.g. 24–48h). | Natural maximum identical run is 4–7 hours across 2 years. 18 hours is $> 2.5\times$ the natural maximum, ensuring zero false positives. |
| **2. Spike Anomaly** | `temperature_2m`, `soil_moisture_0_to_7cm`, `relative_humidity_2m` | Add instantaneous 1-hour delta: $\Delta T \ge +15.0^\circ\text{C}$, $\Delta SM \ge +0.35\,\text{m}^3/\text{m}^3$, $\Delta RH \ge +65\%$. | Baseline 99.9th percentile jumps are 6.6°C, 0.105 m³/m³, and 39% respectively. Injected magnitudes clearly exceed the maximum natural shock. |
| **3. Sensor Drift** | `temperature_2m`, `dew_point_2m` | Linear ramp of **$+0.15^\circ\text{C} / \text{hour}$** sustained over 72–120 hours ($+10.8^\circ\text{C}$ cumulative bias). | Subtly breaches diurnal bounds without tripping instantaneous threshold detectors, allowing evaluation of multi-day rolling EWMA drift filters. |
| **4. Dropout / Missing** | Any telemetry channel or packet | Nullify observations or drop records for **bursts of 3 to 12 hours**. | The baseline has exactly 0 missing values and 0 gaps; any missing packet tests streaming watermark progression and dead-man timer alerts. |
| **5. Out-of-Range** | `relative_humidity_2m`, `soil_moisture_0_to_7cm` | Inject $RH < 0\%$ or $RH > 105\%$; $SM < -0.05\,\text{m}^3/\text{m}^3$ or $SM > 1.10\,\text{m}^3/\text{m}^3$. | Baseline data strictly complies with physical boundaries ($0\le RH\le 100$, $0\le SM\le 1$). Out-of-range should trigger immediate Tumbling 1h filters. |

---

## 10. Phase-I Presentation Target Charts

1. **Temporal Missingness Heatmap (`missingness_heatmap.png`):** Demonstrates 0.000% missingness across all 14 attributes for 175,200 hourly steps.
2. **Diurnal Micro-Climate Profiles (`daily_cycle_combined.png`):** Captures the 24-hour diurnal cycle (temperature peaking at 14:00 IST; RH peaking at 06:00 IST; subtle 0.003 m³/m³ diurnal soil respiration).
3. **Correlation Matrix Heatmap (`correlation_heatmap.png`):** Shows statistical associations ($r = -0.94$ for VPD vs. RH, $r = +0.87$ for VPD vs. Temp).
4. **Rainfall-to-Soil-Moisture Lag Cross-Correlation (`rainfall_to_moisture_lag.png`):** Displays peak cross-correlation at 1-hour lag across 7/10 fields ($r \le 0.297$), decaying over 72 hours.
5. **Natural Anomaly Baseline Example (`natural_anomaly_example.png`):** Highlights 24-hour EWMA control envelope ($0.000\%$ natural temperature outliers vs. natural monsoonal recharge jumps).

---

## 11. Conclusion & Next Steps

Phase-I acquisition, data integrity validation, and statistical characterization are complete and verified against the raw dataset:
1. Constructing the real-time Kafka producer / replay generator with configurable acceleration ($1\times, 10\times, 60\times$).
2. Implementing the baseline-parameterized fault injector module (`stuck`, `spike`, `drift`, `dropout`, `out-of-range`).
3. Deploying Apache Flink / Spark Streaming window aggregations (1h, 6h, 24h, 72h) for real-time crop heat and water stress scoring.
