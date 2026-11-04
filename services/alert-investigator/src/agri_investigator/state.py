"""Investigation state machine and transition validation.

Enforces valid transition paths across the 15 workflow states, rejecting illegal
jumps and recording transition audit records.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field

from agri_investigator.models import InvestigationState, WorkflowState


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal transition is attempted in the investigation workflow."""
    def __init__(self, from_state: WorkflowState, to_state: WorkflowState, reason: str = ""):
        msg = f"Invalid state transition from '{from_state.value}' to '{to_state.value}'."
        if reason:
            msg += f" Reason: {reason}"
        super().__init__(msg)
        self.from_state = from_state
        self.to_state = to_state


class StateTransitionRecord(BaseModel):
    """Immutable audit record of a workflow state transition."""
    from_state: WorkflowState
    to_state: WorkflowState
    triggered_by: str
    reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Explicit Transition Matrix
# Any transition not listed here will be rejected immediately.
VALID_TRANSITIONS: Dict[WorkflowState, Set[WorkflowState]] = {
    WorkflowState.RECEIVED: {
        WorkflowState.QUEUED,
        WorkflowState.FAILED,
    },
    WorkflowState.QUEUED: {
        WorkflowState.CHECKING_RELIABILITY,
        WorkflowState.COLLECTING_FIELD_CONTEXT,
        WorkflowState.FAILED,
    },
    WorkflowState.CHECKING_RELIABILITY: {
        WorkflowState.COLLECTING_FIELD_CONTEXT,
        WorkflowState.ANALYSING_RISK,
        WorkflowState.ABSTAINED,
        WorkflowState.FAILED,
    },
    WorkflowState.COLLECTING_FIELD_CONTEXT: {
        WorkflowState.CHECKING_RELIABILITY,
        WorkflowState.ANALYSING_RISK,
        WorkflowState.ABSTAINED,
        WorkflowState.FAILED,
    },
    WorkflowState.ANALYSING_RISK: {
        WorkflowState.RETRIEVING_EVIDENCE,
        WorkflowState.ABSTAINED,
        WorkflowState.FAILED,
    },
    WorkflowState.RETRIEVING_EVIDENCE: {
        WorkflowState.DRAFTING_ADVISORY,
        WorkflowState.REVISION_REQUESTED,
        WorkflowState.ABSTAINED,
        WorkflowState.FAILED,
    },
    WorkflowState.DRAFTING_ADVISORY: {
        WorkflowState.CRITIC_REVIEW,
        WorkflowState.REVISION_REQUESTED,
        WorkflowState.ABSTAINED,
        WorkflowState.FAILED,
    },
    WorkflowState.CRITIC_REVIEW: {
        WorkflowState.AWAITING_HUMAN_REVIEW,
        WorkflowState.REVISION_REQUESTED,
        WorkflowState.ABSTAINED,
        WorkflowState.FAILED,
    },
    WorkflowState.REVISION_REQUESTED: {
        WorkflowState.RETRIEVING_EVIDENCE,
        WorkflowState.DRAFTING_ADVISORY,
        WorkflowState.CRITIC_REVIEW,
        WorkflowState.ABSTAINED,
        WorkflowState.FAILED,
    },
    WorkflowState.AWAITING_HUMAN_REVIEW: {
        WorkflowState.APPROVED_BY_HUMAN,
        WorkflowState.REJECTED_BY_HUMAN,
        WorkflowState.COMPLETED,
    },
    WorkflowState.APPROVED_BY_HUMAN: {
        WorkflowState.COMPLETED,
    },
    WorkflowState.REJECTED_BY_HUMAN: {
        WorkflowState.COMPLETED,
    },
    # Terminal States
    WorkflowState.ABSTAINED: set(),
    WorkflowState.FAILED: set(),
    WorkflowState.COMPLETED: set(),
}


def validate_transition(from_state: WorkflowState, to_state: WorkflowState, reason: str = "") -> None:
    """Validates whether a transition from from_state to to_state is permissible."""
    allowed_targets = VALID_TRANSITIONS.get(from_state, set())
    if to_state not in allowed_targets:
        raise InvalidStateTransitionError(from_state, to_state, reason=reason)


def transition_state(
    state: InvestigationState,
    target_state: WorkflowState,
    triggered_by: str,
    reason: Optional[str] = None,
) -> StateTransitionRecord:
    """Executes a validated transition on an InvestigationState instance."""
    validate_transition(state.current_state, target_state, reason=reason or "")
    
    record = StateTransitionRecord(
        from_state=state.current_state,
        to_state=target_state,
        triggered_by=triggered_by,
        reason=reason,
    )
    
    state.current_state = target_state
    state.updated_at = datetime.now(timezone.utc)
    state.audit_trail.append({
        "type": "state_transition",
        "from_state": record.from_state.value,
        "to_state": record.to_state.value,
        "triggered_by": record.triggered_by,
        "reason": record.reason,
        "timestamp": record.timestamp.isoformat(),
    })
    
    return record

