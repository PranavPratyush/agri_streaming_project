---
name: "sensor-health-forensics"
description: "Deterministic forensic analysis of agricultural sensor health: detecting stale data, stuck values, spikes, drift, dropouts, physical plausibility, and distinguishing natural precipitation flatlines from hardware failures."
---

# AgriKafka Skill: Sensor Health Forensics

## Purpose
This skill provides the deterministic algorithms, rules, and mathematical bounds for assessing sensor health and data quality in agricultural telemetry before data reaches the crop risk engine or AI agent.

---

## When to Use
- Developing or maintaining the deterministic quality service in `services/risk-engine/` and `services/stream-processor/`.
- Differentiating between hardware malfunctions and natural environmental phenomena.
- Generating sensor health diagnostics published to Kafka topic `sensor-health`.
- Suppressing false alerts caused by dead batteries, severed cables, or bio-fouling.

## When NOT to Use
- Computing agronomic crop water stress (use `crop-risk-modelling`).
- Triaging alerts with the LLM (use `bounded-alert-investigator`).

---

## Forensic Failure Classes & Mathematical Rules

| Failure Class | Diagnostic Condition | Mathematical / Algorithmic Rule |
|---|---|---|
| **Stale / Missing** | Absence of updates past expected interval | $\Delta t = t_{\text{curr}} - t_{\text{last}} > 3 \times T_{\text{cadence}}$ |
| **Stuck Value** | Identical reading repeated across long time windows | $\text{Var}(X_{t-k \dots t}) < \epsilon$ AND $\Delta X = 0$ for $k > K_{\text{threshold}}$ |
| **Out-of-Bounds** | Value violates physical terrestrial plausibility | $X_t < X_{\min}$ OR $X_t > X_{\max}$ (e.g. soil moisture $< 0$ or $> 0.65\text{ m}^3/\text{m}^3$) |
| **Sudden Spike** | Physically impossible rate-of-change between consecutive readings | $|\Delta X / \Delta t| > \text{MaxDeltaRate}$ (e.g. soil moisture jumping $0.30\text{ m}^3/\text{m}^3$ in 5 minutes without rain) |
| **Sensor Drift** | Gradual deviation from neighboring field or physical baseline | Cumulative divergence $|X_{i,t} - \bar{X}_{\text{neighbors},t}| > 3\sigma_{\text{spatial}}$ over $N$ consecutive windows |
| **Signal Dropout** | Sudden drop to exactly zero or electrical saturation (-999, 1023) | $X_t \in \{0.0, -99.9, -999.0, 1023.0\}$ with rapid restoration |

---

## Natural Flatline Differentiation (Critical Principle)
- **Natural Flatlines:**
  - Precipitation in Karnataka can naturally remain at $0.0\text{ mm}$ for weeks (Phase 1 EDA showed natural zero-rain flatlines up to 2,107 hours).
  - Soil moisture in dry seasons naturally plateaus at residual water content ($\theta_r \approx 0.08–0.12\text{ m}^3/\text{m}^3$) for hundreds of hours.
- **Rule:** A zero-variance reading in precipitation or soil moisture is **NOT** a sensor fault unless corroborated by:
  1. Ambient rainfall detected by adjacent fields or weather radar during the flatline.
  2. Battery voltage drop or RSSI transmission failure flags.
  3. Violation of diurnal temperature thermal expansion signals.

---

## Step-by-Step Procedure
1. **Plausibility Check:** Validate that raw readings fall within physically possible bounds for the agro-climatic region.
2. **Delta Rate Check:** Compare against the previous reading in the field partition; flag rate-of-change anomalies.
3. **Rolling Variance Check:** Calculate moving variance over a 24-hour sliding window to catch stuck values.
4. **Spatial Cross-Check:** Correlate against the mean of neighboring fields ($< 25\text{ km}$ radius).
5. **Publish Forensic Health State:** Write health record to `sensor-health` topic with explicit classification (`HEALTHY`, `STUCK`, `DRIFT`, `SPIKE`, `STALE`, `UNRELIABLE`).
