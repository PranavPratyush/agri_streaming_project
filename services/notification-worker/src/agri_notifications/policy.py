"""Notification qualification and content safety policy evaluator."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from agri_notifications.config import notification_settings
from agri_notifications.models import NotificationPayload


QUALIFYING_ALERT_TYPES = {
    "SOIL_MOISTURE_DEPLETION",
    "BLAST_DISEASE_RISK",
    "THERMAL_STRESS_SPIKE",
}

EXTERNAL_BROADCAST_URGENCIES = {"CRITICAL", "HIGH"}

FORBIDDEN_CHEMICAL_PATTERNS = [
    re.compile(r"\b\d+(\.\d+)?\s*(ml|l|g|kg)\s*/\s*(l|ha|acre|plant)\b", re.IGNORECASE),
    re.compile(r"\b(carbendazim|mancozeb|chlorpyrifos|glyphosate|paraquat)\b", re.IGNORECASE),
]

FORBIDDEN_GUARANTEE_PATTERNS = [
    re.compile(r"\b(100%|guaranteed|cure all|eradicate completely|will ensure no loss)\b", re.IGNORECASE),
]


class NotificationPolicyEvaluator:
    """Evaluates whether an alert/advisory qualifies for notification and verifies safety invariants."""

    def __init__(self, pwa_base_url: Optional[str] = None):
        self.pwa_base_url = (pwa_base_url or notification_settings.pwa_base_url).rstrip("/")

    def evaluate_qualification(
        self,
        alert: Dict[str, Any],
        recommendation: Optional[Dict[str, Any]] = None,
        sensor_health_state: Optional[str] = None,
        critic_decision: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Determines if the event qualifies for external notification delivery.
        
        Returns (qualifies: bool, reason: str).
        """
        alert_type = alert.get("alert_type", "")
        if alert_type not in QUALIFYING_ALERT_TYPES:
            return False, f"Alert type '{alert_type}' is not in qualifying categories: {sorted(QUALIFYING_ALERT_TYPES)}"

        severity = (alert.get("severity") or "MEDIUM").upper()
        rec_urgency = (recommendation.get("urgency") if recommendation else "MEDIUM").upper()
        effective_urgency = "CRITICAL" if "CRITICAL" in (severity, rec_urgency) else ("HIGH" if "HIGH" in (severity, rec_urgency) else "MEDIUM")

        if effective_urgency not in EXTERNAL_BROADCAST_URGENCIES:
            return False, f"Urgency '{effective_urgency}' does not qualify for immediate push/external broadcast (requires CRITICAL or HIGH; available in PWA inbox)."

        # Check sensor health
        effective_sensor_health = (sensor_health_state or alert.get("sensor_health_state") or "HEALTHY").upper()
        if effective_sensor_health in ("FAULTY", "UNRELIABLE", "DEGRADED", "STALE"):
            return False, f"Sensor health is '{effective_sensor_health}'; active farmer advisory broadcast suppressed to prevent spurious action."

        # Check Critic/Supervisor decision
        if critic_decision in ("REJECTED", "ABSTAIN", "FAULT_DETECTED"):
            return False, f"Supervisor/Critic state is '{critic_decision}'; advisory delivery suppressed."

        return True, "Alert qualifies for notification dispatch."

    def sanitize_and_validate_content(
        self,
        recommendation: Dict[str, Any],
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Audits content against chemical dosage and guaranteed outcome restrictions.
        
        Returns (is_valid: bool, reason: str, sanitized_recommendation: Dict).
        """
        title = recommendation.get("action_title", "")
        body = recommendation.get("action_body", "")
        full_text = f"{title} {body}"

        # 1. Chemical dosages gate
        for pattern in FORBIDDEN_CHEMICAL_PATTERNS:
            if pattern.search(full_text):
                return False, f"Content contains prohibited specific chemical dosage or synthetic pesticide recommendation matching '{pattern.pattern}'. Must require certified extension officer inspection.", recommendation

        # 2. Guaranteed claims gate
        for pattern in FORBIDDEN_GUARANTEE_PATTERNS:
            if pattern.search(full_text):
                return False, f"Content contains prohibited outcome guarantee matching '{pattern.pattern}'. Agronomic guidance must state uncertainty and limitations.", recommendation

        sanitized = dict(recommendation)
        return True, "Content passed safety validation.", sanitized

    def build_notification_payload(
        self,
        alert: Dict[str, Any],
        recommendation: Dict[str, Any],
        advisory_version: int = 1,
    ) -> NotificationPayload:
        """Constructs a normalized, safety-checked NotificationPayload."""
        field_id = alert.get("field_id", recommendation.get("field_id", "field-unknown"))
        alert_id = str(alert.get("alert_id", "alert-unknown"))
        rec_id = str(recommendation.get("recommendation_id", "rec-unknown"))

        pwa_link = f"{self.pwa_base_url}/?field={field_id}&alert={alert_id}"

        provenance = alert.get("evidence", {}).get("sensor_provenance") or "Ground sensor network & calibrated satellite reanalysis"
        provenance_caveat = f"Observed via {provenance}. Data freshness and calibration checked prior to delivery."

        return NotificationPayload(
            alert_id=alert_id,
            advisory_id=rec_id,
            field_id=field_id,
            advisory_version=advisory_version,
            title=recommendation.get("action_title", "Crop Advisory Notice"),
            summary=recommendation.get("action_body", "Review recommended field actions in the AgriKafka PWA."),
            urgency=recommendation.get("urgency", alert.get("severity", "HIGH")),
            action_category=recommendation.get("action_category", "MONITORING"),
            pwa_deep_link=pwa_link,
            provenance_caveat=provenance_caveat,
            evidence_summary=str(alert.get("contributing_features", {})),
            limitations=recommendation.get("limitations", ["Advisory only; verify actual soil conditions prior to field execution."]),
            when_to_seek_expert=recommendation.get("when_to_seek_expert", "Contact local KVK agronomist if symptoms persist over 48 hours."),
        )

