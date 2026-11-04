"""FastAPI dependency injection providers for database repository, supervisor, and auth."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import Depends

from agri_api.auth import AuthenticatedUser, get_current_user
from agri_investigator.supervisor import MultiAgentSupervisor

logger = logging.getLogger(__name__)

# Start timestamp for uptime calculation
START_TIME = time.time()

# Mock in-memory store for offline development/testing when PostgreSQL is not running
_STATIC_FIELD_PROFILES: Dict[str, Dict[str, Any]] = {
    "field-kolar-001": {
        "field_id": "field-kolar-001",
        "name": "Kolar North Parcel - Finger Millet Demonstration",
        "latitude": 13.1333,
        "longitude": 78.1333,
        "elevation_m": 822.0,
        "crop_name": "finger_millet",
        "variety": "GPU-28",
        "sowing_date": "2026-07-15",
        "expected_harvest_date": "2026-11-20",
        "current_growth_stage": "flowering",
        "soil_type": "red_sandy_loam",
        "soil_texture": "sandy_clay_loam",
        "field_capacity": 0.22,
        "wilting_point": 0.10,
        "root_zone_depth_m": 0.50,
        "irrigation_type": "rainfed",
        "is_active": True,
        "metadata": {"zone": "Karnataka Zone 5", "taluk": "Kolar", "soil_depth_cm": 60},
        "created_at": "2026-07-15T00:00:00Z",
        "updated_at": "2026-11-04T12:00:00Z",
    },
    "field-demo-parcel": {
        "field_id": "field-demo-parcel",
        "name": "Sarvamangalam Test Farm",
        "latitude": 12.0000,
        "longitude": 79.8000,
        "elevation_m": 45.0,
        "crop_name": "finger_millet",
        "variety": "GPU-28",
        "sowing_date": "2026-08-01",
        "expected_harvest_date": "2026-12-05",
        "current_growth_stage": "vegetative",
        "soil_type": "red_sandy_loam",
        "soil_texture": "sandy_clay_loam",
        "field_capacity": 0.22,
        "wilting_point": 0.10,
        "root_zone_depth_m": 0.40,
        "irrigation_type": "protective_drip",
        "is_active": True,
        "metadata": {"station": "openSenseMap_Sarvamangalam"},
        "created_at": "2026-08-01T00:00:00Z",
        "updated_at": "2026-11-04T12:00:00Z",
    },
}

_MOCK_INVESTIGATIONS: Dict[str, Dict[str, Any]] = {}
_MOCK_RECOMMENDATIONS: Dict[str, Dict[str, Any]] = {}
_MOCK_FEEDBACK: List[Dict[str, Any]] = []
_MOCK_DISPATCHES: Dict[str, Dict[str, Any]] = {}
_MOCK_AUDIT_LOG: List[Dict[str, Any]] = []


class LocalMemoryRepository:
    """Fallback repository for offline standalone API execution and unit testing."""

    def __init__(self) -> None:
        self.fields = dict(_STATIC_FIELD_PROFILES)
        self.investigations = _MOCK_INVESTIGATIONS
        self.recommendations = _MOCK_RECOMMENDATIONS
        self.feedback = _MOCK_FEEDBACK
        self.dispatches = _MOCK_DISPATCHES
        self.audit = _MOCK_AUDIT_LOG

    def get_field_profile(self, field_id: str) -> Optional[Dict[str, Any]]:
        return self.fields.get(field_id)

    def list_field_profiles(self, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
        if is_active is None:
            return list(self.fields.values())
        return [f for f in self.fields.values() if f.get("is_active") == is_active]

    def upsert_field_profile(self, profile: Dict[str, Any]) -> bool:
        self.fields[profile["field_id"]] = profile
        return True

    def get_field_observations(self, field_id: str, variable: Optional[str] = None, hours: int = 24, limit: int = 100):
        # Return representative dryland telemetry
        obs = [
            {"event_time": "2026-11-04T12:00:00Z", "sensor_id": "soil-01", "observed_variable": "soil_moisture", "numeric_value": 0.12, "unit": "m3/m3", "provenance": "physical_sensor", "quality_flags": []},
            {"event_time": "2026-11-04T12:00:00Z", "sensor_id": "temp-01", "observed_variable": "ambient_temp", "numeric_value": 31.8, "unit": "celsius", "provenance": "physical_sensor", "quality_flags": []},
            {"event_time": "2026-11-04T11:45:00Z", "sensor_id": "soil-01", "observed_variable": "soil_moisture", "numeric_value": 0.13, "unit": "m3/m3", "provenance": "physical_sensor", "quality_flags": []},
        ]
        if variable:
            obs = [o for o in obs if o["observed_variable"] == variable]
        return obs[:limit]

    def get_sensor_freshness(self, field_id: Optional[str] = None):
        return [
            {
                "sensor_id": "soil-probe-01",
                "field_id": field_id or "field-kolar-001",
                "sensor_model": "Capacitance-VH400",
                "measured_variable": "soil_moisture",
                "unit": "m3/m3",
                "provenance_type": "physical_sensor",
                "last_event_time": "2026-11-04T12:00:00Z",
                "last_value": 0.12,
                "latency_seconds": 18.4,
                "health_state": "HEALTHY",
                "reason_code": "ALL_SENSORS_VALID",
            },
            {
                "sensor_id": "sarvamangalam-osm-temp",
                "field_id": field_id or "field-kolar-001",
                "sensor_model": "openSenseMap-Station",
                "measured_variable": "ambient_temp",
                "unit": "celsius",
                "provenance_type": "physical_sensor",
                "last_event_time": "2026-11-04T12:00:00Z",
                "last_value": 31.8,
                "latency_seconds": 22.1,
                "health_state": "HEALTHY",
                "reason_code": "ALL_SENSORS_VALID",
            },
        ]

    def get_field_sensor_health(self, field_id: str, hours: int = 24, limit: int = 50):
        return [
            {
                "event_time": "2026-11-04T12:00:00Z",
                "sensor_id": "soil-probe-01",
                "health_state": "HEALTHY",
                "reason_code": "ALL_SENSORS_VALID",
                "metrics": {"flatline_window": 0, "z_score": 0.2},
                "diagnostics": {"status": "ok"},
                "exemption_type": None,
            }
        ]

    def list_recent_alerts(self, field_id: Optional[str] = None, hours: int = 72, limit: int = 50):
        return [
            {
                "alert_id": "c1a4169f-48bd-494d-a2e0-32c3f2e9688a",
                "field_id": field_id or "field-kolar-001",
                "event_time": "2026-11-04T11:55:00Z",
                "alert_type": "SOIL_MOISTURE_DEPLETION",
                "severity": "HIGH",
                "status": "CANDIDATE",
                "composite_stress_index": 0.76,
                "fao56_depletion_fraction": 0.65,
                "blast_risk_score": 0.12,
                "thermal_stress_score": 0.35,
                "sensor_health_state": "HEALTHY",
                "uncertainty_score": 0.15,
                "contributing_features": [{"feature_name": "soil_moisture_depletion", "severity": "HIGH"}],
                "evidence": {"soil_moisture": 0.12, "threshold": 0.166},
                "suppression_reason": None,
            }
        ]

    def get_alert_by_id(self, alert_id: str):
        alerts = self.list_recent_alerts()
        for a in alerts:
            if a["alert_id"] == alert_id:
                return a
        # Return fallback
        return {
            "alert_id": alert_id,
            "field_id": "field-kolar-001",
            "event_time": "2026-11-04T11:55:00Z",
            "alert_type": "SOIL_MOISTURE_DEPLETION",
            "severity": "HIGH",
            "status": "CANDIDATE",
            "composite_stress_index": 0.76,
            "fao56_depletion_fraction": 0.65,
            "blast_risk_score": 0.12,
            "thermal_stress_score": 0.35,
            "sensor_health_state": "HEALTHY",
            "uncertainty_score": 0.15,
            "contributing_features": [{"feature_name": "soil_moisture_depletion", "severity": "HIGH"}],
            "evidence": {"soil_moisture": 0.12, "threshold": 0.166},
            "suppression_reason": None,
        }

    def create_multi_agent_run(self, run: Dict[str, Any]) -> str:
        self.investigations[run["run_id"]] = run
        return run["run_id"]

    def update_multi_agent_run(self, run_id: str, updates: Dict[str, Any]) -> bool:
        if run_id in self.investigations:
            self.investigations[run_id].update(updates)
            return True
        return False

    def get_multi_agent_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self.investigations.get(run_id)

    def record_agent_message(self, msg: Dict[str, Any]) -> str:
        run_id = msg["run_id"]
        if run_id not in self.investigations:
            self.investigations[run_id] = {"transitions": [], "messages": []}
        if "messages" not in self.investigations[run_id]:
            self.investigations[run_id]["messages"] = []
        self.investigations[run_id]["messages"].append(msg)
        return msg["message_id"]

    def record_state_transition(self, transition: Dict[str, Any]) -> int:
        run_id = transition["run_id"]
        if run_id not in self.investigations:
            self.investigations[run_id] = {"transitions": [], "messages": []}
        if "transitions" not in self.investigations[run_id]:
            self.investigations[run_id]["transitions"] = []
        self.investigations[run_id]["transitions"].append(transition)
        return len(self.investigations[run_id]["transitions"])

    def get_run_messages(self, run_id: str) -> List[Dict[str, Any]]:
        return self.investigations.get(run_id, {}).get("messages", [])

    def get_run_state_transitions(self, run_id: str) -> List[Dict[str, Any]]:
        return self.investigations.get(run_id, {}).get("transitions", [])

    def create_farmer_recommendation(self, rec: Dict[str, Any]) -> str:
        self.recommendations[rec["recommendation_id"]] = rec
        return rec["recommendation_id"]

    def get_recommendation_by_id(self, recommendation_id: str) -> Optional[Dict[str, Any]]:
        return self.recommendations.get(recommendation_id)

    def list_farmer_recommendations(self, field_id: Optional[str] = None, approval_status: Optional[str] = None, limit: int = 50):
        recs = list(self.recommendations.values())
        if field_id:
            recs = [r for r in recs if r.get("field_id") == field_id]
        if approval_status:
            recs = [r for r in recs if r.get("approval_status") == approval_status]
        return recs[:limit]

    def update_recommendation_status(self, recommendation_id: str, status: str, approved_by: str) -> bool:
        if recommendation_id in self.recommendations:
            self.recommendations[recommendation_id]["approval_status"] = status
            self.recommendations[recommendation_id]["approved_by"] = approved_by
            return True
        return False

    def record_human_feedback(self, feedback: Dict[str, Any]) -> str:
        self.feedback.append(feedback)
        return str(feedback["feedback_id"])

    def get_feedback_by_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        for fb in self.feedback:
            if fb.get("idempotency_key") == idempotency_key:
                return fb
        return None

    def list_human_feedback(self, field_id: Optional[str] = None, limit: int = 50):
        if field_id:
            return [f for f in self.feedback if f.get("field_id") == field_id][:limit]
        return self.feedback[:limit]

    def create_notification_dispatch(self, dispatch: Dict[str, Any]) -> str:
        d_id = dispatch["dispatch_id"]
        self.dispatches[d_id] = dispatch
        return d_id

    def get_notification_dispatch_by_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        for d in self.dispatches.values():
            if d.get("idempotency_key") == idempotency_key:
                return d
        return None

    def list_notification_dispatches(
        self, recipient_id: Optional[str] = None, status: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        results = list(self.dispatches.values())
        if recipient_id:
            results = [d for d in results if d.get("recipient_id") == recipient_id]
        if status:
            results = [d for d in results if d.get("status") == status]
        return results[:limit]

    def record_system_audit(self, action: str, actor: str, entity_type: str, entity_id: str, details: Dict[str, Any]) -> int:
        entry = {
            "audit_id": len(self.audit) + 1,
            "action": action,
            "actor": actor,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details,
            "created_at": time.time(),
        }
        self.audit.append(entry)
        return entry["audit_id"]


# Singleton repository instance
_REPO_INSTANCE: Optional[Any] = None


def get_repository() -> Any:
    """Returns real TimescaleDB PersistenceRepository if pool connects, else LocalMemoryRepository."""
    global _REPO_INSTANCE
    if _REPO_INSTANCE is None:
        import sys
        if os.getenv("AGRI_ENV") == "test" or os.getenv("USE_MOCK_REPO") == "1" or "pytest" in sys.modules:
            logger.info("Using LocalMemoryRepository for testing/mock environment.")
            _REPO_INSTANCE = LocalMemoryRepository()
            return _REPO_INSTANCE
        try:
            from agri_persistence.pool import DatabasePoolManager
            from agri_persistence.repository import PersistenceRepository
            pool_mgr = DatabasePoolManager()
            if pool_mgr.check_health():
                logger.info("Connected to TimescaleDB persistence pool.")
                _REPO_INSTANCE = PersistenceRepository(pool_mgr)
            else:
                logger.warning("TimescaleDB health check failed; using LocalMemoryRepository.")
                _REPO_INSTANCE = LocalMemoryRepository()
        except Exception as e:
            logger.info("Initializing LocalMemoryRepository fallback: %s", e)
            _REPO_INSTANCE = LocalMemoryRepository()
    return _REPO_INSTANCE


# Singleton supervisor instance
_SUPERVISOR_INSTANCE: Optional[MultiAgentSupervisor] = None


def get_supervisor(repo: Any = Depends(get_repository)) -> MultiAgentSupervisor:
    """Provides MultiAgentSupervisor initialized with repository and Stage 15 RAG."""
    global _SUPERVISOR_INSTANCE
    if _SUPERVISOR_INSTANCE is None:
        repo_root = Path(__file__).resolve().parents[4]
        chroma_dir = repo_root / "knowledge" / "chroma_db"
        _SUPERVISOR_INSTANCE = MultiAgentSupervisor(
            persistence_repo=repo,
            max_revisions=2,
            chroma_dir=chroma_dir if chroma_dir.exists() else None,
        )
    return _SUPERVISOR_INSTANCE
