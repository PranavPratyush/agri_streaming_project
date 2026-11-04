"""Farmer advisory proposals, human decision actions, feedback, and notification dispatch endpoints."""

from __future__ import annotations

import datetime
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from agri_api.auth import AuthenticatedUser, get_current_user, require_agronomist_or_admin, verify_field_access
from agri_api.dependencies import get_repository
from agri_api.models.advisories import (
    AdvisoryResponse,
    HumanDecisionRequest,
    HumanDecisionResponse,
    HumanFeedbackRequest,
    HumanFeedbackResponse,
    NotificationDispatchResponse,
)
from agri_api.models.common import PaginatedResponse
from agri_notifications.feedback import FeedbackProcessor
from agri_notifications.lifecycle import HumanReviewLifecycleManager
from agri_notifications.models import (
    HumanReviewActionRequest,
    ReviewAction,
    StructuredFeedbackInput,
)

router = APIRouter(tags=["Advisories & Feedback"])


@router.get("/advisories", response_model=PaginatedResponse[AdvisoryResponse], summary="List proposed or resolved farmer advisories")
def list_advisories(
    field_id: Optional[str] = Query(None, description="Filter by field parcel"),
    approval_status: Optional[str] = Query(None, description="Filter by approval status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    if field_id:
        verify_field_access(field_id, current_user)

    recs = repo.list_farmer_recommendations(field_id=field_id, approval_status=approval_status, limit=limit + offset)
    if not current_user.is_agronomist():
        recs = [r for r in recs if current_user.can_access_field(r["field_id"])]

    total = len(recs)
    sliced = recs[offset : offset + limit]
    return PaginatedResponse(
        items=[
            AdvisoryResponse(
                recommendation_id=r["recommendation_id"],
                alert_id=r.get("alert_id", "alert-unspecified"),
                field_id=r["field_id"],
                investigation_id=r.get("investigation_id"),
                approval_status=r.get("approval_status", "PROPOSED"),
                advisory_version=int(r.get("advisory_version", 1)),
                action_category=r.get("action_category", "IRRIGATION"),
                action_title=r.get("action_title", "Advisory"),
                action_body=r.get("action_body", ""),
                urgency=r.get("urgency", "MEDIUM"),
                cited_evidence_ids=r.get("cited_evidence_ids", []),
                assumptions=r.get("assumptions", []),
                limitations=r.get("limitations", []),
                confidence_score=float(r.get("confidence_score", 0.85)),
                when_to_seek_expert=r.get("when_to_seek_expert"),
                next_step=r.get("next_step"),
                expiry_time=r.get("expiry_time"),
                approved_by=r.get("approved_by"),
                approved_at=r.get("approved_at"),
                created_at=str(r.get("created_at")),
            )
            for r in sliced
        ],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.get("/advisories/{recommendation_id}", response_model=AdvisoryResponse, summary="Get advisory proposal details")
def get_advisory(
    recommendation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    rec = repo.get_recommendation_by_id(recommendation_id)
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Advisory recommendation '{recommendation_id}' not found.",
        )
    verify_field_access(rec["field_id"], current_user)
    return AdvisoryResponse(
        recommendation_id=rec["recommendation_id"],
        alert_id=rec["alert_id"],
        field_id=rec["field_id"],
        investigation_id=rec.get("investigation_id"),
        approval_status=rec.get("approval_status", "PROPOSED"),
        advisory_version=int(rec.get("advisory_version", 1)),
        action_category=rec.get("action_category", "IRRIGATION"),
        action_title=rec.get("action_title", "Advisory"),
        action_body=rec.get("action_body", ""),
        urgency=rec.get("urgency", "MEDIUM"),
        cited_evidence_ids=rec.get("cited_evidence_ids", []),
        assumptions=rec.get("assumptions", []),
        limitations=rec.get("limitations", []),
        confidence_score=float(rec.get("confidence_score", 0.85)),
        when_to_seek_expert=rec.get("when_to_seek_expert"),
        next_step=rec.get("next_step"),
        expiry_time=rec.get("expiry_time"),
        approved_by=rec.get("approved_by"),
        approved_at=rec.get("approved_at"),
        created_at=str(rec.get("created_at")),
    )


@router.post("/advisories/{recommendation_id}/action", response_model=HumanDecisionResponse, summary="Submit human decision action on an advisory")
def submit_advisory_action(
    recommendation_id: str,
    payload: HumanDecisionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    require_agronomist_or_admin(current_user)
    rec = repo.get_recommendation_by_id(recommendation_id)
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Advisory recommendation '{recommendation_id}' not found.",
        )
    verify_field_access(rec["field_id"], current_user)

    action_norm = payload.action.upper().strip()
    try:
        review_action = ReviewAction(action_norm)
    except ValueError:
        valid_actions = [a.value for a in ReviewAction]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action '{payload.action}'. Permitted actions: {valid_actions}.",
        )

    lifecycle = HumanReviewLifecycleManager(repository=repo)
    review_req = HumanReviewActionRequest(
        action=review_action,
        reviewer_id=payload.reviewer_id or current_user.user_id,
        advisory_version=payload.advisory_version,
        reason=payload.comments,
        idempotency_key=payload.idempotency_key or str(uuid.uuid4()),
    )
    success, res, code = lifecycle.apply_action(recommendation_id, review_req)
    if not success and code != 200:
        raise HTTPException(status_code=code, detail=res.message)

    return HumanDecisionResponse(
        success=res.success,
        recommendation_id=res.recommendation_id,
        resulting_status=res.resulting_status,
        action_taken=action_norm,
        advisory_version=res.advisory_version,
        approved_by=res.reviewer_id,
        timestamp=res.timestamp,
        actuation_command_dispatched=res.actuation_command_dispatched,
        message=res.message,
    )


@router.get("/feedback", response_model=PaginatedResponse[HumanFeedbackResponse], summary="List recorded farmer feedback")
def list_feedback(
    field_id: Optional[str] = Query(None, description="Filter by field parcel"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    if field_id:
        verify_field_access(field_id, current_user)

    feedbacks = repo.list_human_feedback(field_id=field_id, limit=limit + offset)
    if not current_user.is_agronomist():
        feedbacks = [f for f in feedbacks if current_user.can_access_field(f["field_id"])]

    total = len(feedbacks)
    sliced = feedbacks[offset : offset + limit]
    return PaginatedResponse(
        items=[
            HumanFeedbackResponse(
                feedback_id=f["feedback_id"],
                recommendation_id=f["recommendation_id"],
                field_id=f["field_id"],
                rating=int(f.get("rating", 5)),
                status="RECORDED",
                advisory_relevant=bool(f.get("advisory_relevant", True)),
                evidence_useful=bool(f.get("evidence_useful", True)),
                sensor_issue_reported=bool(f.get("sensor_issue_reported", False)),
                expert_followup_requested=bool(f.get("expert_followup_requested", False)),
                created_at=str(f.get("created_at")),
            )
            for f in sliced
        ],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.post("/feedback", response_model=HumanFeedbackResponse, status_code=status.HTTP_201_CREATED, summary="Submit farmer feedback on executed advisory")
def submit_feedback(
    payload: HumanFeedbackRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    verify_field_access(payload.field_id, current_user)
    processor = FeedbackProcessor(repository=repo)
    fb_input = StructuredFeedbackInput(
        recommendation_id=payload.recommendation_id,
        field_id=payload.field_id,
        farmer_id=current_user.user_id,
        investigation_id=payload.investigation_id,
        alert_id=payload.alert_id,
        advisory_version=payload.advisory_version,
        rating=payload.rating,
        action_taken=payload.action_taken,
        observed_outcome=payload.observed_outcome,
        advisory_relevant=payload.advisory_relevant,
        evidence_useful=payload.evidence_useful,
        field_context_correct=payload.field_context_correct,
        sensor_issue_reported=payload.sensor_issue_reported,
        sensor_issue_notes=payload.sensor_issue_notes,
        expert_followup_requested=payload.expert_followup_requested,
        cited_agent_outputs=payload.cited_agent_outputs,
        feedback_comments=payload.feedback_comments,
        idempotency_key=payload.idempotency_key,
    )
    success, record, msg = processor.record_feedback(fb_input)

    return HumanFeedbackResponse(
        feedback_id=record["feedback_id"],
        recommendation_id=record["recommendation_id"],
        field_id=record["field_id"],
        rating=record["rating"],
        status="RECORDED",
        advisory_relevant=record["advisory_relevant"],
        evidence_useful=record["evidence_useful"],
        sensor_issue_reported=record["sensor_issue_reported"],
        expert_followup_requested=record["expert_followup_requested"],
        created_at=record["created_at"],
    )


@router.get("/notifications/dispatches", response_model=PaginatedResponse[NotificationDispatchResponse], summary="List notification dispatches for audit")
def list_dispatches(
    recipient_id: Optional[str] = Query(None, description="Filter by recipient"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by delivery status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    require_agronomist_or_admin(current_user)
    dispatches = repo.list_notification_dispatches(recipient_id=recipient_id, status=status_filter, limit=limit + offset)
    total = len(dispatches)
    sliced = dispatches[offset : offset + limit]
    return PaginatedResponse(
        items=[
            NotificationDispatchResponse(
                dispatch_id=d["dispatch_id"],
                alert_id=d["alert_id"],
                investigation_id=d.get("investigation_id"),
                recommendation_id=d.get("recommendation_id"),
                advisory_version=int(d.get("advisory_version", 1)),
                recipient_id=d["recipient_id"],
                channel=d["channel"],
                status=d["status"],
                attempts=int(d.get("attempts", 1)),
                max_retries=int(d.get("max_retries", 3)),
                delivered_at=d.get("delivered_at"),
                payload=d.get("payload", {}),
                error_message=d.get("error_message"),
                created_at=str(d.get("created_at")),
            )
            for d in sliced
        ],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )
