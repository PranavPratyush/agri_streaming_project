# FAO Irrigation and Drainage Paper No. 56: Crop Evapotranspiration
**Document ID:** FAO-56-CH06  
**Authors:** Richard G. Allen, Luis S. Pereira, Dirk Raes, Martin Smith  
**Institution:** Food and Agriculture Organization of the United Nations (FAO), Rome  
**Publication Year:** 1998 (Reprinted 2006)  
**Canonical Source:** https://www.fao.org/3/x0490e/x0490e00.htm  
**Corpus Classification:** Standard Reference Manual  
**Document Applicability:** Crop: Small Millets / Millet; Region: Global / Semi-Arid Tropics; Soil: General; Growth Stages: Initial, Crop Development, Mid-Season, Late Season.

---

## Section 1: Single Crop Coefficient Approach (Kc)

The crop evapotranspiration under standard conditions ($ET_c$) is calculated by the single crop coefficient approach:
$$ET_c = K_c \times ET_0$$

Where:
- $ET_0$ is the reference crop evapotranspiration calculated by the FAO-56 Penman-Monteith method ($mm/day$).
- $K_c$ is the crop coefficient integrating crop characteristics and average evaporation effects from the soil.

For Small Millets (including Finger Millet / Eleusine coracana), the typical growth cycle spans 105 to 135 days depending on variety and latitude. Under sub-humid climates with minimum relative humidity ($RH_{min}$) near 45% and moderate wind speed ($u_2 \approx 2\ m/s$), standard baseline values from Table 12 are:
- $K_{c,\text{ini}}$ (Initial Stage, 15–20 days): 0.30 to 0.40. Reflects primarily bare soil evaporation with limited vegetative canopy.
- $K_{c,\text{mid}}$ (Mid-Season Stage, Peak Canopy / Flowering / Early Grain Fill, 40–50 days): 1.00 to 1.10. Represents maximum transpiration demand when effective canopy cover exceeds 75%.
- $K_{c,\text{end}}$ (Late Season / Maturity / Ripening, 25–30 days): 0.30 to 0.50. Represents crop senescence, leaf drying, and pre-harvest dry-down.

When mean daily $RH_{min}$ differs from 45% or wind speed exceeds $2\ m/s$, $K_{c,\text{mid}}$ must be adjusted:
$$K_{c,\text{mid}} = K_{c,\text{mid(Tab)}} + \left[0.04 \times (u_2 - 2) - 0.004 \times (RH_{\min} - 45)\right] \times \left(\frac{h}{3}\right)^{0.3}$$
Where $h$ is the mean plant height in meters ($h \approx 0.9\ m$ for Finger Millet).

---

## Section 2: Effective Rooting Depth and Soil Water Depletion

Effective rooting depth ($Z_r$) for small millets develops progressively:
- Initial Stage: $0.15 - 0.25\ m$.
- Mid-Season / Peak: $0.60 - 0.90\ m$ in deep soils; restricted to $0.40 - 0.50\ m$ in shallow or gravelly red soils.

The Total Available Water ($TAW$) in the root zone is defined as:
$$TAW = 1000 \times (\theta_{FC} - \theta_{WP}) \times Z_r$$
Where:
- $\theta_{FC}$ is the volumetric soil water content at field capacity ($m^3/m^3$).
- $\theta_{WP}$ is the volumetric soil water content at permanent wilting point ($m^3/m^3$).
- $Z_r$ is the rooting depth ($m$).

The Readily Available Water ($RAW$) that the crop can extract without suffering water stress is:
$$RAW = p \times TAW$$
For small millets, the average soil water depletion fraction for no stress is $p = 0.55 - 0.60$.
When evapotranspiration demand is high ($ET_c > 5\ mm/day$), the depletion fraction decreases by approximately 0.05 per $mm/day$ above 5:
$$p_{\text{adj}} = p + 0.04 \times (5 - ET_c)$$

---

## Section 3: Water Stress Coefficient (Ks) and Yield Reduction

When the root zone depletion $D_r$ exceeds $RAW$, crop evapotranspiration drops below standard $ET_c$:
$$ET_{c,\text{adj}} = K_s \times K_c \times ET_0$$

The water stress coefficient $Ks$ ($0 \le K_s \le 1$) is calculated as:
$$K_s = \frac{TAW - D_r}{TAW - RAW} = \frac{TAW - D_r}{(1 - p) \times TAW}$$
If $D_r \le RAW$, then $K_s = 1.0$ (no water stress).
If $D_r \ge TAW$, then $K_s = 0.0$ (wilting point reached; plant cannot extract further water).

The relative yield reduction due to moisture stress across growth stages is expressed by the Stewart yield response factor ($K_y$):
$$\left(1 - \frac{Y_a}{Y_m}\right) = K_y \times \left(1 - \frac{ET_{c,\text{adj}}}{ET_c}\right)$$
For small millets:
- Flowering and earhead emergence stage has the highest sensitivity ($K_y \approx 0.95 - 1.10$). Water deficits during this stage induce spikelet sterility and acute grain yield loss.
- Vegetative and tillering stages exhibit lower sensitivity ($K_y \approx 0.40 - 0.60$), allowing the crop to recover if subsequent rainfall or protective irrigation occurs.
- Ripening and maturity stage has lowest sensitivity ($K_y \approx 0.20 - 0.30$).

