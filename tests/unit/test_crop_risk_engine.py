"""Unit tests for deterministic crop risk formulations, FAO-56 water balance, and detector baselines."""

import pytest

from agri_contracts.enums import CropRiskLevel
from agri_risk_engine.risk import (
    EWMADetector,
    IsolationForestDetector,
    RollingZScoreDetector,
    calculate_composite_crop_stress_index,
    calculate_moisture_stress_threshold,
    calculate_raw,
    calculate_reference_et0_hargreaves,
    calculate_soil_moisture_stress_index,
    calculate_taw,
    calculate_thermal_stress_index,
    calculate_vpd_stress_index,
    evaluate_fungal_blast_risk_window,
    get_kolar_red_sandy_loam_soil,
    get_ragi_flowering_stage_params,
    get_verified_kolar_ragi_profile,
)
from agri_risk_engine.risk.field_profile import FieldProfile


# ===========================================================================
# 1. FAO-56 Water Balance & Stress Math Tests
# ===========================================================================

class TestFAO56WaterBalanceMath:
    """Verify physical water balance formulations against FAO-56 and UAS Bangalore specifications."""

    def setup_method(self) -> None:
        self.soil = get_kolar_red_sandy_loam_soil()  # FC=0.22, WP=0.10
        self.stage = get_ragi_flowering_stage_params()  # Zr=0.50m, p=0.45

    def test_total_and_readily_available_water(self) -> None:
        # AWC = 0.22 - 0.10 = 0.12 m3/m3
        # TAW = 1000 * 0.12 * 0.50 = 60.0 mm
        taw = calculate_taw(self.soil, self.stage.root_depth_m)
        assert pytest.approx(taw, abs=0.1) == 60.0

        # RAW = 0.45 * 60.0 = 27.0 mm
        raw = calculate_raw(taw, self.stage.depletion_fraction_p)
        assert pytest.approx(raw, abs=0.1) == 27.0

    def test_soil_moisture_stress_threshold(self) -> None:
        # theta_threshold = 0.10 + (1 - 0.45) * (0.22 - 0.10) = 0.10 + 0.55 * 0.12 = 0.166 m3/m3
        threshold = calculate_moisture_stress_threshold(self.soil, self.stage.depletion_fraction_p)
        assert pytest.approx(threshold, abs=1e-3) == 0.166

    def test_moisture_stress_progression(self) -> None:
        # At Field Capacity (0.22): zero stress, zero depletion
        s_fc, dep_fc = calculate_soil_moisture_stress_index(0.22, self.soil, self.stage)
        assert s_fc == 0.0
        assert dep_fc == 0.0

        # Above threshold (0.18 > 0.166): zero stress, partial depletion
        s_mid, dep_mid = calculate_soil_moisture_stress_index(0.18, self.soil, self.stage)
        assert s_mid == 0.0
        assert dep_mid > 0.0

        # At Wilting Point (0.10): maximum stress (1.0)
        s_wp, dep_wp = calculate_soil_moisture_stress_index(0.10, self.soil, self.stage)
        assert s_wp == 1.0
        assert dep_wp == 1.0

        # Below Wilting Point (0.08 residual): clamped to 1.0
        s_sub, dep_sub = calculate_soil_moisture_stress_index(0.08, self.soil, self.stage)
        assert s_sub == 1.0
        assert dep_sub == 1.0

    def test_thermal_stress_index(self) -> None:
        # Optimal temperature (26.0°C <= 30.0°C): zero stress
        s_opt = calculate_thermal_stress_index(26.0, self.stage)
        assert s_opt == 0.0

        # Moderate heat stress (32.0°C between 30°C and 34°C)
        s_mod = calculate_thermal_stress_index(32.0, self.stage)
        assert 0.0 < s_mod < 0.6

        # Critical floret sterility heat stress (35.0°C >= 34°C)
        s_crit = calculate_thermal_stress_index(35.0, self.stage)
        assert s_crit >= 0.6

    def test_vpd_stress_index(self) -> None:
        # Optimal evaporative demand (1.0 kPa <= 1.2 kPa): zero stress
        assert calculate_vpd_stress_index(1.0, self.stage) == 0.0

        # Critical evaporative demand (3.2 kPa >= 2.8 kPa): maximum stress
        assert calculate_vpd_stress_index(3.2, self.stage) == 1.0

    def test_composite_crop_stress_index_calculation(self) -> None:
        # CSI = 0.5 * 0.8 + 0.3 * 0.5 + 0.2 * 0.6 = 0.40 + 0.15 + 0.12 = 0.67
        csi = calculate_composite_crop_stress_index(s_moisture=0.8, s_vpd=0.5, s_temp=0.6)
        assert pytest.approx(csi, abs=1e-2) == 0.67

    def test_fungal_blast_risk_window_conditions(self) -> None:
        # Optimal conditions (24°C, 90% RH for 8 hours): triggers environmental risk window
        active, reason = evaluate_fungal_blast_risk_window(temp_c=24.0, rh_pct=90.0, favorable_hours=8.0)
        assert active is True
        assert "spore germination" in reason
        assert "Environmental risk window only" in reason  # Mandatory disclaimer

        # Insufficient duration (3 hours < 6 hours): does not trigger
        active_short, _ = evaluate_fungal_blast_risk_window(temp_c=24.0, rh_pct=90.0, favorable_hours=3.0)
        assert active_short is False

        # Incompatible temperature (35°C): too hot for blast germination
        active_hot, _ = evaluate_fungal_blast_risk_window(temp_c=35.0, rh_pct=90.0, favorable_hours=8.0)
        assert active_hot is False


