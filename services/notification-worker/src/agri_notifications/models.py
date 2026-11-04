"""Data models and enums for AgriKafka notifications and human feedback."""

from __future__ import annotations

import enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NotificationChannel(str, enum.Enum):
    PWA_PUSH = "pwa_push"
    MOCK_CHANNEL = "mock_channel"
    TELEGRAM = "telegram"


class DeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


class ReviewAction(str, enum.Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    ACKNOWLEDGE = "ACKNOWLEDGE"
    REQUEST_INSPECTION = "REQUEST_INSPECTION"
    EXPIRE = "EXPIRE"
    SUPERSEDE = "SUPERSEDE"


class AdvisoryStatus(str, enum.Enum):
    PROPOSED = "PROPOSED"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    REQUEST_INSPECTION = "REQUEST_INSPECTION"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"


class NotificationPayload(BaseModel):
    """Normalized payload delivered to farmer notification channels."""
    alert_id: str
    advisory_id: str
    field_id: str
    advisory_version: int = 1
    title: str
    summary: str
    urgency: str = "MEDIUM"
    action_category: str = "MONITORING"
    pwa_deep_link: str
    provenance_caveat: str
    evidence_summary: str = ""
    limitations: List[str] = Field(default_factory=list)
    when_to_seek_expert: Optional[str] = None


class NotificationDispatch(BaseModel):
    """Record of a notification dispatch attempt and delivery tracking."""
    dispatch_id: str
    alert_id: str
    investigation_id: Optional[str] = None
    recommendation_id: Optional[str] = None
    advisory_version: int = 1
    recipient_id: str
    channel: NotificationChannel
    idempotency_key: str
    status: DeliveryStatus = DeliveryStatus.PENDING
    attempts: int = 0
    max_retries: int = 3
    next_retry_at: Optional[str] = None
    delivered_at: Optional[str] = None
    payload: Dict[str, Any]
    provider_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: str
    updated_at: str


class StructuredFeedbackInput(BaseModel):
    """Multi-agent linked structured feedback from farmer or field agronomist."""
    feedback_id: Optional[str] = None
    recommendation_id: str
    field_id: str
    farmer_id: Optional[str] = None
    investigation_id: Optional[str] = None
    alert_id: Optional[str] = None
    advisory_version: int = 1
    rating: int = Field(ge=1, le=5, description="1 to 5 utility rating")
    action_taken: bool = False
    observed_outcome: Optional[str] = None
    advisory_relevant: bool = True
    evidence_useful: bool = True
    field_context_correct: bool = True
    sensor_issue_reported: bool = False
    sensor_issue_notes: Optional[str] = None
    expert_followup_requested: bool = False
    cited_agent_outputs: List[str] = Field(default_factory=list, description="IDs/names of cited agent outputs")
    feedback_comments: Optional[str] = None
    idempotency_key: Optional[str] = None


class HumanReviewActionRequest(BaseModel):
    """Payload to record human decision on an advisory awaiting review."""
    action: ReviewAction
    reviewer_id: Optional[str] = None
    advisory_version: int = 1
    reason: Optional[str] = None
    idempotency_key: Optional[str] = None


class HumanReviewActionResponse(BaseModel):
    """Outcome of human review action, asserting zero physical actuation."""
    success: bool
    recommendation_id: str
    previous_status: str
    resulting_status: str
    advisory_version: int
    reviewer_id: str
    idempotency_key: str
    timestamp: str
    actuation_command_dispatched: bool = False  # Hard invariant: Zero physical actuation
    message: str

