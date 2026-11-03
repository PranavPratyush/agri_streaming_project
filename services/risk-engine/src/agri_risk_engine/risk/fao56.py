"""Agronomic water balance, FAO-56 crop stress formulations, and fungal risk window calculations."""

import math
from typing import Any

from agri_risk_engine.risk.field_profile import CropStageParameters, SoilProfile


def calculate_taw(soil: SoilProfile, root_depth_m: float) -> float:
    """Calculate Total Available Water (TAW) in the root zone in mm.
    
    FAO-56 Formula: TAW = 1000 * (theta_FC - theta_WP) * Zr
    """
    if root_depth_m <= 0.0:
        return 0.0
    taw = 1000.0 * (soil.field_capacity - soil.wilting_point) * root_depth_m
    return round(max(0.0, taw), 2)


def calculate_raw(taw_mm: float, depletion_fraction_p: float) -> float:
    """Calculate Readily Available Water (RAW) before moisture stress begins in mm.
    
    FAO-56 Formula: RAW = p * TAW
    """
    raw = taw_mm * min(1.0, max(0.0, depletion_fraction_p))
    return round(max(0.0, raw), 2)


def calculate_moisture_stress_threshold(soil: SoilProfile, depletion_fraction_p: float) -> float:
    """Calculate volumetric soil water content threshold below which crop transpiration is restricted.
    
    Formula: theta_threshold = theta_WP + (1 - p) * (theta_FC - theta_WP)
    """
    p = min(1.0, max(0.0, depletion_fraction_p))
    theta_thresh = soil.wilting_point + (1.0 - p) * (soil.field_capacity - soil.wilting_point)
    return round(theta_thresh, 4)


def calculate_soil_moisture_stress_index(
    current_sm: float,
    soil: SoilProfile,
    stage_params: CropStageParameters,
) -> tuple[float, float]:
    """Calculate root-zone soil water stress index and depletion fraction.
    
    Returns (moisture_stress_index, root_zone_depletion_fraction).
    - moisture_stress_index in [0.0, 1.0]: 0.0 = no stress, 1.0 = wilting point reached.
    - depletion_fraction in [0.0, 1.0]: actual fraction of TAW depleted.
    """
    awc = soil.available_water_capacity
    if awc <= 0.0:
        return 0.0, 0.0

    # Total depletion fraction of AWC: Dr / TAW
    depletion_fraction = (soil.field_capacity - current_sm) / awc
    depletion_fraction = min(1.0, max(0.0, depletion_fraction))

    threshold = calculate_moisture_stress_threshold(soil, stage_params.depletion_fraction_p)

    if current_sm >= threshold:
        # Soil moisture is above threshold: within RAW buffer
        stress_index = 0.0
    elif current_sm <= soil.wilting_point:
        # At or below permanent wilting point: maximum stress
        stress_index = 1.0
    else:
        # Linear stress progression from threshold to wilting point
        stress_index = (threshold - current_sm) / (threshold - soil.wilting_point)
        stress_index = min(1.0, max(0.0, stress_index))

    return round(stress_index, 3), round(depletion_fraction, 3)


def calculate_thermal_stress_index(
    temp_c: float,
    stage_params: CropStageParameters,
) -> float:
    """Calculate heat stress index based on phenological crop tolerance.
    
    Finger millet is tolerant up to ~30°C; temperatures >34°C during flowering
    cause severe floret sterility and pollen abortion.
    """
    t_opt_max = stage_params.t_optimal_max_c
    t_crit = stage_params.t_heat_critical_c

    if temp_c <= t_opt_max:
        return 0.0
    if temp_c >= t_crit:
        # Above critical threshold: rapid scaling to 1.0
        excess = temp_c - t_crit
        return round(min(1.0, 0.6 + 0.4 * (excess / 4.0)), 3)

    # Moderate stress between optimal and critical
    stress = 0.6 * (temp_c - t_opt_max) / (t_crit - t_opt_max)
    return round(min(1.0, max(0.0, stress)), 3)


def calculate_vpd_stress_index(
    vpd_kpa: float,
    stage_params: CropStageParameters,
) -> float:
    """Calculate atmospheric evaporative demand stress index.
    
    High VPD forces stomatal closure to prevent xylem cavitation, halting photosynthesis.
    """
    vpd_opt = stage_params.vpd_optimal_kpa
    vpd_crit = stage_params.vpd_critical_kpa

    if vpd_kpa <= vpd_opt:
        return 0.0
    if vpd_kpa >= vpd_crit:
        return 1.0

    stress = (vpd_kpa - vpd_opt) / (vpd_crit - vpd_opt)
    return round(min(1.0, max(0.0, stress)), 3)


def calculate_composite_crop_stress_index(
    s_moisture: float,
    s_vpd: float,
    s_temp: float,
    w_moisture: float = 0.50,
    w_vpd: float = 0.30,
    w_temp: float = 0.20,
) -> float:
    """Calculate the multi-factor Composite Crop Stress Index (CSI).
    
    CSI = w_moisture * S_moisture + w_vpd * S_vpd + w_temp * S_temp
    Range: [0.0, 1.0].
    
    IMPORTANT DISCLAIMER:
    The CSI is a decision-support heuristic index, NOT an empirically calibrated
    probability of physiological crop loss.
    """
    csi = (w_moisture * s_moisture) + (w_vpd * s_vpd) + (w_temp * s_temp)
    return round(min(1.0, max(0.0, csi)), 3)


def evaluate_fungal_blast_risk_window(
    temp_c: float,
    rh_pct: float,
    favorable_hours: float,
    min_required_hours: float = 6.0,
) -> tuple[bool, str]:
    """Evaluate environmental susceptibility for Finger Millet Blast (Pyricularia grisea).
    
    Optimal blast microclimate:
    - Temperature between 20°C and 28°C
    - Relative humidity >= 85% persisting for >= 6 consecutive hours
    
    In accordance with .agents/rules/agronomic-safety.md:
    This evaluates strictly an ENVIRONMENTAL RISK WINDOW, NOT a definitive diagnosis.
    """
    temp_favorable = (20.0 <= temp_c <= 28.0)
    humidity_favorable = (rh_pct >= 85.0)

    if temp_favorable and humidity_favorable and favorable_hours >= min_required_hours:
        reason = (
            f"Favorable microclimate for fungal blast spore germination: "
            f"Temperature ({temp_c:.1f}°C) in 20-28°C range and RH ({rh_pct:.1f}%) >= 85% "
            f"sustained for {favorable_hours:.1f} hours (>= {min_required_hours}h). "
            f"Environmental risk window only; visual scouting required."
        )
        return True, reason

    return False, "Environmental conditions not favorable for blast fungal germination."


def calculate_reference_et0_hargreaves(
    t_mean_c: float,
    t_min_c: float,
    t_max_c: float,
    ra_mj_m2_day: float = 35.0,
) -> float:
    """Calculate daily reference evapotranspiration (ET0) using the FAO-56 Hargreaves-Samani method.
    
    ET0 = 0.0023 * (Tmean + 17.8) * sqrt(Tmax - Tmin) * Ra * 0.408
    """
    temp_range = max(0.1, t_max_c - t_min_c)
    et0 = 0.0023 * (t_mean_c + 17.8) * math.sqrt(temp_range) * (ra_mj_m2_day * 0.408)
    return round(max(0.0, et0), 2)

