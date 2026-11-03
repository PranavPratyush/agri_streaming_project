"""Data Access Object (Repository) for AgriKafka-Agent persistence layer.

Provides safe, idempotent upsert operations and analytical query executions.
Strictly separates event_time from ingestion_time.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

try:
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:
    psycopg = None  # type: ignore
    Jsonb = None  # type: ignore

from agri_contracts.models.observation import AgriObservationEvent
from agri_contracts.models.sensor_health import SensorHealthResultEvent
from agri_contracts.models.crop_risk import CropRiskCandidateAlertEvent
from agri_persistence.pool import DatabasePoolManager

logger = logging.getLogger(__name__)


def _to_jsonb(data: Any) -> Any:
    """Helper to convert dictionaries or lists to Psycopg Jsonb adapter."""
    if data is None:
        data = {}
    if Jsonb is not None:
        return Jsonb(data)
    return json.dumps(data)


def _to_iso_utc(dt: Any) -> Optional[datetime]:
    """Ensures datetime object has timezone awareness set to UTC."""
    if dt is None:
        return None
    if isinstance(dt, str):
        # Handle string parsing if passed
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    return dt


class PersistenceRepository:
    """Repository handling all database persistence operations."""

    def __init__(self, pool_manager: DatabasePoolManager) -> None:
        self.pool = pool_manager

    # =========================================================================
    # 1. Relational Entities (Field Profiles, Sensors)
    # =========================================================================

    def upsert_field_profile(self, profile: Dict[str, Any]) -> bool:
        """Upserts a field profile entity."""
        query = """
        INSERT INTO field_profiles (
            field_id, name, latitude, longitude, elevation_m, crop_name, variety,
            sowing_date, expected_harvest_date, current_growth_stage, soil_type,
            soil_texture, field_capacity, wilting_point, root_zone_depth_m,
            irrigation_type, is_active, metadata, updated_at
        ) VALUES (
            %(field_id)s, %(name)s, %(latitude)s, %(longitude)s, %(elevation_m)s, %(crop_name)s, %(variety)s,
            %(sowing_date)s, %(expected_harvest_date)s, %(current_growth_stage)s, %(soil_type)s,
            %(soil_texture)s, %(field_capacity)s, %(wilting_point)s, %(root_zone_depth_m)s,
            %(irrigation_type)s, %(is_active)s, %(metadata)s, now()
        )
        ON CONFLICT (field_id) DO UPDATE SET
            current_growth_stage = EXCLUDED.current_growth_stage,
            root_zone_depth_m = EXCLUDED.root_zone_depth_m,
            irrigation_type = EXCLUDED.irrigation_type,
            is_active = EXCLUDED.is_active,
            metadata = EXCLUDED.metadata,
            updated_at = now();
        """
        params = {
            "field_id": profile["field_id"],
            "name": profile.get("name", profile["field_id"]),
            "latitude": float(profile["latitude"]),
            "longitude": float(profile["longitude"]),
            "elevation_m": profile.get("elevation_m"),
            "crop_name": profile.get("crop_name", "finger_millet"),
            "variety": profile.get("variety", "GPU-28"),
            "sowing_date": profile["sowing_date"],
            "expected_harvest_date": profile.get("expected_harvest_date"),
            "current_growth_stage": profile.get("current_growth_stage", "flowering"),
            "soil_type": profile.get("soil_type", "red_sandy_loam"),
            "soil_texture": profile.get("soil_texture", "sandy_clay_loam"),
            "field_capacity": float(profile.get("field_capacity", 0.22)),
            "wilting_point": float(profile.get("wilting_point", 0.10)),
            "root_zone_depth_m": float(profile.get("root_zone_depth_m", 0.50)),
            "irrigation_type": profile.get("irrigation_type", "rainfed"),
            "is_active": profile.get("is_active", True),
            "metadata": _to_jsonb(profile.get("metadata", {})),
        }

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                return cur.rowcount > 0

    def upsert_sensor_metadata(self, sensor: Dict[str, Any]) -> bool:
        """Upserts a sensor metadata entity."""
        query = """
        INSERT INTO sensor_metadata (
            sensor_id, field_id, sensor_model, manufacturer, measured_variable,
            unit, installation_date, depth_m, sampling_interval_seconds,
            provenance_type, is_active, metadata, updated_at
        ) VALUES (
            %(sensor_id)s, %(field_id)s, %(sensor_model)s, %(manufacturer)s, %(measured_variable)s,
            %(unit)s, %(installation_date)s, %(depth_m)s, %(sampling_interval_seconds)s,
            %(provenance_type)s, %(is_active)s, %(metadata)s, now()
        )
        ON CONFLICT (sensor_id) DO UPDATE SET
            is_active = EXCLUDED.is_active,
            sampling_interval_seconds = EXCLUDED.sampling_interval_seconds,
            metadata = EXCLUDED.metadata,
            updated_at = now();
        """
        params = {
            "sensor_id": sensor["sensor_id"],
            "field_id": sensor["field_id"],
            "sensor_model": sensor.get("sensor_model", "Standard-Sensor"),
            "manufacturer": sensor.get("manufacturer"),
            "measured_variable": sensor["measured_variable"],
            "unit": sensor["unit"],
            "installation_date": sensor.get("installation_date"),
            "depth_m": sensor.get("depth_m"),
            "sampling_interval_seconds": int(sensor.get("sampling_interval_seconds", 300)),
            "provenance_type": sensor.get("provenance_type", "physical_sensor"),
            "is_active": sensor.get("is_active", True),
            "metadata": _to_jsonb(sensor.get("metadata", {})),
        }

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                return cur.rowcount > 0

    # =========================================================================
    # 2. Time-Series Hypertables (Idempotent Insert Operations)
    # =========================================================================

    def upsert_observation(self, obs: AgriObservationEvent | Dict[str, Any]) -> bool:
        """Inserts an observation into the hypertable.

        Enforces idempotency using ON CONFLICT (idempotency_key, event_time) DO NOTHING.
        Returns True if a new row was inserted, False if skipped due to existing duplicate.
        """
        if isinstance(obs, AgriObservationEvent):
            d = obs.model_dump()
        else:
            d = obs

        query = """
        INSERT INTO observations (
            idempotency_key, event_id, event_time, ingestion_time, field_id, sensor_id,
            source_provider, source_type, observed_variable, numeric_value, unit,
            latitude, longitude, elevation, sensor_depth_m, provenance, quality_flags, metadata
        ) VALUES (
            %(idempotency_key)s, %(event_id)s, %(event_time)s, %(ingestion_time)s, %(field_id)s, %(sensor_id)s,
            %(source_provider)s, %(source_type)s, %(observed_variable)s, %(numeric_value)s, %(unit)s,
            %(latitude)s, %(longitude)s, %(elevation)s, %(sensor_depth_m)s, %(provenance)s, %(quality_flags)s, %(metadata)s
        )
        ON CONFLICT (idempotency_key, event_time) DO NOTHING;
        """

        loc = d.get("location") or {}
        placement = d.get("sensor_placement") or {}
        q_flags = d.get("quality_flags") or {}
        prov = d.get("provenance") or {}

        observed_var = str(d.get("variable") or d.get("observed_variable"))
        num_val = float(d.get("value") if d.get("value") is not None else d.get("numeric_value", 0.0))
        unit_val = str(d.get("unit"))
        source_prov = d.get("source_provider", "unknown")
        src_type = str(prov.get("provenance_class") or d.get("source_type", "physical_sensor"))
        provenance_str = str(prov.get("provenance_class") or d.get("provenance", "physical_sensor"))

        params = {
            "idempotency_key": d["idempotency_key"],
            "event_id": str(d["event_id"]),
            "event_time": _to_iso_utc(d["event_time"]),
            "ingestion_time": _to_iso_utc(d.get("ingestion_time", d["event_time"])),
            "field_id": d["field_id"],
            "sensor_id": d.get("sensor_id") or "unspecified",
            "source_provider": source_prov,
            "source_type": src_type,
            "observed_variable": observed_var,
            "numeric_value": num_val,
            "unit": unit_val,
            "latitude": float(loc.get("latitude")) if loc.get("latitude") is not None else None,
            "longitude": float(loc.get("longitude")) if loc.get("longitude") is not None else None,
            "elevation": float(loc.get("elevation")) if loc.get("elevation") is not None else None,
            "sensor_depth_m": float(placement.get("depth_cm", 0) / 100.0) if placement.get("depth_cm") is not None else placement.get("depth_m"),
            "provenance": provenance_str,
            "quality_flags": _to_jsonb(q_flags),
            "metadata": _to_jsonb(d.get("metadata", {})),
        }

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                return cur.rowcount > 0

    def upsert_windowed_feature(self, feature: Dict[str, Any]) -> bool:
        """Upserts an aggregated window feature (5-min tumbling or 30-min sliding)."""
        query = """
        INSERT INTO windowed_features (
            feature_id, field_id, window_start, window_end, window_type, feature_name,
            feature_value, unit, sample_count, min_value, max_value, std_dev
        ) VALUES (
            %(feature_id)s, %(field_id)s, %(window_start)s, %(window_end)s, %(window_type)s, %(feature_name)s,
            %(feature_value)s, %(unit)s, %(sample_count)s, %(min_value)s, %(max_value)s, %(std_dev)s
        )
        ON CONFLICT (field_id, feature_name, window_start, window_type)
        DO UPDATE SET
            feature_value = EXCLUDED.feature_value,
            sample_count = EXCLUDED.sample_count,
            min_value = EXCLUDED.min_value,
            max_value = EXCLUDED.max_value,
            std_dev = EXCLUDED.std_dev;
        """
        params = {
            "feature_id": str(feature["feature_id"]),
            "field_id": feature["field_id"],
            "window_start": _to_iso_utc(feature["window_start"]),
            "window_end": _to_iso_utc(feature["window_end"]),
            "window_type": feature["window_type"],
            "feature_name": feature["feature_name"],
            "feature_value": float(feature["feature_value"]),
            "unit": feature.get("unit", "dimensionless"),
            "sample_count": int(feature.get("sample_count", 1)),
            "min_value": float(feature["min_value"]) if feature.get("min_value") is not None else None,
            "max_value": float(feature["max_value"]) if feature.get("max_value") is not None else None,
            "std_dev": float(feature["std_dev"]) if feature.get("std_dev") is not None else None,
        }

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                return cur.rowcount > 0

    def upsert_sensor_health_event(self, event: SensorHealthResultEvent | Dict[str, Any]) -> bool:
        """Inserts a forensic sensor health result event.

        Enforces idempotency on (idempotency_key, event_time).
        """
        if isinstance(event, SensorHealthResultEvent):
            d = event.model_dump()
        else:
            d = event

        query = """
        INSERT INTO sensor_health_events (
            idempotency_key, event_id, sensor_id, field_id, event_time, ingestion_time,
            health_state, reason_code, reason_description, is_usable_for_advisory,
            metrics, evidence
        ) VALUES (
            %(idempotency_key)s, %(event_id)s, %(sensor_id)s, %(field_id)s, %(event_time)s, %(ingestion_time)s,
            %(health_state)s, %(reason_code)s, %(reason_description)s, %(is_usable_for_advisory)s,
            %(metrics)s, %(evidence)s
        )
        ON CONFLICT (idempotency_key, event_time) DO NOTHING;
        """

        metrics_data = d.get("metrics") or {}
        if "observed_mean_window" in d:
            metrics_data["observed_mean_window"] = d["observed_mean_window"]
        if "confidence_score" in d:
            metrics_data["confidence_score"] = d["confidence_score"]

        reason_code_val = str(d.get("reason_code") or d.get("detected_anomaly_reason") or "UNKNOWN")
        reason_desc_val = d.get("detected_anomaly_reason") or d.get("reason_description")
        health_state_val = str(d.get("health_state") or d.get("health_flag") or "UNKNOWN")

        params = {
            "idempotency_key": d.get("idempotency_key", f"sh-{d['event_id']}"),
            "event_id": str(d["event_id"]),
            "sensor_id": d["sensor_id"],
            "field_id": d.get("field_id", "unspecified"),
            "event_time": _to_iso_utc(d["event_time"]),
            "ingestion_time": _to_iso_utc(d.get("ingestion_time", d["event_time"])),
            "health_state": health_state_val,
            "reason_code": reason_code_val,
            "reason_description": reason_desc_val,
            "is_usable_for_advisory": bool(d.get("is_usable_for_advisory", True)),
            "metrics": _to_jsonb(metrics_data),
            "evidence": _to_jsonb(d.get("evidence", {})),
        }

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                return cur.rowcount > 0

    def upsert_crop_candidate_alert(self, alert: CropRiskCandidateAlertEvent | Dict[str, Any]) -> bool:
        """Upserts a candidate crop risk alert on (alert_id, event_time)."""
        if isinstance(alert, CropRiskCandidateAlertEvent):
            d = alert.model_dump()
        else:
            d = alert

        query = """
        INSERT INTO crop_candidate_alerts (
            alert_id, field_id, event_time, ingestion_time, alert_type, severity,
            status, composite_stress_index, fao56_depletion_fraction, blast_risk_score,
            thermal_stress_score, sensor_health_state, uncertainty_score,
            contributing_features, evidence, suppression_reason
        ) VALUES (
            %(alert_id)s, %(field_id)s, %(event_time)s, %(ingestion_time)s, %(alert_type)s, %(severity)s,
            %(status)s, %(composite_stress_index)s, %(fao56_depletion_fraction)s, %(blast_risk_score)s,
            %(thermal_stress_score)s, %(sensor_health_state)s, %(uncertainty_score)s,
            %(contributing_features)s, %(evidence)s, %(suppression_reason)s
        )
        ON CONFLICT (alert_id, event_time)
        DO UPDATE SET
            status = EXCLUDED.status,
            composite_stress_index = EXCLUDED.composite_stress_index,
            uncertainty_score = EXCLUDED.uncertainty_score,
            contributing_features = EXCLUDED.contributing_features,
            evidence = EXCLUDED.evidence,
            suppression_reason = EXCLUDED.suppression_reason;
        """

        alert_type_val = str(d.get("risk_type") or d.get("alert_type") or "CROP_STRESS")
        severity_val = str(d.get("risk_level") or d.get("severity") or "MEDIUM")
        health_state_val = str(d.get("sensor_health_status") or d.get("sensor_health_state") or "HEALTHY")
        depletion_val = d.get("soil_depletion_fraction") if d.get("soil_depletion_fraction") is not None else d.get("fao56_depletion_fraction")
        evidence_dict = d.get("evidence") or {}
        if "evidence_summary" in d and isinstance(d["evidence_summary"], str):
            evidence_dict["evidence_summary"] = d["evidence_summary"]

        params = {
            "alert_id": str(d["alert_id"]),
            "field_id": d["field_id"],
            "event_time": _to_iso_utc(d["event_time"]),
            "ingestion_time": _to_iso_utc(d.get("ingestion_time", d["event_time"])),
            "alert_type": alert_type_val,
            "severity": severity_val,
            "status": str(d.get("status", "PENDING_TRIAGE")),
            "composite_stress_index": float(d.get("composite_stress_index", 0.0)),
            "fao56_depletion_fraction": float(depletion_val) if depletion_val is not None else None,
            "blast_risk_score": float(d["blast_risk_score"]) if d.get("blast_risk_score") is not None else None,
            "thermal_stress_score": float(d["thermal_stress_score"]) if d.get("thermal_stress_score") is not None else None,
            "sensor_health_state": health_state_val,
            "uncertainty_score": float(d.get("uncertainty_score", 0.0)),
            "contributing_features": _to_jsonb(d.get("contributing_features", [])),
            "evidence": _to_jsonb(evidence_dict),
            "suppression_reason": d.get("suppression_reason"),
        }

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                return cur.rowcount > 0

    # =========================================================================
    # 3. Investigation, Recommendation & Feedback
    # =========================================================================

    def create_investigation_report(self, report: Dict[str, Any]) -> str:
        """Stores an LLM agent investigation report."""
        query = """
        INSERT INTO investigation_reports (
            investigation_id, alert_id, field_id, agent_model, investigation_summary,
            corroborating_evidence, conflicting_evidence, recommendation_text,
            confidence_score
        ) VALUES (
            %(investigation_id)s, %(alert_id)s, %(field_id)s, %(agent_model)s, %(investigation_summary)s,
            %(corroborating_evidence)s, %(conflicting_evidence)s, %(recommendation_text)s,
            %(confidence_score)s
        );
        """
        params = {
            "investigation_id": str(report["investigation_id"]),
            "alert_id": str(report["alert_id"]),
            "field_id": report["field_id"],
            "agent_model": report.get("agent_model", "gemini-2.0-flash"),
            "investigation_summary": report["investigation_summary"],
            "corroborating_evidence": _to_jsonb(report.get("corroborating_evidence", [])),
            "conflicting_evidence": _to_jsonb(report.get("conflicting_evidence", [])),
            "recommendation_text": report["recommendation_text"],
            "confidence_score": float(report.get("confidence_score", 0.8)),
        }

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                return params["investigation_id"]

    def create_farmer_recommendation(self, rec: Dict[str, Any]) -> str:
        """Creates a proposed action recommendation for the farmer PWA."""
        query = """
        INSERT INTO farmer_recommendations (
            recommendation_id, alert_id, field_id, investigation_id, approval_status,
            action_category, action_title, action_body, urgency, expiry_time
        ) VALUES (
            %(recommendation_id)s, %(alert_id)s, %(field_id)s, %(investigation_id)s, %(approval_status)s,
            %(action_category)s, %(action_title)s, %(action_body)s, %(urgency)s, %(expiry_time)s
        );
        """
        params = {
            "recommendation_id": str(rec["recommendation_id"]),
            "alert_id": str(rec["alert_id"]),
            "field_id": rec["field_id"],
            "investigation_id": str(rec["investigation_id"]) if rec.get("investigation_id") else None,
            "approval_status": rec.get("approval_status", "PROPOSED"),
            "action_category": rec.get("action_category", "IRRIGATION"),
            "action_title": rec["action_title"],
            "action_body": rec["action_body"],
            "urgency": rec.get("urgency", "MEDIUM"),
            "expiry_time": _to_iso_utc(rec.get("expiry_time")),
        }

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                return params["recommendation_id"]

    def record_human_feedback(self, feedback: Dict[str, Any]) -> str:
        """Records farmer or agronomist human approval/feedback."""
        query = """
        INSERT INTO human_feedback (
            feedback_id, recommendation_id, field_id, farmer_id, rating,
            action_taken, observed_outcome, feedback_comments
        ) VALUES (
            %(feedback_id)s, %(recommendation_id)s, %(field_id)s, %(farmer_id)s, %(rating)s,
            %(action_taken)s, %(observed_outcome)s, %(feedback_comments)s
        );
        """
        params = {
            "feedback_id": str(feedback["feedback_id"]),
            "recommendation_id": str(feedback["recommendation_id"]),
            "field_id": feedback["field_id"],
            "farmer_id": feedback.get("farmer_id", "farmer-anonymous"),
            "rating": int(feedback["rating"]),
            "action_taken": bool(feedback["action_taken"]),
            "observed_outcome": feedback.get("observed_outcome"),
            "feedback_comments": feedback.get("feedback_comments"),
        }

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                return params["feedback_id"]

    # =========================================================================
    # 4. Representative Analytical Queries
    # =========================================================================

    def get_field_timeline(self, field_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Retrieves 24-hour observation timeline for a field."""
        query = """
        SELECT 
            o.event_time, o.ingestion_time, o.sensor_id, o.observed_variable,
            o.numeric_value, o.unit, o.provenance, o.quality_flags
        FROM observations o
        WHERE o.field_id = %s
          AND o.event_time >= NOW() - INTERVAL '1 hour' * %s
        ORDER BY o.event_time ASC;
        """
        results = []
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (field_id, hours))
                for row in cur.fetchall():
                    results.append({
                        "event_time": row[0],
                        "ingestion_time": row[1],
                        "sensor_id": row[2],
                        "observed_variable": row[3],
                        "numeric_value": row[4],
                        "unit": row[5],
                        "provenance": row[6],
                        "quality_flags": row[7],
                    })
        return results

    def get_sensor_freshness(self, field_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves latest observation latency and forensic status per sensor."""
        query = """
        SELECT 
            sm.sensor_id, sm.field_id, sm.sensor_model, sm.measured_variable,
            sm.unit, sm.provenance_type, latest_obs.last_event_time, latest_obs.last_value,
            ROUND(EXTRACT(EPOCH FROM (NOW() - latest_obs.last_event_time))::numeric, 1) AS latency_seconds,
            COALESCE(latest_health.health_state, 'UNKNOWN') AS health_state,
            COALESCE(latest_health.reason_code, 'NO_DATA') AS reason_code
        FROM sensor_metadata sm
        LEFT JOIN LATERAL (
            SELECT o.event_time AS last_event_time, o.numeric_value AS last_value
            FROM observations o
            WHERE o.sensor_id = sm.sensor_id
            ORDER BY o.event_time DESC LIMIT 1
        ) latest_obs ON TRUE
        LEFT JOIN LATERAL (
            SELECT sh.health_state, sh.reason_code
            FROM sensor_health_events sh
            WHERE sh.sensor_id = sm.sensor_id
            ORDER BY sh.event_time DESC LIMIT 1
        ) latest_health ON TRUE
        WHERE sm.is_active = TRUE
          AND (%s IS NULL OR sm.field_id = %s)
        ORDER BY latency_seconds ASC NULLS LAST;
        """
        results = []
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (field_id, field_id))
                for row in cur.fetchall():
                    results.append({
                        "sensor_id": row[0],
                        "field_id": row[1],
                        "sensor_model": row[2],
                        "measured_variable": row[3],
                        "unit": row[4],
                        "provenance_type": row[5],
                        "last_event_time": row[6],
                        "last_value": row[7],
                        "latency_seconds": float(row[8]) if row[8] is not None else None,
                        "health_state": row[9],
                        "reason_code": row[10],
                    })
        return results

    def get_recent_alerts(self, hours: int = 72) -> List[Dict[str, Any]]:
        """Retrieves recent candidate crop risk alerts."""
        query = """
        SELECT 
            ca.alert_id, ca.field_id, ca.event_time, ca.alert_type, ca.severity,
            ca.status, ca.composite_stress_index, ca.uncertainty_score,
            ca.contributing_features, ca.suppression_reason,
            ir.investigation_id IS NOT NULL AS has_investigation,
            rec.approval_status AS recommendation_status
        FROM crop_candidate_alerts ca
        LEFT JOIN investigation_reports ir ON ca.alert_id = ir.alert_id
        LEFT JOIN farmer_recommendations rec ON ca.alert_id = rec.alert_id
        WHERE ca.event_time >= NOW() - INTERVAL '1 hour' * %s
        ORDER BY ca.event_time DESC;
        """
        results = []
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (hours,))
                for row in cur.fetchall():
                    results.append({
                        "alert_id": str(row[0]),
                        "field_id": row[1],
                        "event_time": row[2],
                        "alert_type": row[3],
                        "severity": row[4],
                        "status": row[5],
                        "composite_stress_index": row[6],
                        "uncertainty_score": row[7],
                        "contributing_features": row[8],
                        "suppression_reason": row[9],
                        "has_investigation": bool(row[10]),
                        "recommendation_status": row[11],
                    })
        return results

    def get_alert_evidence_chain(self, alert_id: str | UUID) -> Optional[Dict[str, Any]]:
        """Retrieves the full evidence chain for a specific alert."""
        query = """
        SELECT 
            ca.alert_id, ca.field_id, ca.event_time, ca.alert_type, ca.severity,
            ca.composite_stress_index, ca.uncertainty_score, ca.contributing_features, ca.evidence,
            ir.investigation_id, ir.agent_model, ir.investigation_summary, ir.confidence_score,
            rec.recommendation_id, rec.action_title, rec.action_body, rec.approval_status,
            fb.feedback_id, fb.rating, fb.action_taken, fb.observed_outcome
        FROM crop_candidate_alerts ca
        LEFT JOIN investigation_reports ir ON ca.alert_id = ir.alert_id
        LEFT JOIN farmer_recommendations rec ON ca.alert_id = rec.alert_id
        LEFT JOIN human_feedback fb ON rec.recommendation_id = fb.recommendation_id
        WHERE ca.alert_id = %s;
        """
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (str(alert_id),))
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "alert_id": str(row[0]),
                    "field_id": row[1],
                    "event_time": row[2],
                    "alert_type": row[3],
                    "severity": row[4],
                    "composite_stress_index": row[5],
                    "uncertainty_score": row[6],
                    "contributing_features": row[7],
                    "evidence": row[8],
                    "investigation": {
                        "investigation_id": str(row[9]) if row[9] else None,
                        "agent_model": row[10],
                        "summary": row[11],
                        "confidence": row[12],
                    } if row[9] else None,
                    "recommendation": {
                        "recommendation_id": str(row[13]) if row[13] else None,
                        "title": row[14],
                        "body": row[15],
                        "status": row[16],
                    } if row[13] else None,
                    "feedback": {
                        "feedback_id": str(row[17]) if row[17] else None,
                        "rating": row[18],
                        "action_taken": row[19],
                        "observed_outcome": row[20],
                    } if row[17] else None,
                }
