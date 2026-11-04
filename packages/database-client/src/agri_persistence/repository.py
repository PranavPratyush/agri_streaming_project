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
    # 3b. Multi-Agent Investigation Runs, Messages & State Transitions
    # =========================================================================

    def create_multi_agent_run(self, run: Dict[str, Any]) -> str:
        """Persists a new multi-agent investigation run."""
        query = """
        INSERT INTO multi_agent_investigation_runs (
            run_id, alert_id, field_id, current_state, revision_count, max_revisions,
            final_decision, abstention_reason, summary, reliability_score, confidence_score,
            candidate_alert, state_payload, created_at, updated_at
        ) VALUES (
            %(run_id)s, %(alert_id)s, %(field_id)s, %(current_state)s, %(revision_count)s, %(max_revisions)s,
            %(final_decision)s, %(abstention_reason)s, %(summary)s, %(reliability_score)s, %(confidence_score)s,
            %(candidate_alert)s, %(state_payload)s, NOW(), NOW()
        )
        ON CONFLICT (run_id) DO UPDATE SET
            current_state = EXCLUDED.current_state,
            revision_count = EXCLUDED.revision_count,
            final_decision = EXCLUDED.final_decision,
            abstention_reason = EXCLUDED.abstention_reason,
            summary = EXCLUDED.summary,
            reliability_score = EXCLUDED.reliability_score,
            confidence_score = EXCLUDED.confidence_score,
            state_payload = EXCLUDED.state_payload,
            updated_at = NOW();
        """
        params = {
            "run_id": str(run["run_id"]),
            "alert_id": str(run["alert_id"]),
            "field_id": run["field_id"],
            "current_state": run.get("current_state", "received"),
            "revision_count": int(run.get("revision_count", 0)),
            "max_revisions": int(run.get("max_revisions", 2)),
            "final_decision": run.get("final_decision", "IN_PROGRESS"),
            "abstention_reason": run.get("abstention_reason"),
            "summary": run.get("summary"),
            "reliability_score": float(run["reliability_score"]) if run.get("reliability_score") is not None else None,
            "confidence_score": float(run["confidence_score"]) if run.get("confidence_score") is not None else None,
            "candidate_alert": _to_jsonb(run.get("candidate_alert", {})),
            "state_payload": _to_jsonb(run.get("state_payload", {})),
        }

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                return params["run_id"]

    def update_multi_agent_run(self, run_id: str, updates: Dict[str, Any]) -> bool:
        """Updates status and state of an existing multi-agent investigation run."""
        set_clauses = ["updated_at = NOW()"]
        params: Dict[str, Any] = {"run_id": str(run_id)}

        for key in ["current_state", "revision_count", "final_decision", "abstention_reason", "summary", "reliability_score", "confidence_score"]:
            if key in updates:
                set_clauses.append(f"{key} = %({key})s")
                params[key] = updates[key]

        if "state_payload" in updates:
            set_clauses.append("state_payload = %(state_payload)s")
            params["state_payload"] = _to_jsonb(updates["state_payload"])

        query = f"""
        UPDATE multi_agent_investigation_runs
        SET {", ".join(set_clauses)}
        WHERE run_id = %(run_id)s;
        """

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                return cur.rowcount > 0

    def record_agent_message(self, msg: Dict[str, Any]) -> str:
        """Persists a structured versioned agent message with idempotency guarantee."""
        query = """
        INSERT INTO agent_messages (
            message_id, run_id, correlation_id, parent_message_id, from_agent, to_agent,
            message_type, payload_schema_version, payload, idempotency_key, status,
            error_details, created_at
        ) VALUES (
            %(message_id)s, %(run_id)s, %(correlation_id)s, %(parent_message_id)s, %(from_agent)s, %(to_agent)s,
            %(message_type)s, %(payload_schema_version)s, %(payload)s, %(idempotency_key)s, %(status)s,
            %(error_details)s, %(created_at)s
        )
        ON CONFLICT (idempotency_key) DO NOTHING;
        """
        created_at = _to_iso_utc(msg.get("created_at")) or datetime.now(timezone.utc)
        params = {
            "message_id": str(msg["message_id"]),
            "run_id": str(msg["run_id"]),
            "correlation_id": str(msg["correlation_id"]),
            "parent_message_id": str(msg["parent_message_id"]) if msg.get("parent_message_id") else None,
            "from_agent": msg["from_agent"],
            "to_agent": msg["to_agent"],
            "message_type": msg["message_type"],
            "payload_schema_version": msg.get("payload_schema_version", "1.0.0"),
            "payload": _to_jsonb(msg.get("payload", {})),
            "idempotency_key": msg["idempotency_key"],
            "status": msg.get("status", "ACCEPTED"),
            "error_details": _to_jsonb(msg.get("error_details")) if msg.get("error_details") else None,
            "created_at": created_at,
        }

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                return params["message_id"]

    def record_state_transition(self, transition: Dict[str, Any]) -> int:
        """Records an explicit state machine transition."""
        query = """
        INSERT INTO investigation_state_transitions (
            run_id, from_state, to_state, triggered_by, reason, created_at
        ) VALUES (
            %(run_id)s, %(from_state)s, %(to_state)s, %(triggered_by)s, %(reason)s, NOW()
        )
        RETURNING transition_id;
        """
        params = {
            "run_id": str(transition["run_id"]),
            "from_state": transition["from_state"],
            "to_state": transition["to_state"],
            "triggered_by": transition.get("triggered_by", "supervisor"),
            "reason": transition.get("reason"),
        }

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                conn.commit()
                return row[0] if row else 0

    def get_multi_agent_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a multi-agent investigation run by ID."""
        query = """
        SELECT run_id, alert_id, field_id, current_state, revision_count, max_revisions,
               final_decision, abstention_reason, summary, reliability_score, confidence_score,
               candidate_alert, state_payload, created_at, updated_at
        FROM multi_agent_investigation_runs
        WHERE run_id = %s;
        """
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (str(run_id),))
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "run_id": row[0],
                    "alert_id": row[1],
                    "field_id": row[2],
                    "current_state": row[3],
                    "revision_count": row[4],
                    "max_revisions": row[5],
                    "final_decision": row[6],
                    "abstention_reason": row[7],
                    "summary": row[8],
                    "reliability_score": row[9],
                    "confidence_score": row[10],
                    "candidate_alert": row[11],
                    "state_payload": row[12],
                    "created_at": row[13],
                    "updated_at": row[14],
                }

    def get_run_messages(self, run_id: str) -> List[Dict[str, Any]]:
        """Retrieves all messages routed during an investigation run."""
        query = """
        SELECT message_id, run_id, correlation_id, parent_message_id, from_agent, to_agent,
               message_type, payload_schema_version, payload, idempotency_key, status,
               error_details, created_at
        FROM agent_messages
        WHERE run_id = %s
        ORDER BY created_at ASC;
        """
        results = []
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (str(run_id),))
                for row in cur.fetchall():
                    results.append({
                        "message_id": row[0],
                        "run_id": row[1],
                        "correlation_id": row[2],
                        "parent_message_id": row[3],
                        "from_agent": row[4],
                        "to_agent": row[5],
                        "message_type": row[6],
                        "payload_schema_version": row[7],
                        "payload": row[8],
                        "idempotency_key": row[9],
                        "status": row[10],
                        "error_details": row[11],
                        "created_at": row[12],
                    })
        return results

    def get_run_state_transitions(self, run_id: str) -> List[Dict[str, Any]]:
        """Retrieves complete transition audit log for an investigation run."""
        query = """
        SELECT transition_id, run_id, from_state, to_state, triggered_by, reason, created_at
        FROM investigation_state_transitions
        WHERE run_id = %s
        ORDER BY transition_id ASC;
        """
        results = []
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (str(run_id),))
                for row in cur.fetchall():
                    results.append({
                        "transition_id": row[0],
                        "run_id": row[1],
                        "from_state": row[2],
                        "to_state": row[3],
                        "triggered_by": row[4],
                        "reason": row[5],
                        "created_at": row[6],
                    })
        return results

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

    # =========================================================================
    # 5. Additional Query Endpoints for FastAPI Backend
    # =========================================================================

    def get_field_profile(self, field_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves field profile entity by field_id."""
        query = """
        SELECT field_id, name, latitude, longitude, elevation_m, crop_name, variety,
               sowing_date, expected_harvest_date, current_growth_stage, soil_type,
               soil_texture, field_capacity, wilting_point, root_zone_depth_m,
               irrigation_type, is_active, metadata, created_at, updated_at
        FROM field_profiles
        WHERE field_id = %s;
        """
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (field_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "field_id": row[0],
                    "name": row[1],
                    "latitude": row[2],
                    "longitude": row[3],
                    "elevation_m": row[4],
                    "crop_name": row[5],
                    "variety": row[6],
                    "sowing_date": row[7].isoformat() if row[7] else None,
                    "expected_harvest_date": row[8].isoformat() if row[8] else None,
                    "current_growth_stage": row[9],
                    "soil_type": row[10],
                    "soil_texture": row[11],
                    "field_capacity": row[12],
                    "wilting_point": row[13],
                    "root_zone_depth_m": row[14],
                    "irrigation_type": row[15],
                    "is_active": row[16],
                    "metadata": row[17] if isinstance(row[17], dict) else {},
                    "created_at": row[18].isoformat() if row[18] else None,
                    "updated_at": row[19].isoformat() if row[19] else None,
                }

    def list_field_profiles(self, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Lists all registered field profiles with optional active filter."""
        query = """
        SELECT field_id, name, latitude, longitude, elevation_m, crop_name, variety,
               sowing_date, expected_harvest_date, current_growth_stage, soil_type,
               soil_texture, field_capacity, wilting_point, root_zone_depth_m,
               irrigation_type, is_active, metadata, created_at, updated_at
        FROM field_profiles
        """
        params = []
        if is_active is not None:
            query += " WHERE is_active = %s"
            params.append(is_active)
        query += " ORDER BY field_id ASC;"

        results = []
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                for row in cur.fetchall():
                    results.append({
                        "field_id": row[0],
                        "name": row[1],
                        "latitude": row[2],
                        "longitude": row[3],
                        "elevation_m": row[4],
                        "crop_name": row[5],
                        "variety": row[6],
                        "sowing_date": row[7].isoformat() if row[7] else None,
                        "expected_harvest_date": row[8].isoformat() if row[8] else None,
                        "current_growth_stage": row[9],
                        "soil_type": row[10],
                        "soil_texture": row[11],
                        "field_capacity": row[12],
                        "wilting_point": row[13],
                        "root_zone_depth_m": row[14],
                        "irrigation_type": row[15],
                        "is_active": row[16],
                        "metadata": row[17] if isinstance(row[17], dict) else {},
                        "created_at": row[18].isoformat() if row[18] else None,
                        "updated_at": row[19].isoformat() if row[19] else None,
                    })
        return results

    def get_field_observations(
        self,
        field_id: str,
        variable: Optional[str] = None,
        hours: int = 24,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieves raw or canonical observations with provenance flags."""
        query = """
        SELECT o.event_time, o.ingestion_time, o.sensor_id, o.observed_variable,
               o.numeric_value, o.unit, o.provenance, o.quality_flags
        FROM observations o
        WHERE o.field_id = %s
          AND o.event_time >= NOW() - INTERVAL '1 hour' * %s
        """
        params = [field_id, hours]
        if variable:
            query += " AND o.observed_variable = %s"
            params.append(variable)
        query += " ORDER BY o.event_time DESC LIMIT %s;"
        params.append(limit)

        results = []
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                for row in cur.fetchall():
                    results.append({
                        "event_time": row[0].isoformat() if row[0] else None,
                        "ingestion_time": row[1].isoformat() if row[1] else None,
                        "sensor_id": row[2],
                        "observed_variable": row[3],
                        "numeric_value": row[4],
                        "unit": row[5],
                        "provenance": row[6],
                        "quality_flags": row[7],
                    })
        return results

    def get_field_sensor_health(
        self,
        field_id: str,
        hours: int = 24,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieves recent sensor-health forensic events for a field parcel."""
        query = """
        SELECT sh.event_time, sh.sensor_id, sh.health_state, sh.reason_code,
               sh.metrics, sh.diagnostics, sh.exemption_type
        FROM sensor_health_events sh
        WHERE sh.field_id = %s
          AND sh.event_time >= NOW() - INTERVAL '1 hour' * %s
        ORDER BY sh.event_time DESC LIMIT %s;
        """
        results = []
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (field_id, hours, limit))
                for row in cur.fetchall():
                    results.append({
                        "event_time": row[0].isoformat() if row[0] else None,
                        "sensor_id": row[1],
                        "health_state": row[2],
                        "reason_code": row[3],
                        "metrics": row[4],
                        "diagnostics": row[5],
                        "exemption_type": row[6],
                    })
        return results

    def list_recent_alerts(
        self,
        field_id: Optional[str] = None,
        hours: int = 72,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Lists candidate alerts across fields or for a specific field."""
        query = """
        SELECT alert_id, field_id, event_time, ingestion_time, alert_type, severity, status,
               composite_stress_index, fao56_depletion_fraction, blast_risk_score,
               thermal_stress_score, sensor_health_state, uncertainty_score,
               contributing_features, evidence, suppression_reason
        FROM crop_candidate_alerts
        WHERE event_time >= NOW() - INTERVAL '1 hour' * %s
        """
        params = [hours]
        if field_id:
            query += " AND field_id = %s"
            params.append(field_id)
        query += " ORDER BY event_time DESC LIMIT %s;"
        params.append(limit)

        results = []
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                for row in cur.fetchall():
                    results.append({
                        "alert_id": str(row[0]),
                        "field_id": row[1],
                        "event_time": row[2].isoformat() if row[2] else None,
                        "ingestion_time": row[3].isoformat() if row[3] else None,
                        "alert_type": row[4],
                        "severity": row[5],
                        "status": row[6],
                        "composite_stress_index": row[7],
                        "fao56_depletion_fraction": row[8],
                        "blast_risk_score": row[9],
                        "thermal_stress_score": row[10],
                        "sensor_health_state": row[11],
                        "uncertainty_score": row[12],
                        "contributing_features": row[13],
                        "evidence": row[14],
                        "suppression_reason": row[15],
                    })
        return results

    def get_alert_by_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves candidate alert details by alert_id."""
        query = """
        SELECT alert_id, field_id, event_time, ingestion_time, alert_type, severity, status,
               composite_stress_index, fao56_depletion_fraction, blast_risk_score,
               thermal_stress_score, sensor_health_state, uncertainty_score,
               contributing_features, evidence, suppression_reason
        FROM crop_candidate_alerts
        WHERE alert_id = %s
        ORDER BY event_time DESC LIMIT 1;
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
                    "event_time": row[2].isoformat() if row[2] else None,
                    "ingestion_time": row[3].isoformat() if row[3] else None,
                    "alert_type": row[4],
                    "severity": row[5],
                    "status": row[6],
                    "composite_stress_index": row[7],
                    "fao56_depletion_fraction": row[8],
                    "blast_risk_score": row[9],
                    "thermal_stress_score": row[10],
                    "sensor_health_state": row[11],
                    "uncertainty_score": row[12],
                    "contributing_features": row[13],
                    "evidence": row[14],
                    "suppression_reason": row[15],
                }

    def list_farmer_recommendations(
        self,
        field_id: Optional[str] = None,
        approval_status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Lists proposed or active farmer recommendations."""
        query = """
        SELECT recommendation_id, alert_id, field_id, investigation_id, approval_status,
               action_category, action_title, action_body, urgency, expiry_time,
               approved_by, approved_at, created_at
        FROM farmer_recommendations
        """
        clauses = []
        params = []
        if field_id:
            clauses.append("field_id = %s")
            params.append(field_id)
        if approval_status:
            clauses.append("approval_status = %s")
            params.append(approval_status)

        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC LIMIT %s;"
        params.append(limit)

        results = []
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                for row in cur.fetchall():
                    results.append({
                        "recommendation_id": str(row[0]),
                        "alert_id": str(row[1]),
                        "field_id": row[2],
                        "investigation_id": str(row[3]) if row[3] else None,
                        "approval_status": row[4],
                        "action_category": row[5],
                        "action_title": row[6],
                        "action_body": row[7],
                        "urgency": row[8],
                        "expiry_time": row[9].isoformat() if row[9] else None,
                        "approved_by": row[10],
                        "approved_at": row[11].isoformat() if row[11] else None,
                        "created_at": row[12].isoformat() if row[12] else None,
                    })
        return results

    def get_recommendation_by_id(self, recommendation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single farmer recommendation by ID."""
        query = """
        SELECT recommendation_id, alert_id, field_id, investigation_id, approval_status,
               action_category, action_title, action_body, urgency, expiry_time,
               approved_by, approved_at, created_at
        FROM farmer_recommendations
        WHERE recommendation_id = %s;
        """
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (str(recommendation_id),))
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "recommendation_id": str(row[0]),
                    "alert_id": str(row[1]),
                    "field_id": row[2],
                    "investigation_id": str(row[3]) if row[3] else None,
                    "approval_status": row[4],
                    "action_category": row[5],
                    "action_title": row[6],
                    "action_body": row[7],
                    "urgency": row[8],
                    "expiry_time": row[9].isoformat() if row[9] else None,
                    "approved_by": row[10],
                    "approved_at": row[11].isoformat() if row[11] else None,
                    "created_at": row[12].isoformat() if row[12] else None,
                }

    def update_recommendation_status(
        self,
        recommendation_id: str,
        status: str,
        approved_by: str,
    ) -> bool:
        """Updates approval status (e.g., APPROVED, REJECTED) of a recommendation."""
        query = """
        UPDATE farmer_recommendations
        SET approval_status = %s,
            approved_by = %s,
            approved_at = now()
        WHERE recommendation_id = %s;
        """
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (status, approved_by, str(recommendation_id)))
                conn.commit()
                return cur.rowcount > 0

    def list_human_feedback(self, field_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Lists recorded farmer feedback and action outcomes."""
        query = """
        SELECT feedback_id, recommendation_id, field_id, farmer_id, rating,
               action_taken, observed_outcome, feedback_comments, created_at
        FROM human_feedback
        """
        params = []
        if field_id:
            query += " WHERE field_id = %s"
            params.append(field_id)
        query += " ORDER BY created_at DESC LIMIT %s;"
        params.append(limit)

        results = []
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                for row in cur.fetchall():
                    results.append({
                        "feedback_id": str(row[0]),
                        "recommendation_id": str(row[1]),
                        "field_id": row[2],
                        "farmer_id": row[3],
                        "rating": row[4],
                        "action_taken": row[5],
                        "observed_outcome": row[6],
                        "feedback_comments": row[7],
                        "created_at": row[8].isoformat() if row[8] else None,
                    })
        return results

    def record_human_feedback(self, feedback: Dict[str, Any]) -> str:
        """Records farmer or agronomist feedback linked to an advisory and investigation."""
        query = """
        INSERT INTO human_feedback (
            feedback_id, recommendation_id, field_id, farmer_id, rating,
            action_taken, observed_outcome, feedback_comments, investigation_id,
            alert_id, advisory_version, advisory_relevant, evidence_useful,
            field_context_correct, sensor_issue_reported, sensor_issue_notes,
            expert_followup_requested, cited_agent_outputs, idempotency_key, created_at
        ) VALUES (
            %(feedback_id)s, %(recommendation_id)s, %(field_id)s, %(farmer_id)s, %(rating)s,
            %(action_taken)s, %(observed_outcome)s, %(feedback_comments)s, %(investigation_id)s,
            %(alert_id)s, %(advisory_version)s, %(advisory_relevant)s, %(evidence_useful)s,
            %(field_context_correct)s, %(sensor_issue_reported)s, %(sensor_issue_notes)s,
            %(expert_followup_requested)s, %(cited_agent_outputs)s, %(idempotency_key)s, now()
        )
        ON CONFLICT (idempotency_key) DO UPDATE SET
            rating = EXCLUDED.rating,
            feedback_comments = EXCLUDED.feedback_comments
        RETURNING feedback_id;
        """
        params = {
            "feedback_id": str(feedback.get("feedback_id") or uuid.uuid4()),
            "recommendation_id": str(feedback["recommendation_id"]),
            "field_id": feedback["field_id"],
            "farmer_id": feedback.get("farmer_id") or "farmer-anonymous",
            "rating": int(feedback.get("rating", 5)),
            "action_taken": bool(feedback.get("action_taken", False)),
            "observed_outcome": feedback.get("observed_outcome"),
            "feedback_comments": feedback.get("feedback_comments"),
            "investigation_id": str(feedback["investigation_id"]) if feedback.get("investigation_id") else None,
            "alert_id": str(feedback["alert_id"]) if feedback.get("alert_id") else None,
            "advisory_version": int(feedback.get("advisory_version", 1)),
            "advisory_relevant": bool(feedback.get("advisory_relevant", True)),
            "evidence_useful": bool(feedback.get("evidence_useful", True)),
            "field_context_correct": bool(feedback.get("field_context_correct", True)),
            "sensor_issue_reported": bool(feedback.get("sensor_issue_reported", False)),
            "sensor_issue_notes": feedback.get("sensor_issue_notes"),
            "expert_followup_requested": bool(feedback.get("expert_followup_requested", False)),
            "cited_agent_outputs": _to_jsonb(feedback.get("cited_agent_outputs", [])),
            "idempotency_key": feedback.get("idempotency_key"),
        }
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                conn.commit()
                return str(row[0]) if row else str(params["feedback_id"])

    def get_feedback_by_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves feedback by unique idempotency key."""
        query = """
        SELECT feedback_id, recommendation_id, field_id, farmer_id, rating,
               action_taken, observed_outcome, feedback_comments, investigation_id,
               alert_id, advisory_version, advisory_relevant, evidence_useful,
               field_context_correct, sensor_issue_reported, sensor_issue_notes,
               expert_followup_requested, cited_agent_outputs, idempotency_key, created_at
        FROM human_feedback
        WHERE idempotency_key = %s;
        """
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (idempotency_key,))
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "feedback_id": str(row[0]),
                    "recommendation_id": str(row[1]),
                    "field_id": row[2],
                    "farmer_id": row[3],
                    "rating": row[4],
                    "action_taken": row[5],
                    "observed_outcome": row[6],
                    "feedback_comments": row[7],
                    "investigation_id": str(row[8]) if row[8] else None,
                    "alert_id": str(row[9]) if row[9] else None,
                    "advisory_version": row[10],
                    "advisory_relevant": row[11],
                    "evidence_useful": row[12],
                    "field_context_correct": row[13],
                    "sensor_issue_reported": row[14],
                    "sensor_issue_notes": row[15],
                    "expert_followup_requested": row[16],
                    "cited_agent_outputs": row[17],
                    "idempotency_key": row[18],
                    "created_at": row[19].isoformat() if row[19] else None,
                }

    def create_notification_dispatch(self, dispatch: Dict[str, Any]) -> str:
        """Records a notification dispatch attempt."""
        query = """
        INSERT INTO notification_dispatches (
            dispatch_id, alert_id, investigation_id, recommendation_id, advisory_version,
            recipient_id, channel, idempotency_key, status, attempts, max_retries,
            next_retry_at, delivered_at, payload, provider_response, error_message,
            created_at, updated_at
        ) VALUES (
            %(dispatch_id)s, %(alert_id)s, %(investigation_id)s, %(recommendation_id)s, %(advisory_version)s,
            %(recipient_id)s, %(channel)s, %(idempotency_key)s, %(status)s, %(attempts)s, %(max_retries)s,
            %(next_retry_at)s, %(delivered_at)s, %(payload)s, %(provider_response)s, %(error_message)s,
            NOW(), NOW()
        )
        ON CONFLICT (idempotency_key) DO UPDATE SET
            status = EXCLUDED.status,
            attempts = EXCLUDED.attempts,
            delivered_at = EXCLUDED.delivered_at,
            provider_response = EXCLUDED.provider_response,
            error_message = EXCLUDED.error_message,
            updated_at = NOW()
        RETURNING dispatch_id;
        """
        params = {
            "dispatch_id": str(dispatch["dispatch_id"]),
            "alert_id": str(dispatch["alert_id"]),
            "investigation_id": str(dispatch["investigation_id"]) if dispatch.get("investigation_id") else None,
            "recommendation_id": str(dispatch["recommendation_id"]) if dispatch.get("recommendation_id") else None,
            "advisory_version": int(dispatch.get("advisory_version", 1)),
            "recipient_id": dispatch["recipient_id"],
            "channel": dispatch["channel"],
            "idempotency_key": dispatch["idempotency_key"],
            "status": dispatch.get("status", "PENDING"),
            "attempts": int(dispatch.get("attempts", 0)),
            "max_retries": int(dispatch.get("max_retries", 3)),
            "next_retry_at": dispatch.get("next_retry_at"),
            "delivered_at": dispatch.get("delivered_at"),
            "payload": _to_jsonb(dispatch.get("payload", {})),
            "provider_response": _to_jsonb(dispatch.get("provider_response", {})),
            "error_message": dispatch.get("error_message"),
        }
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                conn.commit()
                return str(row[0]) if row else str(params["dispatch_id"])

    def get_notification_dispatch_by_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves a notification dispatch by compound idempotency key."""
        query = """
        SELECT dispatch_id, alert_id, investigation_id, recommendation_id, advisory_version,
               recipient_id, channel, idempotency_key, status, attempts, max_retries,
               next_retry_at, delivered_at, payload, provider_response, error_message,
               created_at, updated_at
        FROM notification_dispatches
        WHERE idempotency_key = %s;
        """
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (idempotency_key,))
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "dispatch_id": str(row[0]),
                    "alert_id": str(row[1]),
                    "investigation_id": str(row[2]) if row[2] else None,
                    "recommendation_id": str(row[3]) if row[3] else None,
                    "advisory_version": row[4],
                    "recipient_id": row[5],
                    "channel": row[6],
                    "idempotency_key": row[7],
                    "status": row[8],
                    "attempts": row[9],
                    "max_retries": row[10],
                    "next_retry_at": row[11].isoformat() if row[11] else None,
                    "delivered_at": row[12].isoformat() if row[12] else None,
                    "payload": row[13],
                    "provider_response": row[14],
                    "error_message": row[15],
                    "created_at": row[16].isoformat() if row[16] else None,
                    "updated_at": row[17].isoformat() if row[17] else None,
                }

    def list_notification_dispatches(
        self,
        recipient_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Lists recent notification dispatches."""
        query = """
        SELECT dispatch_id, alert_id, investigation_id, recommendation_id, advisory_version,
               recipient_id, channel, idempotency_key, status, attempts, max_retries,
               next_retry_at, delivered_at, payload, provider_response, error_message,
               created_at, updated_at
        FROM notification_dispatches
        """
        clauses = []
        params = []
        if recipient_id:
            clauses.append("recipient_id = %s")
            params.append(recipient_id)
        if status:
            clauses.append("status = %s")
            params.append(status)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC LIMIT %s;"
        params.append(limit)

        results = []
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                for row in cur.fetchall():
                    results.append({
                        "dispatch_id": str(row[0]),
                        "alert_id": str(row[1]),
                        "investigation_id": str(row[2]) if row[2] else None,
                        "recommendation_id": str(row[3]) if row[3] else None,
                        "advisory_version": row[4],
                        "recipient_id": row[5],
                        "channel": row[6],
                        "idempotency_key": row[7],
                        "status": row[8],
                        "attempts": row[9],
                        "max_retries": row[10],
                        "next_retry_at": row[11].isoformat() if row[11] else None,
                        "delivered_at": row[12].isoformat() if row[12] else None,
                        "payload": row[13],
                        "provider_response": row[14],
                        "error_message": row[15],
                        "created_at": row[16].isoformat() if row[16] else None,
                        "updated_at": row[17].isoformat() if row[17] else None,
                    })
        return results

    def record_system_audit(
        self,
        action: str,
        actor: str,
        entity_type: str,
        entity_id: str,
        details: Dict[str, Any],
    ) -> int:
        """Appends an event to the system audit log."""
        query = """
        INSERT INTO system_audit_log (action, actor, entity_type, entity_id, details, created_at)
        VALUES (%s, %s, %s, %s, %s, now())
        RETURNING audit_id;
        """
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (action, actor, entity_type, str(entity_id), _to_jsonb(details)))
                row = cur.fetchone()
                conn.commit()
                return row[0] if row else 0
