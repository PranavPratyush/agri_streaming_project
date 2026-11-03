"""Deterministic Crop-Context-Aware Agronomic Risk Engine."""

from datetime import datetime, timezone
from typing import Any
import uuid

from agri_contracts.enums import CropRiskLevel, ObservedVariable, ProvenanceClass
from agri_contracts.models.crop_risk import CropRiskCandidateAlertEvent
from agri_risk_engine.risk.detectors import EWMADetector, RollingZScoreDetector
from agri_risk_engine.risk.fao56 import (
    calculate_composite_crop_stress_index,
    calculate_moisture_stress_threshold,
    calculate_raw,
    calculate_soil_moisture_stress_index,
    calculate_taw,
    calculate_thermal_stress_index,
    calculate_vpd_stress_index,
    evaluate_fungal_blast_risk_window,
)
from agri_risk_engine.risk.field_profile import FieldProfile


class DeterministicCropRiskEngine:
    """Evaluates crop water balance, heat stress, and fungal risk windows with contextual safety guardrails."""

    def __init__(self, rule_version: str = "1.0.0") -> None:
        self.rule_version = rule_version
        self.z_score_detector = RollingZScoreDetector(window_size=24, z_threshold=2.5)
        self.ewma_detector = EWMADetector(alpha=0.2, l_sigma=2.5)

    def evaluate_field_risk(
        self,
        field_profile: FieldProfile | None,
        event_time: datetime,
        temperature_c: float,
        relative_humidity_pct: float,
        soil_moisture_m3_m3: float | None = None,
        soil_moisture_provenance: ProvenanceClass = ProvenanceClass.PHYSICAL_SENSOR,
        precipitation_mm: float = 0.0,
        vpd_kpa: float | None = None,
        wind_speed_mps: float = 1.5,
        leaf_wetness_hours: float = 0.0,
        sensor_health_status: str = "HEALTHY",
        is_sensor_suppressed: bool = False,
        input_provenance: dict[str, str] | None = None,
    ) -> CropRiskCandidateAlertEvent:
        """Execute deterministic risk evaluation and return canonical candidate alert event."""
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)

        provenance_map = input_provenance or {
            "temperature": "physical_sensor",
            "relative_humidity": "physical_sensor",
            "soil_moisture": soil_moisture_provenance.value,
        }
        field_id = field_profile.field_id if field_profile else "field_unknown"

        # -------------------------------------------------------------------
        # Guardrail 1: Missing or Incomplete Field Profile (Mandatory Abstention)
        # -------------------------------------------------------------------
        if field_profile is None:
            return self._build_candidate_event(
                field_id=field_id,
                crop_name="Unknown Crop",
                growth_stage="unknown",
                risk_type="ABSTENTION_MISSING_CROP_PROFILE",
                risk_level=CropRiskLevel.NONE,
                csi=0.0,
                triggered_threshold="N/A",
                evidence="Field profile is entirely missing. Refusing to fabricate crop parameters per agronomic-safety rule.",
                event_time=event_time,
                is_suppressed=True,
                suppression_reason="ABSTAINED: Missing crop profile context. Cannot calculate water balance or thermal stress.",
                uncertainty_score=1.0,
                reason_codes=["ABSTAIN_MISSING_PROFILE"],
                sensor_health_status=sensor_health_status,
                provenance_map=provenance_map,
            )

        is_complete, missing_fields = field_profile.is_profile_complete()
        if not is_complete:
            return self._build_candidate_event(
                field_id=field_id,
                crop_name=field_profile.crop_name or "Unknown Crop",
                growth_stage=field_profile.growth_stage or "unknown",
                risk_type="ABSTENTION_INCOMPLETE_CROP_PROFILE",
                risk_level=CropRiskLevel.NONE,
                csi=0.0,
                triggered_threshold="N/A",
                evidence=f"Field profile lacks critical parameters: {missing_fields}. Refusing to fabricate defaults.",
                event_time=event_time,
                is_suppressed=True,
                suppression_reason=f"ABSTAINED: Incomplete profile ({missing_fields}). Cannot evaluate risk reliably.",
                uncertainty_score=0.95,
                reason_codes=["ABSTAIN_INCOMPLETE_PROFILE"],
                sensor_health_status=sensor_health_status,
                provenance_map=provenance_map,
            )

        # -------------------------------------------------------------------
        # Guardrail 2: Faulty or Untrusted Sensor Telemetry (Mandatory Suppression)
        # -------------------------------------------------------------------
        if is_sensor_suppressed or sensor_health_status in ("FAULTY", "STALE"):
            return self._build_candidate_event(
                field_id=field_id,
                crop_name=field_profile.crop_name,
                growth_stage=field_profile.growth_stage,
                risk_type="SUPPRESSED_UNRELIABLE_SENSOR_DATA",
                risk_level=CropRiskLevel.LOW,
                csi=0.0,
                triggered_threshold="SensorHealth == FAULTY/STALE",
                evidence=f"Underlying telemetry diagnosed with health state '{sensor_health_status}'. Risk recommendations blocked.",
                event_time=event_time,
                is_suppressed=True,
                suppression_reason=f"SUPPRESSED: Sensor diagnosed as {sensor_health_status}. Recommendation suppressed to prevent false alarm.",
                uncertainty_score=1.0,
                reason_codes=["SUPPRESSED_SENSOR_FAULT"],
                sensor_health_status=sensor_health_status,
                provenance_map=provenance_map,
            )

        # -------------------------------------------------------------------
        # Guardrail 3: Conflicting Telemetry Signals (Mandatory Abstention)
        # -------------------------------------------------------------------
        if precipitation_mm >= 10.0 and soil_moisture_m3_m3 is not None and soil_moisture_m3_m3 < 0.12:
            return self._build_candidate_event(
                field_id=field_id,
                crop_name=field_profile.crop_name,
                growth_stage=field_profile.growth_stage,
                risk_type="ABSTENTION_CONFLICTING_SIGNALS",
                risk_level=CropRiskLevel.LOW,
                csi=0.0,
                triggered_threshold="Precipitation >= 10mm but SoilMoisture < 0.12",
                evidence=f"Significant rain ({precipitation_mm:.1f}mm) contradicts critically low soil moisture ({soil_moisture_m3_m3:.3f}).",
                event_time=event_time,
                is_suppressed=True,
                suppression_reason="ABSTAINED: Conflicting environmental trends. Manual field inspection required.",
                uncertainty_score=0.85,
                reason_codes=["ABSTAIN_CONFLICTING_SIGNALS"],
                sensor_health_status=sensor_health_status,
                provenance_map=provenance_map,
            )

        # -------------------------------------------------------------------
        # Step 4: Deterministic Agronomic Calculations (FAO-56)
        # -------------------------------------------------------------------
        soil = field_profile.soil_profile
        stage = field_profile.stage_parameters

        # Calculate VPD if not pre-computed
        if vpd_kpa is None:
            # Tetens formulation
            es = 0.61078 * 2.71828 ** ((17.27 * temperature_c) / (temperature_c + 237.3))
            ea = es * (relative_humidity_pct / 100.0)
            vpd_kpa = round(max(0.0, es - ea), 3)

        # 1. Soil moisture stress & depletion fraction
        s_moisture = 0.0
        depletion_p = None
        if soil_moisture_m3_m3 is not None:
            s_moisture, depletion_p = calculate_soil_moisture_stress_index(
                current_sm=soil_moisture_m3_m3, soil=soil, stage_params=stage
            )

        # 2. Thermal stress index
        s_temp = calculate_thermal_stress_index(temp_c=temperature_c, stage_params=stage)

        # 3. Atmospheric VPD evaporative stress index
        s_vpd = calculate_vpd_stress_index(vpd_kpa=vpd_kpa, stage_params=stage)

        # 4. Composite Crop Stress Index
        csi = calculate_composite_crop_stress_index(
            s_moisture=s_moisture, s_vpd=s_vpd, s_temp=s_temp
        )

        # 5. Fungal disease susceptibility window
        blast_active, blast_reason = evaluate_fungal_blast_risk_window(
            temp_c=temperature_c,
            rh_pct=relative_humidity_pct,
            favorable_hours=leaf_wetness_hours,
        )

        # Statistical baseline detector metrics
        z_res = self.z_score_detector.evaluate(temperature_c)
        ewma_res = self.ewma_detector.evaluate(temperature_c)

        contributing_features = {
            "temperature_c": temperature_c,
            "relative_humidity_pct": relative_humidity_pct,
            "soil_moisture_m3_m3": soil_moisture_m3_m3,
            "soil_moisture_provenance": soil_moisture_provenance.value,
            "vpd_kpa": vpd_kpa,
            "precipitation_mm": precipitation_mm,
            "stress_moisture": s_moisture,
            "stress_temp": s_temp,
            "stress_vpd": s_vpd,
            "fao56_depletion_fraction": depletion_p,
            "fao56_threshold_sm": calculate_moisture_stress_threshold(soil, stage.depletion_fraction_p),
            "z_score_anomaly": z_res.is_anomaly,
            "ewma_anomaly": ewma_res.is_anomaly,
        }

        # -------------------------------------------------------------------
        # Step 5: Risk Severity & Category Assignment
        # -------------------------------------------------------------------
        reason_codes: list[str] = []
        is_suppressed = False
        suppression_reason = None

        if blast_active:
            risk_type = "FUNGAL_DISEASE_WINDOW"
            risk_level = CropRiskLevel.HIGH
            triggered_threshold = "Temp in [20, 28]°C and RH >= 85% for >= 6 hours"
            evidence = blast_reason
            reason_codes.append("RISK_BLAST_SUSCEPTIBILITY_WINDOW")
        elif s_temp >= 0.70 or temperature_c >= stage.t_heat_critical_c:
            risk_type = "HEAT_STRESS"
            risk_level = CropRiskLevel.HIGH if temperature_c < 36.0 else CropRiskLevel.CRITICAL
            triggered_threshold = f"Temperature ({temperature_c:.1f}°C) >= Critical Heat Limit ({stage.t_heat_critical_c:.1f}°C)"
            evidence = f"Flowering ragi heat stress: floret sterility risk at {temperature_c:.1f}°C (exceeds {stage.t_heat_critical_c}°C limit)."
            reason_codes.append("RISK_FLORET_HEAT_STERILITY")
        elif s_moisture >= 0.50:
            risk_type = "SOIL_MOISTURE_DEFICIT"
            risk_level = CropRiskLevel.CRITICAL if s_moisture >= 0.85 else CropRiskLevel.HIGH
            dep_pct = round((depletion_p or 0.0) * 100, 1)
            triggered_threshold = f"Root-zone SM ({soil_moisture_m3_m3:.3f}) below RAW threshold (depletion {dep_pct}%)"
            evidence = f"Soil moisture deficit: available water depleted to {dep_pct}%, inducing transpiration reduction."
            reason_codes.append("RISK_ROOT_ZONE_MOISTURE_DEFICIT")
        elif csi >= 0.60:
            risk_type = "COMPOSITE_CROP_STRESS"
            risk_level = CropRiskLevel.MEDIUM
            triggered_threshold = "Composite Crop Stress Index (CSI) >= 0.60"
            evidence = f"Elevated multi-factor stress: CSI={csi:.2f} (Soil={s_moisture:.2f}, VPD={s_vpd:.2f}, Temp={s_temp:.2f})."
            reason_codes.append("RISK_ELEVATED_COMPOSITE_STRESS")
        else:
            # Baseline normal conditions
            risk_type = "NO_ACUTE_STRESS"
            risk_level = CropRiskLevel.NONE
            triggered_threshold = "CSI < 0.60 and all environmental factors within optimal ranges"
            evidence = f"Crop conditions optimal. CSI={csi:.2f}, Soil moisture within RAW buffer."
            is_suppressed = True
            suppression_reason = "No acute agronomic risk detected. Alert suppressed from farmer notification."
            reason_codes.append("NORMAL_OPTIMAL_CONDITIONS")

        # Uncertainty calculation: 0.10 for direct physical probe, 0.35 if soil moisture is modelled reanalysis
        uncertainty = 0.10
        if soil_moisture_provenance == ProvenanceClass.MODELLED_REANALYSIS:
            uncertainty += 0.25

        return self._build_candidate_event(
            field_id=field_id,
            crop_name=field_profile.crop_name,
            growth_stage=field_profile.growth_stage,
            risk_type=risk_type,
            risk_level=risk_level,
            csi=csi,
            triggered_threshold=triggered_threshold,
            evidence=evidence,
            event_time=event_time,
            is_suppressed=is_suppressed,
            suppression_reason=suppression_reason,
            uncertainty_score=uncertainty,
            reason_codes=reason_codes,
            sensor_health_status=sensor_health_status,
            provenance_map=provenance_map,
            current_sm=soil_moisture_m3_m3,
            current_temp=temperature_c,
            current_vpd=vpd_kpa,
            depletion_p=depletion_p,
            contributing_features=contributing_features,
        )

    def _build_candidate_event(
        self,
        field_id: str,
        crop_name: str,
        growth_stage: str,
        risk_type: str,
        risk_level: CropRiskLevel,
        csi: float,
        triggered_threshold: str,
        evidence: str,
        event_time: datetime,
        is_suppressed: bool,
        suppression_reason: str | None,
        uncertainty_score: float,
        reason_codes: list[str],
        sensor_health_status: str,
        provenance_map: dict[str, str],
        current_sm: float | None = None,
        current_temp: float | None = None,
        current_vpd: float | None = None,
        depletion_p: float | None = None,
        contributing_features: dict[str, Any] | None = None,
    ) -> CropRiskCandidateAlertEvent:
        return CropRiskCandidateAlertEvent(
            event_id=str(uuid.uuid4()),
            alert_id=str(uuid.uuid4()),
            schema_version="1.0.0",
            event_time=event_time,
            ingestion_time=datetime.now(timezone.utc),
            field_id=field_id,
            idempotency_key=f"risk:{field_id}:{risk_type}:{int(event_time.timestamp())}",
            crop_name=crop_name,
            growth_stage=growth_stage,
            risk_type=risk_type,
            risk_level=risk_level,
            composite_stress_index=csi,
            soil_depletion_fraction=depletion_p,
            current_soil_moisture_m3_m3=current_sm,
            current_temperature_c=current_temp,
            current_vpd_kpa=current_vpd,
            triggered_threshold=triggered_threshold,
            evidence_summary=evidence,
            rule_version=self.rule_version,
            contributing_features=contributing_features or {},
            sensor_health_status=sensor_health_status,
            reason_codes=reason_codes,
            uncertainty_score=uncertainty_score,
            input_provenance=provenance_map,
            is_suppressed=is_suppressed,
            suppression_reason=suppression_reason,
            provenance={
                "provenance_class": ProvenanceClass.DERIVED,
                "dataset_origin": "DeterministicCropRiskEngine",
                "is_synthetic": False,
            },
        )

