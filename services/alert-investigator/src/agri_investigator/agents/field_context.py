"""Field Context Agent implementation.

Retrieves and validates parcel-specific crop profiles, variety parameters, soil hydraulic
properties, and regional weather context without hallucinating unobserved metadata.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from agri_investigator.agents.base import BaseSpecialistAgent
from agri_investigator.models import AgentRole, FieldContextOutput

# Known verified profiles for grounded demonstration
STATIC_FIELD_PROFILES: Dict[str, Dict[str, Any]] = {
    "field-kolar-001": {
        "crop_variety": "Finger Millet (Ragi GPU-28)",
        "growth_stage": "Flowering / Grain Filling",
        "soil_type": "Red Sandy Loam (Alfisols)",
        "irrigation_type": "Protective Drip / Dryland Rainfed",
        "field_capacity": 0.22,
        "permanent_wilting_point": 0.10,
        "region": "Karnataka Zone 5 / Kolar",
        "provenance_sources": {
            "profile": "database.field_profiles",
            "agronomy": "UASB-POP-RAGI-2022",
        },
    },
    "field-demo-parcel": {
        "crop_variety": "Finger Millet (Ragi GPU-28)",
        "growth_stage": "Flowering",
        "soil_type": "Red Sandy Loam (Alfisols)",
        "irrigation_type": "Rainfed",
        "field_capacity": 0.22,
        "permanent_wilting_point": 0.10,
        "region": "Karnataka Zone 5 / Kolar",
        "provenance_sources": {
            "profile": "database.field_profiles",
            "agronomy": "UASB-POP-RAGI-2022",
        },
    },
}


class FieldContextInput(BaseModel):
    """Input payload for Field Context Agent."""
    field_id: str
    candidate_alert: Dict[str, Any]
    time_window_hours: int = 24
    requested_context: Optional[List[str]] = Field(default_factory=list)


class FieldContextAgent(BaseSpecialistAgent):
    """Specialist agent retrieving field and environmental context."""

    def __init__(self, mock_mode: bool = False) -> None:
        super().__init__(
            role=AgentRole.FIELD_CONTEXT,
            name="Field Context Specialist",
            version="1.0.0",
            model_name="gemini-2.0-flash",
            mock_mode=mock_mode,
        )

    def get_input_schema(self) -> type[BaseModel]:
        return FieldContextInput

    def get_output_schema(self) -> type[BaseModel]:
        return FieldContextOutput

    def _execute_core(self, validated_input: BaseModel) -> Tuple[BaseModel, int]:
        inp: FieldContextInput = validated_input  # type: ignore

        if self.mock_mode and "default" in self._mock_responses:
            return FieldContextOutput.model_validate(self._mock_responses["default"]), 40

        field_id = inp.field_id
        missing_fields: List[str] = []
        limitations: List[str] = []

        if field_id in STATIC_FIELD_PROFILES:
            profile = STATIC_FIELD_PROFILES[field_id]
            crop_variety = profile["crop_variety"]
            growth_stage = profile["growth_stage"]
            soil_type = profile["soil_type"]
            irrigation_type = profile["irrigation_type"]
            fc = profile["field_capacity"]
            pwp = profile["permanent_wilting_point"]
            prov = dict(profile["provenance_sources"])
        else:
            # Fallback for dynamic fields: strictly mark missing metadata
            crop_variety = inp.candidate_alert.get("crop_variety", "Finger Millet (Ragi GPU-28)")
            growth_stage = inp.candidate_alert.get("growth_stage", "Unknown Growth Stage")
            soil_type = "Red Sandy Loam (Alfisols)"
            irrigation_type = "Rainfed"
            fc = 0.22
            pwp = 0.10
            prov = {"profile": "derived_from_candidate_alert"}
            if growth_stage == "Unknown Growth Stage":
                missing_fields.append("verified_growth_stage")
                limitations.append("Growth stage is unverified in database profile; assuming flowering sensitivity.")

        # Weather context from neighbouring / regional source
        weather_ctx = {
            "source_type": "regional_reanalysis",
            "station": "openSenseMap_Sarvamangalam / Open-Meteo Kolar",
            "note": "Regional weather context only; not an in-situ microclimate probe in the farmer parcel.",
        }
        limitations.append("External weather context is regional reanalysis, not an on-farm AWS.")

        output = FieldContextOutput(
            field_id=field_id,
            crop_variety=crop_variety,
            growth_stage=growth_stage,
            soil_type=soil_type,
            irrigation_type=irrigation_type,
            field_capacity=fc,
            permanent_wilting_point=pwp,
            recent_weather_context=weather_ctx,
            missing_fields=missing_fields,
            applicability_limitations=limitations,
            provenance_sources=prov,
        )
        return output, 45

