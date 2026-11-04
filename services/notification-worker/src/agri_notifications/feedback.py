"""Feedback processor for farmer feedback linked to multi-agent investigation evidence."""

from __future__ import annotations

import datetime
import logging
import uuid
from typing import Any, Dict, Optional, Tuple

from agri_notifications.models import StructuredFeedbackInput

logger = logging.getLogger("agri.notifications.feedback")


class FeedbackProcessor:
    """Processes, validates, and persists farmer feedback linked to investigation runs."""

    def __init__(self, repository: Any):
        self.repo = repository

    def record_feedback(
        self,
        feedback: StructuredFeedbackInput,
    ) -> Tuple[bool, Dict[str, Any], str]:
        """Validates and persists feedback without any online mutation of agent prompts or thresholds.
        
        Returns (success: bool, recorded_feedback: Dict, message: str).
        """
        idempotency_key = feedback.idempotency_key or f"fb-{uuid.uuid4()}"

        # Deduplication check
        if hasattr(self.repo, "get_feedback_by_idempotency"):
            existing = self.repo.get_feedback_by_idempotency(idempotency_key)
            if existing:
                logger.info("Feedback already recorded for idempotency key %s", idempotency_key)
                return True, existing, "Idempotent replay: Feedback already recorded."

        feedback_id = feedback.feedback_id or str(uuid.uuid4())
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Invariant check: Ensure prompt/threshold mutations are prevented
        feedback_record = {
            "feedback_id": feedback_id,
            "recommendation_id": feedback.recommendation_id,
            "field_id": feedback.field_id,
            "farmer_id": feedback.farmer_id or "farmer-anonymous",
            "investigation_id": feedback.investigation_id,
            "alert_id": feedback.alert_id,
            "advisory_version": feedback.advisory_version,
            "rating": feedback.rating,
            "action_taken": feedback.action_taken,
            "observed_outcome": feedback.observed_outcome,
            "advisory_relevant": feedback.advisory_relevant,
            "evidence_useful": feedback.evidence_useful,
            "field_context_correct": feedback.field_context_correct,
            "sensor_issue_reported": feedback.sensor_issue_reported,
            "sensor_issue_notes": feedback.sensor_issue_notes,
            "expert_followup_requested": feedback.expert_followup_requested,
            "cited_agent_outputs": feedback.cited_agent_outputs,
            "feedback_comments": feedback.feedback_comments,
            "idempotency_key": idempotency_key,
            "created_at": now_iso,
        }

        # Persist feedback
        self.repo.record_human_feedback(feedback_record)

        # Audit log entry
        self.repo.record_system_audit(
            action="RECORD_HUMAN_FEEDBACK",
            actor=feedback_record["farmer_id"],
            entity_type="human_feedback",
            entity_id=feedback_id,
            details={
                "recommendation_id": feedback.recommendation_id,
                "rating": feedback.rating,
                "sensor_issue_reported": feedback.sensor_issue_reported,
                "expert_followup_requested": feedback.expert_followup_requested,
                "online_prompt_mutation": False,  # Hard invariant: zero online mutation
                "online_threshold_mutation": False,
            },
        )

        logger.info(
            "Feedback recorded for advisory %s (rating: %d/5, sensor_issue: %s). Offline learning pipeline queryable.",
            feedback.recommendation_id,
            feedback.rating,
            feedback.sensor_issue_reported,
        )

        return True, feedback_record, "Feedback recorded successfully for offline Stage 20 evaluation."

