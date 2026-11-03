"""Field profile models and verified ICAR / UAS Bangalore agronomic baselines."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class SoilProfile(BaseModel):
    """Soil physical properties governing root-zone water balance."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    soil_type: str = Field(
        description="Textural soil class (e.g. Red Sandy Loam / Alfisol)"
    )
    field_capacity: float = Field(
        ge=0.05,
        le=0.50,
        description="Volumetric soil water content at field capacity (m³/m³)"
    )
    wilting_point: float = Field(
        ge=0.01,
        le=0.30,
        description="Volumetric soil water content at permanent wilting point (m³/m³)"
    )
    residual_moisture: float = Field(
        ge=0.01,
        le=0.20,
        description="Residual water content theta_r (m³/m³) during prolonged drought"
    )
    bulk_density_g_cm3: float = Field(
        default=1.45,
        ge=1.0,
        le=1.8,
        description="Soil bulk density in g/cm³"
    )
    provenance: str = Field(
        default="UAS Bangalore Soil Science & Zone 5 Dryland Agronomy Package",
        description="Source of physical soil measurements"
    )

    @property
    def available_water_capacity(self) -> float:
        """Available Water Capacity (AWC = FC - WP) in m³/m³."""
        return max(0.0, self.field_capacity - self.wilting_point)


