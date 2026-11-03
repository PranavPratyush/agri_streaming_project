"""Agronomic feature computation functions and Spark column expressions.

Computes Vapor Pressure Deficit (VPD), Dew Point, Leaf Wetness Proxy,
and Soil Moisture Deficit Rates using validated physical/meteorological models.
"""

from __future__ import annotations

import math
from pyspark.sql import Column
import pyspark.sql.functions as F


# ---------------------------------------------------------------------------
# Pure Python Agronomic Functions (Unit-Testable & Deterministic)
# ---------------------------------------------------------------------------

def calculate_saturation_vapor_pressure(temp_c: float) -> float:
    """Calculate saturation vapor pressure (es) in kPa using the Tetens equation.
    
    es(T) = 0.61078 * exp((17.27 * T) / (T + 237.3))
    """
    if math.isnan(temp_c) or math.isinf(temp_c):
        raise ValueError(f"Temperature must be a finite number, got {temp_c}")
    return 0.61078 * math.exp((17.27 * temp_c) / (temp_c + 237.3))


def calculate_vapor_pressure_deficit(temp_c: float, rh_pct: float) -> float:
    """Calculate Vapor Pressure Deficit (VPD) in kPa.
    
    VPD = es(T) * (1 - RH / 100)
    Result bounded to >= 0.0 kPa.
    """
    if rh_pct < 0.0 or rh_pct > 100.0:
        raise ValueError(f"Relative humidity must be between 0 and 100%, got {rh_pct}")
    es = calculate_saturation_vapor_pressure(temp_c)
    ea = es * (rh_pct / 100.0)
    vpd = max(0.0, es - ea)
    return round(vpd, 3)


def calculate_dew_point(temp_c: float, rh_pct: float) -> float:
    """Calculate dew point temperature in degrees Celsius using the Magnus formula.
    
    alpha = ((17.27 * T) / (237.3 + T)) + ln(RH / 100)
    Td = (237.3 * alpha) / (17.27 - alpha)
    """
    bounded_rh = max(0.01, min(100.0, rh_pct))
    alpha = ((17.27 * temp_c) / (237.3 + temp_c)) + math.log(bounded_rh / 100.0)
    dew_point = (237.3 * alpha) / (17.27 - alpha)
    return round(dew_point, 2)


def calculate_leaf_wetness_proxy(temp_c: float, rh_pct: float, dew_point_c: float | None = None) -> float:
    """Calculate leaf wetness proxy as a dimensionless fraction in [0.0, 1.0].
    
    Physical logic:
    Condensation occurs when relative humidity is high (>= 90%) and ambient
    temperature is close to or below the dew point (dew depression <= 2.0 °C).
    """
    if dew_point_c is None:
        dew_point_c = calculate_dew_point(temp_c, rh_pct)

    dew_depression = max(0.0, temp_c - dew_point_c)

    if rh_pct < 80.0:
        return 0.0

    # High humidity contributes to wetness fraction
    rh_factor = (rh_pct - 80.0) / 20.0  # 0.0 at 80% to 1.0 at 100%

    # Small dew depression (<= 2.0 °C) indicates condensation
    if dew_depression <= 0.5:
        depression_factor = 1.0
    elif dew_depression <= 2.0:
        depression_factor = (2.0 - dew_depression) / 1.5
    else:
        depression_factor = 0.0

    proxy = 0.6 * rh_factor + 0.4 * depression_factor
    return round(min(1.0, max(0.0, proxy)), 3)


def calculate_soil_moisture_depletion_rate(
    current_sm: float,
    previous_sm: float,
    delta_hours: float
) -> float:
    """Calculate rate of soil moisture depletion in m³/m³ per hour.
    
    Positive value indicates moisture loss (drying/evapotranspiration).
    Negative value indicates moisture gain (irrigation or rain infiltration).
    """
    if delta_hours <= 0.0:
        return 0.0
    rate = (previous_sm - current_sm) / delta_hours
    return round(rate, 5)


# ---------------------------------------------------------------------------
# Native PySpark Column Expressions (High-Performance JVM Execution)
# ---------------------------------------------------------------------------

def spark_saturation_vapor_pressure(temp_col: Column) -> Column:
    """PySpark expression for saturation vapor pressure es(T) in kPa."""
    return F.lit(0.61078) * F.exp((F.lit(17.27) * temp_col) / (temp_col + F.lit(237.3)))


def spark_vapor_pressure_deficit(temp_col: Column, rh_col: Column) -> Column:
    """PySpark expression for Vapor Pressure Deficit (VPD) in kPa."""
    es = spark_saturation_vapor_pressure(temp_col)
    ea = es * (rh_col / F.lit(100.0))
    return F.round(F.greatest(F.lit(0.0), es - ea), 3)


def spark_dew_point(temp_col: Column, rh_col: Column) -> Column:
    """PySpark expression for dew point temperature in degrees Celsius."""
    bounded_rh = F.greatest(F.lit(0.01), F.least(F.lit(100.0), rh_col))
    alpha = ((F.lit(17.27) * temp_col) / (temp_col + F.lit(237.3))) + F.log(bounded_rh / F.lit(100.0))
    return F.round((F.lit(237.3) * alpha) / (F.lit(17.27) - alpha), 2)


def spark_leaf_wetness_proxy(temp_col: Column, rh_col: Column) -> Column:
    """PySpark expression for leaf wetness proxy in [0.0, 1.0]."""
    dew_point = spark_dew_point(temp_col, rh_col)
    dew_depression = F.greatest(F.lit(0.0), temp_col - dew_point)
    rh_factor = F.greatest(F.lit(0.0), (rh_col - F.lit(80.0)) / F.lit(20.0))
    depression_factor = F.when(dew_depression <= 0.5, F.lit(1.0)) \
                         .when(dew_depression <= 2.0, (F.lit(2.0) - dew_depression) / F.lit(1.5)) \
                         .otherwise(F.lit(0.0))
    proxy = F.lit(0.6) * rh_factor + F.lit(0.4) * depression_factor
    return F.round(
        F.when(rh_col < 80.0, F.lit(0.0))
        .otherwise(F.least(F.lit(1.0), F.greatest(F.lit(0.0), proxy))),
        3
    )

