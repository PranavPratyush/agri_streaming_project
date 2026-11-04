"""Human review lifecycle management for farmer advisory recommendations."""

from __future__ import annotations

import datetime
import logging
import uuid
from typing import Any, Dict, Optional, Tuple

from agri_notifications.models import (
    AdvisoryStatus,
    HumanReviewActionRequest,
    HumanReviewActionResponse,
    ReviewAction,
)

logger = logging.getLogger("agri.notifications.lifecycle")

ACTION_TO_STATUS_MAP = {
    ReviewAction.APPROVE: AdvisoryStatus.APPROVED,
    ReviewAction.REJECT: AdvisoryStatus.REJECTED,
    ReviewAction.ACKNOWLEDGE: AdvisoryStatus.ACKNOWLEDGED,
    ReviewAction.REQUEST_INSPECTION: AdvisoryStatus.REQUEST_INSPECTION,
    ReviewAction.EXPIRE: AdvisoryStatus.EXPIRED,
    ReviewAction.SUPERSEDE: AdvisoryStatus.SUPERSEDED,
}

FINAL_STATUSES = {
    AdvisoryStatus.APPROVED.value,
    AdvisoryStatus.REJECTED.value,
    AdvisoryStatus.EXPIRED.value,
    AdvisoryStatus.SUPERSEDED.value,
}


class HumanReviewLifecycleManager:
    """Safely manages advisory decision state transitions, idempotency, and audit trails."""

    def __init__(self, repository: Any):
        self.repo = repository

    def apply_action(
        self,
        recommendation_id: str,
        request: HumanReviewActionRequest,
    ) -> Tuple[bool, HumanReviewActionResponse, int]:
        """Applies a human review action.
        
        Returns (success: bool, response: HumanReviewActionResponse, http_status_code: int).
        """
        rec = self.repo.get_recommendation_by_id(recommendation_id)
        if not rec:
            return False, HumanReviewActionResponse(
                success=False,
                recommendation_id=recommendation_id,
                previous_status="UNKNOWN",
                resulting_status="NOT_FOUND",
                advisory_version=request.advisory_version,
                reviewer_id=request.reviewer_id or "system",
                idempotency_key=request.idempotency_key or "",
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                actuation_command_dispatched=False,
                message=f"Advisory recommendation '{recommendation_id}' not found.",
            ), 404

        current_status = rec.get("approval_status", AdvisoryStatus.PROPOSED.value)
        idempotency_key = request.idempotency_key or str(uuid.uuid4())
        reviewer_id = request.reviewer_id or "human-reviewer"
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        target_status = ACTION_TO_STATUS_MAP[request.action].value

        # Idempotency / Finality check
        if current_status in FINAL_STATUSES:
            if current_status == target_status:
                # Idempotent replay of identical decision
                return True, HumanReviewActionResponse(
                    success=True,
                    recommendation_id=recommendation_id,
                    previous_status=current_status,
                    resulting_status=current_status,
                    advisory_version=rec.get("advisory_version", request.advisory_version),
                    reviewer_id=rec.get("approved_by") or reviewer_id,
                    idempotency_key=idempotency_key,
                    timestamp=now_iso,
                    actuation_command_dispatched=False,
                    message=f"Idempotent replay: Advisory '{recommendation_id}' was already finalized with status '{current_status}'.",
                ), 200
            else:
                # Stale or conflicting transition attempted on finalized advisory
                return False, HumanReviewActionResponse(
                    success=False,
                    recommendation_id=recommendation_id,
                    previous_status=current_status,
                    resulting_status=current_status,
                    advisory_version=rec.get("advisory_version", request.advisory_version),
                    reviewer_id=reviewer_id,
                    idempotency_key=idempotency_key,
                    timestamp=now_iso,
                    actuation_command_dispatched=False,
                    message=f"Conflict: Advisory '{recommendation_id}' is already finalized as '{current_status}'. Cannot transition to '{target_status}'.",
                ), 409

        # Version consistency check
        rec_version = int(rec.get("advisory_version", 1))
        if request.advisory_version < rec_version:
            return False, HumanReviewActionResponse(
                success=False,
                recommendation_id=recommendation_id,
                previous_status=current_status,
                resulting_status=current_status,
                advisory_version=rec_version,
                reviewer_id=reviewer_id,
                idempotency_key=idempotency_key,
                timestamp=now_iso,
                actuation_command_dispatched=False,
                message=f"Stale advisory version {request.advisory_version} submitted; current version is {rec_version}.",
            ), 409

        # Update recommendation status in persistence
        self.repo.update_recommendation_status(
            recommendation_id=recommendation_id,
            status=target_status,
            approved_by=reviewer_id,
        )

        # Audit record
        self.repo.record_system_audit(
            action=f"ADVISORY_{request.action.value}",
            actor=reviewer_id,
            entity_type="farmer_recommendation",
            entity_id=recommendation_id,
            details={
                "action": request.action.value,
                "previous_status": current_status,
                "resulting_status": target_status,
                "reason": request.reason,
                "idempotency_key": idempotency_key,
                "actuation_command_dispatched": False,
            },
        )

        logger.info(
            "Advisory %s transitioned: %s -> %s by reviewer %s (Zero actuation dispatched)",
            recommendation_id,
            current_status,
            target_status,
            reviewer_id,
        )

        return True, HumanReviewActionResponse(
            success=True,
            recommendation_id=recommendation_id,
            previous_status=current_status,
            resulting_status=target_status,
            advisory_version=rec_version,
            reviewer_id=reviewer_id,
            idempotency_key=idempotency_key,
            timestamp=now_iso,
            actuation_command_dispatched=False,
            message=f"Advisory status successfully updated to '{target_status}'. Zero autonomous physical actuation was dispatched.",
        ), 200

