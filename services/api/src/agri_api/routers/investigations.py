"""Multi-agent alert investigation and supervisor coordination endpoints."""

from __future__ import annotations

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from agri_api.auth import AuthenticatedUser, get_current_user, require_agronomist_or_admin, verify_field_access
from agri_api.dependencies import get_repository, get_supervisor
from agri_api.models.advisories import HumanDecisionRequest, HumanDecisionResponse
from agri_api.models.investigations import (
    AgentHandoffSummary,
    CitationReferenceResponse,
    InvestigationCreateRequest,
    InvestigationSummaryResponse,
    StateTimelineEvent,
)
from agri_investigator.models import AgentRole, WorkflowState
from agri_investigator.supervisor import MultiAgentSupervisor

router = APIRouter(prefix="/investigations", tags=["Multi-Agent Investigations"])


def _sanitize_run_summary(run: dict) -> InvestigationSummaryResponse:
    """Helper to format a persisted multi-agent run into a sanitized public summary."""
    state_payload = run.get("state_payload", {})
    if not isinstance(state_payload, dict):
        state_payload = {}

    rel_output = state_payload.get("sensor_reliability")
    risk_output = state_payload.get("risk_assessment")
    adv_output = state_payload.get("advisory_proposal")
    critic_output = state_payload.get("critic_review")
    safety_output = state_payload.get("safety_gate_result")

    # Sanitized preview (no private chain-of-thought or raw prompts)
    adv_preview = None
    if adv_output:
        adv_preview = {
            "title": adv_output.get("action_title"),
            "category": adv_output.get("action_category"),
            "urgency": adv_output.get("urgency"),
            "confidence": adv_output.get("confidence_score"),
            "citations": adv_output.get("cited_evidence_ids", []),
            "next_step": adv_output.get("next_step"),
        }

    return InvestigationSummaryResponse(
        run_id=str(run["run_id"]),
        alert_id=str(run["alert_id"]),
        field_id=run["field_id"],
        current_state=run.get("current_state", "received"),
        final_decision=run.get("final_decision", "IN_PROGRESS"),
        revision_count=int(run.get("revision_count", 0)),
        max_revisions=int(run.get("max_revisions", 2)),
        abstention_reason=run.get("abstention_reason"),
        summary_title=run.get("summary") or (adv_output.get("action_title") if adv_output else None),
        reliability_assessment={
            "is_trustworthy": rel_output.get("is_trustworthy"),
            "health_state": rel_output.get("sensor_health_state"),
            "reason_code": rel_output.get("reason_code"),
            "summary": rel_output.get("summary"),
        } if rel_output else None,
        risk_assessment={
            "severity": risk_output.get("severity"),
            "category": risk_output.get("risk_category"),
            "deterministic_csi": risk_output.get("deterministic_csi"),
            "hypothesis": risk_output.get("risk_hypothesis"),
        } if risk_output else None,
        advisory_preview=adv_preview,
        critic_verdict=critic_output.get("verdict") if critic_output else None,
        safety_gate_passed=safety_output.get("passed") if safety_output else None,
        created_at=str(run.get("created_at")),
        updated_at=str(run.get("updated_at")),
    )


@router.post("", response_model=InvestigationSummaryResponse, status_code=status.HTTP_201_CREATED, summary="Trigger multi-agent investigation on a candidate alert")
def create_investigation(
    payload: InvestigationCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    supervisor: MultiAgentSupervisor = Depends(get_supervisor),
    repo=Depends(get_repository),
):
    field_id = payload.field_id
    if payload.candidate_alert:
        alert = payload.candidate_alert
        if not field_id:
            field_id = alert.get("field_id", "field-kolar-001")
    else:
        if not payload.alert_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either alert_id or candidate_alert must be provided.",
            )
        alert = repo.get_alert_by_id(payload.alert_id)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate alert '{payload.alert_id}' not found.",
            )
        if not field_id:
            field_id = alert.get("field_id", "field-kolar-001")

    verify_field_access(field_id, current_user)

    # Multi-agent Rule 1: Always invoke investigation through the Supervisor service
    state = supervisor.investigate_alert(alert)

    # Persist farmer recommendation if advisory was formulated
    if state.advisory_proposal and state.current_state == WorkflowState.AWAITING_HUMAN_REVIEW:
        rec_id = str(uuid.uuid4())
        rec_dict = {
            "recommendation_id": rec_id,
            "alert_id": state.alert_id,
            "field_id": state.field_id,
            "investigation_id": state.run_id,
            "approval_status": "PROPOSED",
            "action_category": state.advisory_proposal.action_category,
            "action_title": state.advisory_proposal.action_title,
            "action_body": state.advisory_proposal.action_body,
            "urgency": state.advisory_proposal.urgency,
            "expiry_time": None,
        }
        repo.create_farmer_recommendation(rec_dict)

    repo.record_system_audit(
        action="TRIGGER_INVESTIGATION",
        actor=current_user.user_id,
        entity_type="multi_agent_investigation_run",
        entity_id=state.run_id,
        details={"alert_id": state.alert_id, "final_decision": state.final_decision},
    )

    persisted = repo.get_multi_agent_run(state.run_id)
    if persisted:
        return _sanitize_run_summary(persisted)

    # Fallback to in-memory state object
    return _sanitize_run_summary({
        "run_id": state.run_id,
        "alert_id": state.alert_id,
        "field_id": state.field_id,
        "current_state": state.current_state.value,
        "revision_count": state.revision_count,
        "max_revisions": state.max_revisions,
        "final_decision": state.final_decision,
        "abstention_reason": state.abstention_reason,
        "summary": state.advisory_proposal.action_title if state.advisory_proposal else None,
        "state_payload": state.model_dump(mode="json"),
        "created_at": state.created_at.isoformat(),
        "updated_at": state.updated_at.isoformat(),
    })