class CropStageParameters(BaseModel):
    """Phenological growth stage parameters and FAO-56 crop coefficients."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    stage_name: str = Field(
        description="Phenological stage (e.g. initial, vegetative, flowering_heading, grain_filling)"
    )
    kc: float = Field(
        ge=0.2,
        le=1.4,
        description="FAO-56 single crop coefficient (Kc)"
    )
    root_depth_m: float = Field(
        ge=0.05,
        le=1.5,
        description="Effective crop root zone depth in meters (Zr)"
    )
    depletion_fraction_p: float = Field(
        ge=0.1,
        le=0.8,
        description="FAO-56 maximum allowable soil water depletion fraction (p)"
    )
    t_optimal_min_c: float = Field(
        default=22.0,
        description="Lower bound of optimal temperature range in °C"
    )
    t_optimal_max_c: float = Field(
        default=30.0,
        description="Upper bound of optimal temperature range in °C"
    )
    t_heat_critical_c: float = Field(
        default=34.0,
        description="Critical threshold above which floret sterility/stress occurs in °C"
    )
    vpd_optimal_kpa: float = Field(
        default=1.2,
        description="Optimal Vapour Pressure Deficit in kPa"
    )
    vpd_critical_kpa: float = Field(
        default=2.8,
        description="Critical Vapour Pressure Deficit causing stomatal closure in kPa"
    )
    provenance: str = Field(
        default="ICAR-IIMR & UAS Bangalore Finger Millet Production Technology Bulletin",
        description="Agronomic source of crop parameters"
    )


class FieldProfile(BaseModel):
    """Complete contextual agricultural parcel profile."""
    model_config = ConfigDict(extra="forbid")

    field_id: str = Field(
        min_length=1,
        description="Unique identifier of agricultural parcel (e.g. field_kolar_ragi_01)"
    )
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    crop_name: str | None = Field(default=None, description="Crop name (e.g. Finger Millet / Ragi)")
    variety: str | None = Field(default=None, description="Cultivar or variety (e.g. GPU-28, ML-365)")
    sowing_date: datetime | None = Field(default=None, description="Date of sowing or transplanting")
    growth_stage: str | None = Field(default=None, description="Active phenological growth stage")
    irrigation_method: str | None = Field(
        default="rainfed",
        description="Irrigation infrastructure (rainfed, protective_sprinkler, drip)"
    )
    soil_profile: SoilProfile | None = Field(
        default=None,
        description="Physical soil profile parameters"
    )
    stage_parameters: CropStageParameters | None = Field(
        default=None,
        description="Active phenological stage parameters"
    )
    sensor_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Installed in-situ probe metadata (depth, hardware IDs)"
    )

    def is_profile_complete(self) -> tuple[bool, list[str]]:
        """Verify whether contextual profile contains all required parameters for numerical risk models.
        
        Returns (is_complete, missing_fields_list).
        In accordance with .agents/rules/agronomic-safety.md:
        Missing critical parameters require explicit abstention, never fabricated defaults.
        """
        missing: list[str] = []
        if not self.crop_name:
            missing.append("crop_name")
        if not self.growth_stage:
            missing.append("growth_stage")
        if not self.soil_profile:
            missing.append("soil_profile")
        if not self.stage_parameters:
            missing.append("stage_parameters")
        return len(missing) == 0, missing


# ---------------------------------------------------------------------------
# Verified Regional Reference Profiles (UAS Bangalore Zone 5 / Kolar)
# ---------------------------------------------------------------------------

def get_kolar_red_sandy_loam_soil() -> SoilProfile:
    """Verified physical soil parameters for Red Sandy Loam (Zone 5, Kolar, Karnataka).
    
    Source: UAS Bangalore Soil Survey & ICAR National Bureau of Soil Survey (NBSS&LUP).
    - Field Capacity (FC): 0.22 m³/m³ (22% volumetric)
    - Permanent Wilting Point (WP): 0.10 m³/m³ (10% volumetric)
    - Available Water Capacity (AWC): 0.12 m³/m³ (120 mm/m)
    - Residual water content: 0.08 m³/m³
    - Bulk Density: 1.45 g/cm³
    """
    return SoilProfile(
        soil_type="Red Sandy Loam (Alfisols)",
        field_capacity=0.22,
        wilting_point=0.10,
        residual_moisture=0.08,
        bulk_density_g_cm3=1.45,
        provenance="UAS Bangalore Zone 5 Dryland Soil Survey & ICAR NBSS&LUP Bulletin 124",
    )


def get_ragi_flowering_stage_params() -> CropStageParameters:
    """Verified phenological parameters for Finger Millet (GPU-28 / ML-365) at flowering stage.
    
    Source: UAS Bangalore Package of Practices & FAO-56 Irrigation and Drainage Paper No. 56.
    - Growth Stage: flowering_heading (DAS 46–75)
    - Crop Coefficient (Kc): 1.05 (Peak transpirational water demand)
    - Root Depth (Zr): 0.50 m
    - Depletion Fraction (p): 0.45 (High drought sensitivity during panicle emergence)
    - Optimal Temp: 22.0 - 30.0 °C
    - Critical Heat Threshold: 34.0 °C (Spikelet sterility trigger)
    - Optimal VPD: 1.2 kPa; Critical VPD: 2.8 kPa
    """
    return CropStageParameters(
        stage_name="flowering_heading",
        kc=1.05,
        root_depth_m=0.50,
        depletion_fraction_p=0.45,
        t_optimal_min_c=22.0,
        t_optimal_max_c=30.0,
        t_heat_critical_c=34.0,
        vpd_optimal_kpa=1.2,
        vpd_critical_kpa=2.8,
        provenance="UAS Bangalore High-Yielding Ragi Package & FAO-56 Table 12",
    )


def get_verified_kolar_ragi_profile(
    field_id: str = "field_kolar_ragi_01",
    growth_stage: str = "flowering_heading",
) -> FieldProfile:
    """Build a fully grounded, defensible reference profile for a Kolar smallholder parcel."""
    return FieldProfile(
        field_id=field_id,
        latitude=13.137,
        longitude=78.129,
        crop_name="Finger Millet (Ragi)",
        variety="GPU-28",
        growth_stage=growth_stage,
        irrigation_method="rainfed_protective_sprinkler",
        soil_profile=get_kolar_red_sandy_loam_soil(),
        stage_parameters=get_ragi_flowering_stage_params(),
        sensor_metadata={
            "soil_probe_depth_cm": 15.0,
            "sensor_model": "Capacitive_FDR_v1.2",
            "telemetry_source": "openSenseMap_Sarvamangalam",
        },
    )

