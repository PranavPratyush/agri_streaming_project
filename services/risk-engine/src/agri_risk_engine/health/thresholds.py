"""Configurable thresholds with explicit physical units, agronomic provenance, and rationale."""

from dataclasses import dataclass, field
from typing import Any

from agri_contracts.enums import ObservedVariable, StandardUnit


@dataclass(frozen=True)
class ThresholdParameter:
    """Configurable threshold parameter carrying full traceability metadata."""
    name: str
    value: Any
    unit: str
    provenance: str
    rationale: str


@dataclass
class HealthThresholdsConfig:
    """Master configurable threshold repository for deterministic sensor health forensics."""

    # -----------------------------------------------------------------------
    # 1. Staleness & Cadence Parameters
    # -----------------------------------------------------------------------
    cadence_multiplier: ThresholdParameter = field(
        default_factory=lambda: ThresholdParameter(
            name="cadence_multiplier",
            value=3.0,
            unit="ratio",
            provenance="WMO-No. 8 (Guide to Meteorological Instruments and Methods of Observation, Part III)",
            rationale="A sensor telemetry feed is declared stale after missing 3 consecutive expected reporting intervals.",
        )
    )
    max_acceptable_age_sec: ThresholdParameter = field(
        default_factory=lambda: ThresholdParameter(
            name="max_acceptable_age_sec",
            value=3600.0,
            unit="seconds",
            provenance="openSenseMap / IMD AWS operational latency SLA",
            rationale="Observations older than 1 hour without refresh cannot support real-time acute risk decisions.",
        )
    )
    clock_skew_tolerance_sec: ThresholdParameter = field(
        default_factory=lambda: ThresholdParameter(
            name="clock_skew_tolerance_sec",
            value=120.0,
            unit="seconds",
            provenance="NTP network synchronization jitter standard",
            rationale="Timestamps in the future by >2 minutes indicate RTC malfunction or misconfigured gateway clock.",
        )
    )

    # -----------------------------------------------------------------------
    # 2. Rate-of-Change / Spike Limits (Per Variable, Max Delta per Minute)
    # -----------------------------------------------------------------------
    max_rate_of_change_per_minute: dict[ObservedVariable, ThresholdParameter] = field(
        default_factory=lambda: {
            ObservedVariable.TEMPERATURE_2M: ThresholdParameter(
                name="temp_max_rate",
                value=5.0,
                unit="celsius_per_minute",
                provenance="IMD AWS Quality Control Standard & WMO-No. 8",
                rationale="Ambient air temperature cannot naturally shift >5°C within 60 seconds without fire or sensor disconnection.",
            ),
            ObservedVariable.RELATIVE_HUMIDITY_2M: ThresholdParameter(
                name="rh_max_rate",
                value=20.0,
                unit="percent_per_minute",
                provenance="WMO-No. 8 Humidity Sensor Guidelines",
                rationale="Relative humidity changes >20% within 1 minute indicate condensation shock or capacitive sensor defect.",
            ),
            ObservedVariable.SOIL_MOISTURE_0_TO_7CM: ThresholdParameter(
                name="soil_moisture_max_rate",
                value=0.08,
                unit="m3_per_m3_per_minute",
                provenance="UAS Bangalore Red Sandy Loam Soil Physics & Saturated Hydraulic Conductivity (Ksat)",
                rationale="Volumetric soil moisture cannot increase >0.08 m³/m³ per minute unless extreme standing water infiltration occurs.",
            ),
            ObservedVariable.BAROMETRIC_PRESSURE: ThresholdParameter(
                name="pressure_max_rate",
                value=4.0,
                unit="hpa_per_minute",
                provenance="WMO Atmospheric Pressure Pressure-Tendency Guide",
                rationale="Terrestrial atmospheric pressure shifts >4 hPa/min exceed tornado/severe cyclone boundaries.",
            ),
        }
    )

    # -----------------------------------------------------------------------
    # 3. Stuck Value Limits (Zero Variance Window Duration & Thresholds)
    # -----------------------------------------------------------------------
    stuck_window_hours: ThresholdParameter = field(
        default_factory=lambda: ThresholdParameter(
            name="stuck_window_hours",
            value=12.0,
            unit="hours",
            provenance="Diurnal Solar Radiation & Thermodynamic Variance Cycle",
            rationale="Temperature, humidity, and solar radiation must exhibit natural diurnal variance over 12 daytime hours.",
        )
    )
    stuck_variance_epsilon: ThresholdParameter = field(
        default_factory=lambda: ThresholdParameter(
            name="stuck_variance_epsilon",
            value=1e-4,
            unit="squared_units",
            provenance="Digital ADC Quantization Noise Floor (10-bit to 12-bit DAC)",
            rationale="Real hardware analog probes exhibit electrical quantization noise floor of at least 1e-4 variance.",
        )
    )
    stuck_min_consecutive_identical: ThresholdParameter = field(
        default_factory=lambda: ThresholdParameter(
            name="stuck_min_consecutive_identical",
            value=12,
            unit="count",
            provenance="Sampling Cadence Standard (e.g. 5-min cadence * 12 = 1 hour identical)",
            rationale="12 identical floating-point readings on a high-precision sensor indicate stuck ADC register or frozen I2C bus.",
        )
    )

    # -----------------------------------------------------------------------
    # 4. Signal Dropout Sentinel Values
    # -----------------------------------------------------------------------
    dropout_sentinels: ThresholdParameter = field(
        default_factory=lambda: ThresholdParameter(
            name="dropout_sentinels",
            value={-99.9, -999.0, -9999.0, 1023.0, 4095.0, 65535.0},
            unit="raw_codes",
            provenance="Microcontroller ADC Saturation (10/12/16-bit) & Missing Value Flags",
            rationale="Electrical disconnection or uncalibrated firmware reads pull-up resistor or saturation value.",
        )
    )

    # -----------------------------------------------------------------------
    # 5. Sensor Drift Thresholds
    # -----------------------------------------------------------------------
    drift_sigma_threshold: ThresholdParameter = field(
        default_factory=lambda: ThresholdParameter(
            name="drift_sigma_threshold",
            value=3.0,
            unit="standard_deviations",
            provenance="Three-Sigma Statistical Anomaly Detection & Shewhart Control Limits",
            rationale="Persistent divergence >3 standard deviations from reference/neighbor mean across >=24 hours indicates sensor drift.",
        )
    )
    drift_min_history_samples: ThresholdParameter = field(
        default_factory=lambda: ThresholdParameter(
            name="drift_min_history_samples",
            value=24,
            unit="count",
            provenance="Central Limit Theorem Minimum Sample Size",
            rationale="At least 24 temporal samples are required to establish statistically valid mean and variance for drift.",
        )
    )

    def get_max_rate_for_variable(self, variable: ObservedVariable) -> float:
        """Retrieve maximum allowable rate of change per minute for an observed variable."""
        if variable in self.max_rate_of_change_per_minute:
            return float(self.max_rate_of_change_per_minute[variable].value)
        return 100.0  # Safe default if variable has no explicit rate limit

