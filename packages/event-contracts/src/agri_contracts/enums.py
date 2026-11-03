"""Enumerations for AgriKafka-Agent event contracts."""

from enum import Enum


class ProvenanceClass(str, Enum):
    """Explicit data provenance classification enforcing data integrity rules.
    
    In accordance with .agents/rules/data-provenance.md, modelled/reanalysis data
    must never be conflated with physical sensor telemetry.
    """
    PHYSICAL_SENSOR = "physical_sensor"
    EXTERNAL_STATION = "external_station"
    MODELLED_REANALYSIS = "modelled_reanalysis"
    FORECAST = "forecast"
    DERIVED = "derived"
    HISTORICAL_REPLAY = "historical_replay"
    INJECTED_SCENARIO = "injected_scenario"


class ObservedVariable(str, Enum):
    """Standardized agronomic and environmental observation variables."""
    TEMPERATURE_2M = "temperature_2m"
    RELATIVE_HUMIDITY_2M = "relative_humidity_2m"
    DEW_POINT_2M = "dew_point_2m"
    PRECIPITATION = "precipitation"
    PRECIPITATION_RATE = "precipitation_rate"
    VAPOUR_PRESSURE_DEFICIT = "vapour_pressure_deficit"
    SOIL_MOISTURE_0_TO_7CM = "soil_moisture_0_to_7cm"
    SOIL_MOISTURE_15CM = "soil_moisture_15cm"
    SOIL_MOISTURE_30CM = "soil_moisture_30cm"
    SOIL_TEMPERATURE_0CM = "soil_temperature_0cm"
    WIND_SPEED_10M = "wind_speed_10m"
    WIND_DIRECTION = "wind_direction"
    BAROMETRIC_PRESSURE = "barometric_pressure"
    SOLAR_RADIATION = "solar_radiation"
    UV_INDEX = "uv_index"
    LEAF_WETNESS_PROXY = "leaf_wetness_proxy"
    CROP_STRESS_INDEX = "crop_stress_index"


class StandardUnit(str, Enum):
    """Standardized SI and agronomic measurement units."""
    CELSIUS = "celsius"
    PERCENT = "percent"
    MM = "mm"
    MM_PER_HOUR = "mm_per_hour"
    KPA = "kpa"
    HPA = "hpa"
    M3_PER_M3 = "m3_per_m3"
    M_PER_S = "m_per_s"
    KM_PER_H = "km_per_h"
    W_PER_M2 = "w_per_m2"
    DEGREES = "degrees"
    FRACTION_0_TO_1 = "fraction_0_to_1"
    UNITLESS = "unitless"


class ValidationStatus(str, Enum):
    """Quality assertion status for an observation."""
    VALID = "VALID"
    SUSPECT = "SUSPECT"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    STALE = "STALE"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


class SensorHealthFlag(str, Enum):
    """Forensic sensor health states evaluated by the deterministic health service."""
    HEALTHY = "HEALTHY"
    STUCK_VALUE = "STUCK_VALUE"
    SPIKE_ANOMALY = "SPIKE_ANOMALY"
    DRIFT_ANOMALY = "DRIFT_ANOMALY"
    DROPOUT = "DROPOUT"
    OUT_OF_BOUNDS = "OUT_OF_BOUNDS"
    UNKNOWN = "UNKNOWN"


class HealthState(str, Enum):
    """Explicit sensor health status model for data-quality gating."""
    HEALTHY = "HEALTHY"
    STALE = "STALE"
    SUSPECT = "SUSPECT"
    FAULTY = "FAULTY"
    UNKNOWN = "UNKNOWN"


class CropRiskLevel(str, Enum):
    """Standardized agronomic risk severity levels."""
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class InvestigationDecision(str, Enum):
    """Outcome of the Bounded Alert Investigator."""
    ADVISORY_ISSUED = "ADVISORY_ISSUED"
    ALERT_ESCALATED = "ALERT_ESCALATED"
    SUPPRESSED_SENSOR_FAULT = "SUPPRESSED_SENSOR_FAULT"
    SUPPRESSED_NO_STRESS = "SUPPRESSED_NO_STRESS"
    SYSTEM_FALLBACK = "SYSTEM_FALLBACK"


class HumanFeedbackDecision(str, Enum):
    """Action taken by the human farmer or agronomist."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"
    DEFERRED = "DEFERRED"
    EXPIRED = "EXPIRED"