@router.get("/{run_id}", response_model=InvestigationSummaryResponse, summary="Get multi-agent investigation run summary")
def get_investigation(
    run_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    run = repo.get_multi_agent_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation run '{run_id}' not found.",
        )
    verify_field_access(run["field_id"], current_user)
    return _sanitize_run_summary(run)


@router.get("/{run_id}/timeline", response_model=List[StateTimelineEvent], summary="Get state machine transition timeline")
def get_investigation_timeline(
    run_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    run = repo.get_multi_agent_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation run '{run_id}' not found.",
        )
    verify_field_access(run["field_id"], current_user)

    transitions = repo.get_run_state_transitions(run_id)
    if not transitions:
        state_payload = run.get("state_payload", {})
        if isinstance(state_payload, dict):
            transitions = state_payload.get("audit_trail", [])

    results = []
    for idx, t in enumerate(transitions, 1):
        results.append(
            StateTimelineEvent(
                transition_id=t.get("transition_id", idx),
                from_state=t["from_state"],
                to_state=t["to_state"],
                triggered_by=t.get("triggered_by", "supervisor"),
                reason=t.get("reason"),
                timestamp=str(t.get("created_at") or t.get("timestamp")),
            )
        )
    return results


@router.get("/{run_id}/messages", response_model=List[AgentHandoffSummary], summary="Get auditable agent handoff summaries")
def get_investigation_messages(
    run_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    run = repo.get_multi_agent_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation run '{run_id}' not found.",
        )
    verify_field_access(run["field_id"], current_user)

    raw_msgs = repo.get_run_messages(run_id)
    if not raw_msgs:
        state_payload = run.get("state_payload", {})
        if isinstance(state_payload, dict):
            raw_msgs = state_payload.get("messages", [])

    summaries: List[AgentHandoffSummary] = []

    for m in raw_msgs:
        payload = m.get("payload", {})
        # Build concise public summary (strictly omit private prompt or hidden chain-of-thought)
        from_ag = m.get("from_agent", "")
        summary_text = "Handoff task or evaluation"
        refs: List[str] = []

        if from_ag == AgentRole.SENSOR_RELIABILITY.value:
            summary_text = f"Evaluated telemetry: health={payload.get('sensor_health_state')}, proceed={payload.get('proceed_to_agronomy')}"
            refs = payload.get("evidence_references", [])
        elif from_ag == AgentRole.FIELD_CONTEXT.value:
            summary_text = f"Retrieved profile: crop={payload.get('crop_variety')}, soil={payload.get('soil_type')}"
        elif from_ag == AgentRole.CROP_RISK_ANALYST.value:
            summary_text = f"Risk hypothesis: {payload.get('risk_hypothesis')} (CSI: {payload.get('deterministic_csi')})"
            refs = payload.get("supporting_feature_ids", [])
        elif from_ag == AgentRole.AGRONOMY_KNOWLEDGE.value:
            summary_text = f"Retrieved {payload.get('total_chunks', 0)} chunks. Status: {payload.get('evidence_status')}"
            refs = [c.get("citation_id") for c in payload.get("chunks", []) if "citation_id" in c]
        elif from_ag == AgentRole.AGRICULTURAL_ADVISORY.value:
            summary_text = f"Formulated proposal: {payload.get('action_title')}"
            refs = payload.get("cited_evidence_ids", [])
        elif from_ag == AgentRole.CRITIC_SAFETY.value:
            summary_text = f"Critic verdict: {payload.get('verdict')}. Findings count: {len(payload.get('findings', []))}"
        elif from_ag == AgentRole.SUPERVISOR.value:
            summary_text = f"Supervisor routed task to {m.get('to_agent')}"

        summaries.append(
            AgentHandoffSummary(
                message_id=str(m["message_id"]),
                from_agent=from_ag,
                to_agent=m.get("to_agent", ""),
                message_type=m.get("message_type", ""),
                status=m.get("status", "ACCEPTED"),
                created_at=str(m.get("created_at")),
                concise_summary=summary_text,
                evidence_references=refs,
            )
        )
    return summaries


