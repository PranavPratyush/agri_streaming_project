"""Validation rules, plausible agronomic ranges, and canonical unit conversions."""

from __future__ import annotations

from typing import Any
import json
from datetime import datetime, timezone
from agri_contracts.enums import (
    ObservedVariable,
    StandardUnit,
    ValidationStatus,
)
from agri_contracts.models.dead_letter import DeadLetterRecordEvent


# Plausible physical and agronomic boundaries for Southern Karnataka semi-arid drylands
VARIABLE_BOUNDS: dict[ObservedVariable, tuple[float, float, StandardUnit]] = {
    ObservedVariable.TEMPERATURE_2M: (-5.0, 55.0, StandardUnit.CELSIUS),
    ObservedVariable.RELATIVE_HUMIDITY_2M: (0.0, 100.0, StandardUnit.PERCENT),
    ObservedVariable.DEW_POINT_2M: (-10.0, 40.0, StandardUnit.CELSIUS),
    ObservedVariable.PRECIPITATION: (0.0, 300.0, StandardUnit.MM),
    ObservedVariable.PRECIPITATION_RATE: (0.0, 300.0, StandardUnit.MM_PER_HOUR),
    ObservedVariable.VAPOUR_PRESSURE_DEFICIT: (0.0, 10.0, StandardUnit.KPA),
    ObservedVariable.SOIL_MOISTURE_0_TO_7CM: (0.0, 0.70, StandardUnit.M3_PER_M3),
    ObservedVariable.SOIL_MOISTURE_15CM: (0.0, 0.70, StandardUnit.M3_PER_M3),
    ObservedVariable.SOIL_MOISTURE_30CM: (0.0, 0.70, StandardUnit.M3_PER_M3),
    ObservedVariable.SOIL_TEMPERATURE_0CM: (-5.0, 65.0, StandardUnit.CELSIUS),
    ObservedVariable.WIND_SPEED_10M: (0.0, 50.0, StandardUnit.M_PER_S),
    ObservedVariable.BAROMETRIC_PRESSURE: (800.0, 1100.0, StandardUnit.HPA),
    ObservedVariable.SOLAR_RADIATION: (0.0, 1500.0, StandardUnit.W_PER_M2),
    ObservedVariable.UV_INDEX: (0.0, 20.0, StandardUnit.UNITLESS),
    ObservedVariable.LEAF_WETNESS_PROXY: (0.0, 1.0, StandardUnit.FRACTION_0_TO_1),
    ObservedVariable.CROP_STRESS_INDEX: (0.0, 1.0, StandardUnit.FRACTION_0_TO_1),
}


def validate_observation_bounds(
    variable: ObservedVariable,
    value: float,
    unit: StandardUnit
) -> tuple[ValidationStatus, str | None]:
    """Validate a numeric value against plausible physical bounds.
    
    Returns (ValidationStatus, failure_reason_or_none).
    """
    if variable not in VARIABLE_BOUNDS:
        return ValidationStatus.UNKNOWN, f"No explicit bounds configured for variable '{variable}'"

    min_val, max_val, expected_unit = VARIABLE_BOUNDS[variable]

    if unit != expected_unit:
        return ValidationStatus.INVALID, f"Unit mismatch: variable '{variable}' expects '{expected_unit}', got '{unit}'"

    if value < min_val or value > max_val:
        return ValidationStatus.OUT_OF_RANGE, (
            f"Value {value} {unit} is outside plausible range [{min_val}, {max_val}] for '{variable}'"
        )

    return ValidationStatus.VALID, None


def convert_to_standard_unit(
    variable: ObservedVariable,
    value: float,
    from_unit: str
) -> tuple[float, StandardUnit]:
    """Convert common provider units into canonical SI units.
    
    Raises ValueError if conversion is unsupported.
    """
    norm = from_unit.strip().lower()

    # Temperature
    if variable in (ObservedVariable.TEMPERATURE_2M, ObservedVariable.DEW_POINT_2M, ObservedVariable.SOIL_TEMPERATURE_0CM):
        if norm in ("°c", "c", "celsius"):
            return value, StandardUnit.CELSIUS
        if norm in ("°f", "f", "fahrenheit"):
            return round((value - 32.0) * 5.0 / 9.0, 3), StandardUnit.CELSIUS
        if norm in ("k", "kelvin"):
            return round(value - 273.15, 3), StandardUnit.CELSIUS

    # Wind speed
    if variable == ObservedVariable.WIND_SPEED_10M:
        if norm in ("m/s", "m_per_s", "mps"):
            return value, StandardUnit.M_PER_S
        if norm in ("km/h", "km_per_h", "kmh"):
            # 1 km/h = 1 / 3.6 m/s
            return round(value / 3.6, 3), StandardUnit.M_PER_S
        if norm in ("knots", "kt"):
            return round(value * 0.514444, 3), StandardUnit.M_PER_S

    # Pressure
    if variable == ObservedVariable.BAROMETRIC_PRESSURE:
        if norm in ("hpa", "mbar"):
            return value, StandardUnit.HPA
        if norm in ("kpa",):
            return round(value * 10.0, 2), StandardUnit.HPA

    # Precipitation
    if variable in (ObservedVariable.PRECIPITATION, ObservedVariable.PRECIPITATION_RATE):
        if norm in ("mm", "millimeter"):
            return value, StandardUnit.MM
        if norm in ("mm/h", "mm_per_hour", "mm/hr"):
            return value, StandardUnit.MM_PER_HOUR

    # Relative humidity
    if variable == ObservedVariable.RELATIVE_HUMIDITY_2M:
        if norm in ("%", "percent"):
            return value, StandardUnit.PERCENT
        if norm in ("fraction", "0_to_1") and 0.0 <= value <= 1.0:
            return round(value * 100.0, 2), StandardUnit.PERCENT

    # Soil moisture
    if variable in (ObservedVariable.SOIL_MOISTURE_0_TO_7CM, ObservedVariable.SOIL_MOISTURE_15CM, ObservedVariable.SOIL_MOISTURE_30CM):
        if norm in ("m³/m³", "m3/m3", "m3_per_m3", "volumetric"):
            return value, StandardUnit.M3_PER_M3
        if norm in ("%", "percent") and 0.0 <= value <= 100.0:
            return round(value / 100.0, 4), StandardUnit.M3_PER_M3

    # Fallback to direct enum match
    try:
        return value, StandardUnit(norm)
    except ValueError:
        raise ValueError(f"Unsupported unit '{from_unit}' for variable '{variable}'")


def wrap_in_dead_letter(
    raw_payload: str | bytes,
    failed_topic: str,
    error: Exception | str,
    partition: int | None = None,
    offset: int | None = None,
    correlation_id: str | None = None,
) -> DeadLetterRecordEvent:
    """Create a standardized dead-letter record for unparseable or rejected messages."""
    payload_str = raw_payload.decode("utf-8", errors="replace") if isinstance(raw_payload, bytes) else str(raw_payload)
    err_class = error.__class__.__name__ if isinstance(error, Exception) else "ValidationError"
    err_msg = str(error)

    return DeadLetterRecordEvent(
        failed_topic=failed_topic,
        source_partition=partition,
        source_offset=offset,
        error_reason=err_msg,
        error_class=err_class,
        raw_payload=payload_str,
        failed_at=datetime.now(timezone.utc),
        correlation_id=correlation_id,
    )