# ===========================================================================
# 2. Field Profile Completeness & Grounding Tests
# ===========================================================================

class TestFieldProfileGrounding:
    """Verify field profile model and mandatory abstention on missing context."""

    def test_verified_reference_profile_is_complete(self) -> None:
        profile = get_verified_kolar_ragi_profile()
        is_complete, missing = profile.is_profile_complete()
        assert is_complete is True
        assert len(missing) == 0
        assert profile.crop_name == "Finger Millet (Ragi)"
        assert profile.variety == "GPU-28"
        assert profile.soil_profile.field_capacity == 0.22

    def test_incomplete_profile_identifies_missing_fields(self) -> None:
        # Profile without soil and stage parameters
        incomplete = FieldProfile(
            field_id="field_kolar_sparse",
            crop_name="Finger Millet (Ragi)",
            growth_stage=None,
            soil_profile=None,
            stage_parameters=None,
        )
        is_complete, missing = incomplete.is_profile_complete()
        assert is_complete is False
        assert "growth_stage" in missing
        assert "soil_profile" in missing
        assert "stage_parameters" in missing


# ===========================================================================
# 3. Detector Candidate Comparison (Z-Score, EWMA, Isolation Forest)
# ===========================================================================

class TestDetectorCandidatesComparison:
    """Evaluate EWMA, rolling Z-score, and Isolation Forest on controlled fixtures."""

    def test_detectors_on_normal_and_spike_series(self) -> None:
        z_det = RollingZScoreDetector(window_size=20, z_threshold=2.5)
        ewma_det = EWMADetector(alpha=0.2, l_sigma=2.5)
        iforest = IsolationForestDetector(contamination=0.05, n_estimators=30)

        # 1. Warm up with normal temperature readings (24 - 28°C)
        normal_series = [24.0, 24.5, 25.0, 25.5, 26.0, 26.5, 27.0, 27.2, 27.5, 27.1, 26.8, 26.2, 25.5, 25.0, 24.8, 24.5, 24.2, 24.5, 25.0, 25.5]
        training_vectors = [[t, 70.0, 1.2, 0.20] for t in normal_series]
        iforest.fit(training_vectors)

        for val in normal_series:
            z_res = z_det.evaluate(val)
            ewma_res = ewma_det.evaluate(val)

        # Baseline series should not trigger anomaly
        assert z_res.is_anomaly is False
        assert ewma_res.is_anomaly is False

        # 2. Inject acute thermal anomaly (44.0°C)
        spike_val = 44.0
        z_spike = z_det.evaluate(spike_val)
        ewma_spike = ewma_det.evaluate(spike_val)
        if_spike = iforest.evaluate([spike_val, 30.0, 4.5, 0.12])

        # Both streaming detectors cleanly identify the spike
        assert z_spike.is_anomaly is True
        assert ewma_spike.is_anomaly is True
        assert z_spike.anomaly_score > 3.0
        assert ewma_spike.anomaly_score > 3.0
        assert z_spike.latency_microseconds < 100.0  # Ultra-low sub-millisecond latency
        assert ewma_spike.latency_microseconds < 100.0