@router.get("/{run_id}/citations", response_model=List[CitationReferenceResponse], summary="Get validated evidence and citations")
def get_investigation_citations(
    run_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    run = repo.get_multi_agent_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation run '{run_id}' not found.",
        )
    verify_field_access(run["field_id"], current_user)

    state_payload = run.get("state_payload", {})
    ev_bundle = state_payload.get("evidence_bundle", {})
    chunks = ev_bundle.get("chunks", [])

    results: List[CitationReferenceResponse] = []
    for c in chunks:
        results.append(
            CitationReferenceResponse(
                citation_id=c.get("citation_id", "unknown"),
                source_id=c.get("source_id", "unknown"),
                document_title=c.get("document_title", "Agronomy Reference"),
                section_heading=c.get("section_heading", ""),
                canonical_url=c.get("canonical_url", ""),
                relevance_score=float(c.get("relevance_score", 0.0)),
                excerpt=c.get("text", "")[:300],
            )
        )
    return results


@router.post("/{run_id}/human-decision", response_model=HumanDecisionResponse, summary="Record human approval or rejection on an advisory")
def submit_human_decision(
    run_id: str,
    payload: HumanDecisionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    supervisor: MultiAgentSupervisor = Depends(get_supervisor),
    repo=Depends(get_repository),
):
    run = repo.get_multi_agent_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation run '{run_id}' not found.",
        )
    verify_field_access(run["field_id"], current_user)

    # Multi-agent Rule 3: Status must reflect persisted state machine
    current_st = run.get("current_state")
    if current_st != WorkflowState.AWAITING_HUMAN_REVIEW.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot submit human decision: Investigation is in state '{current_st}', expected '{WorkflowState.AWAITING_HUMAN_REVIEW.value}'.",
        )

    action_norm = payload.action.upper().strip()
    valid_actions = ("APPROVE", "REJECT", "REQUEST_INSPECTION", "ACKNOWLEDGE")
    if action_norm not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action '{payload.action}'. Permitted actions: {valid_actions}.",
        )

    is_approved = action_norm in ("APPROVE", "APPROVED")
    reviewer_id = payload.reviewer_id or current_user.user_id
    idempotency_key = payload.idempotency_key or str(uuid.uuid4())

    # Multi-agent Rule 6: A human decision must NOT trigger automated physical actuation
    # Execute state machine transition
    resulting_state = WorkflowState.APPROVED_BY_HUMAN.value if is_approved else WorkflowState.REJECTED_BY_HUMAN.value
    repo.update_multi_agent_run(
        run_id=run_id,
        updates={
            "current_state": WorkflowState.COMPLETED.value,
            "final_decision": resulting_state,
            "abstention_reason": None if is_approved else f"Rejected by human: {payload.comments}",
        },
    )

    # Update associated farmer recommendation
    recs = repo.list_farmer_recommendations(field_id=run["field_id"], limit=5)
    matching_rec = next((r for r in recs if r.get("investigation_id") == run_id), None)
    if matching_rec:
        repo.update_recommendation_status(
            recommendation_id=matching_rec["recommendation_id"],
            status="APPROVED" if is_approved else "REJECTED",
            approved_by=reviewer_id,
        )

    repo.record_system_audit(
        action=f"HUMAN_{action_norm}",
        actor=reviewer_id,
        entity_type="multi_agent_investigation_run",
        entity_id=run_id,
        details={
            "action": action_norm,
            "comments": payload.comments,
            "idempotency_key": idempotency_key,
        },
    )

    return HumanDecisionResponse(
        success=True,
        recommendation_id=matching_rec["recommendation_id"] if matching_rec else run_id,
        resulting_status=resulting_state,
        action_taken=action_norm,
        approved_by=reviewer_id,
        timestamp=str(run.get("updated_at")),
        message=f"Human decision '{action_norm}' successfully recorded. Zero autonomous actuation was dispatched.",
    )
