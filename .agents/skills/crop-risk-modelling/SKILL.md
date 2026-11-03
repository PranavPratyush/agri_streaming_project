---
name: "crop-risk-modelling"
description: "Agronomic risk calculation procedures incorporating crop type, variety, phenological growth stage, root depth, soil available water capacity, and evapotranspiration into explainable stress indices."
---

# AgriKafka Skill: Crop Risk Modelling

## Purpose
This skill defines the deterministic agronomic algorithms and environmental feature calculations that evaluate crop water status, thermal stress, and disease risk windows based on physical science and FAO-56 standards.

---

## When to Use
- Implementing or calibrating the risk engine in `services/risk-engine/`.
- Calculating the composite Crop Stress Index (CSI) or crop water balance features.
- Evaluating whether candidate alerts qualify for forwarding to `crop-alerts`.
- Incorporating soil physical parameters (Field Capacity, Permanent Wilting Point) into risk thresholds.

## When NOT to Use
- Determining whether a sensor probe is electrically malfunctioning (use `sensor-health-forensics`).
- Drafting natural-language advisory messages for farmers (use `agri-rag-grounded-advisory`).
- Prescribing chemical fungicides or pesticide dosages (strictly prohibited).

---

## Agronomic Mathematical Models

### 1. Soil Water Balance & Readily Available Water (RAW)
Soil water availability is bounded by:
- $\theta_{FC}$: Field Capacity ($\approx 0.22\text{ m}^3/\text{m}^3$ in Karnataka Red Sandy Loam).
- $\theta_{WP}$: Permanent Wilting Point ($\approx 0.10\text{ m}^3/\text{m}^3$).
- $\text{TAW} = 1000 \times (\theta_{FC} - \theta_{WP}) \times Z_r$ (Total Available Water in mm, where $Z_r$ is root depth in meters).
- $\text{RAW} = p \times \text{TAW}$ (Readily Available Water, where $p \approx 0.5$ is the crop-specific depletion fraction).
- **Water Deficit Trigger:** When root-zone soil moisture $\theta < \theta_{WP} + (1 - p)(\theta_{FC} - \theta_{WP})$, genuine moisture stress begins.

### 2. Composite Crop Stress Index (CSI)
When canopy temperature infrared sensors are unavailable, the system computes an empirical, explainable Crop Stress Index ($0 \le \text{CSI} \le 1.0$):
$$\text{CSI} = w_{\text{soil}} \cdot S_{\text{moisture}} + w_{\text{vpd}} \cdot S_{\text{vpd}} + w_{\text{temp}} \cdot S_{\text{temp}}$$
Where:
- $S_{\text{moisture}} = \max\left(0, \frac{\theta_{\text{threshold}} - \theta}{\theta_{\text{threshold}} - \theta_{WP}}\right)$
- $S_{\text{vpd}} = \frac{\text{VPD} - \text{VPD}_{\text{opt}}}{\text{VPD}_{\max} - \text{VPD}_{\text{opt}}}$ (captures atmospheric evaporative demand)
- $S_{\text{temp}} = \max\left(0, \frac{T - T_{\text{optimal}}}{T_{\text{critical}} - T_{\text{optimal}}}\right)$

### 3. Fungal / Disease Risk Window
- Flagged when Relative Humidity $> 85\%$ AND Temperature between $20^\circ\text{C}$ and $30^\circ\text{C}$ persist for $\ge 6$ consecutive hours.
- Labelled strictly as an *environmental risk window*, NOT a confirmed fungal infection.

---

## Step-by-Step Procedure
1. **Load Field Context:** Retrieve crop type (e.g. Ragi), variety, days after sowing (DAS), growth stage (vegetative, flowering, grain-fill), and root depth $Z_r$.
2. **Calculate Reference ET ($ET_0$):** Apply FAO-56 Penman-Monteith or Hargreaves method using temperature, radiation proxy, and wind speed.
3. **Compute Moisture Depletion:** Calculate actual soil moisture relative to field capacity and wilting point for the active root depth.
4. **Evaluate Multi-Factor Stress:** Compute the Composite Crop Stress Index.
5. **Publish Candidate Alert:** If $\text{CSI} > 0.65$ or moisture stress persists past the depletion threshold, emit candidate alert to `crop-alerts`.

---

## Calibration Limitations & Disclaimers
- The Crop Stress Index is a heuristic decision-support score, not an empirically validated physiological crop damage probability.
- Soil moisture from reanalysis (Open-Meteo) reflects 0–7 cm surface moisture, which dries faster than the deeper root zone ($20–60\text{ cm}$). Depth compensation factors must be documented in calibration notes.
