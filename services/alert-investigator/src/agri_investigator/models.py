"""Pydantic v2 data models, enums, and message contracts for the Multi-Agent Investigation Architecture.

Defines the versioned AgentMessage contract, workflow states, and all specialist agent
input and output schemas adhering strictly to professor feedback.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class WorkflowState(str, Enum):
    """Explicit state machine workflow states."""
    RECEIVED = "received"
    QUEUED = "queued"
    CHECKING_RELIABILITY = "checking_reliability"
    COLLECTING_FIELD_CONTEXT = "collecting_field_context"
    ANALYSING_RISK = "analysing_risk"
    RETRIEVING_EVIDENCE = "retrieving_evidence"
    DRAFTING_ADVISORY = "drafting_advisory"
    CRITIC_REVIEW = "critic_review"
    REVISION_REQUESTED = "revision_requested"
    AWAITING_HUMAN_REVIEW = "awaiting_human_review"
    APPROVED_BY_HUMAN = "approved_by_human"
    REJECTED_BY_HUMAN = "rejected_by_human"
    ABSTAINED = "abstained"
    FAILED = "failed"
    COMPLETED = "completed"


class AgentRole(str, Enum):
    """Identifiable agent roles in the multi-agent investigation system."""
    SUPERVISOR = "supervisor"
    SENSOR_RELIABILITY = "sensor_reliability_agent"
    FIELD_CONTEXT = "field_context_agent"
    CROP_RISK_ANALYST = "crop_risk_analyst_agent"
    AGRONOMY_KNOWLEDGE = "agronomy_knowledge_agent"
    AGRICULTURAL_ADVISORY = "agricultural_advisory_agent"
    CRITIC_SAFETY = "critic_safety_agent"


class MessageType(str, Enum):
    """Types of messages exchanged between supervisor and specialist agents."""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    REVISION_REQUEST = "revision_request"
    REVISION_RESPONSE = "revision_response"
    SUPERVISOR_DECISION = "supervisor_decision"
    ERROR_NOTIFICATION = "error_notification"


class CriticVerdict(str, Enum):
    """Critic / Safety Agent evaluation verdict."""
    APPROVED_FOR_HUMAN_REVIEW = "approved_for_human_review"
    REVISION_REQUIRED = "revision_required"
    REJECTED = "rejected"
    ABSTAIN = "abstain"


class AgentMessage(BaseModel):
    """Versioned, immutable message contract for all agent interactions."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    correlation_id: str
    parent_message_id: Optional[str] = None
    from_agent: str
    to_agent: str
    message_type: MessageType
    payload_schema_version: str = "1.0.0"
    payload: Dict[str, Any]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deadline: Optional[datetime] = None
    idempotency_key: str
    status: str = "ACCEPTED"  # "ACCEPTED", "REJECTED", "ERROR"
    error_details: Optional[Dict[str, Any]] = None


# =============================================================================
# Specialist Agent Output Models
# =============================================================================

class SensorReliabilityOutput(BaseModel):
    """Output contract for Sensor Reliability Agent."""
    is_trustworthy: bool
    proceed_to_agronomy: bool
    sensor_health_state: str  # e.g., "HEALTHY", "DEGRADED", "SUSPECT", "FAULTY"
    reason_code: str          # e.g., "ALL_SENSORS_VALID", "NATURAL_RAIN_ZERO", "STUCK_VALUE_DETECTED"
    trusted_inputs: List[str] = Field(default_factory=list)
    untrusted_inputs: List[str] = Field(default_factory=list)
    evidence_references: List[str] = Field(default_factory=list)
    uncertainty_score: float = Field(ge=0.0, le=1.0)
    summary: str


class FieldContextOutput(BaseModel):
    """Output contract for Field Context Agent."""
    field_id: str
    crop_variety: str
    growth_stage: str
    soil_type: str
    irrigation_type: str
    field_capacity: float
    permanent_wilting_point: float
    recent_weather_context: Dict[str, Any] = Field(default_factory=dict)
    missing_fields: List[str] = Field(default_factory=list)
    applicability_limitations: List[str] = Field(default_factory=list)
    provenance_sources: Dict[str, str] = Field(default_factory=dict)


class AgronomyEvidenceRequest(BaseModel):
    """Structured evidence request formulated by Crop Risk Analyst for Agronomy Knowledge Agent."""
    query: str
    topics: List[str] = Field(default_factory=list)
    target_crop: str
    growth_stage: str
    soil_type: Optional[str] = None
    region: Optional[str] = None
    specific_questions: List[str] = Field(default_factory=list)


class CropRiskAnalystOutput(BaseModel):
    """Output contract for Crop Risk Analyst Agent."""
    risk_hypothesis: str
    severity: str        # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    risk_category: str   # "MOISTURE_DEFICIT", "HEAT_STRESS", "FUNGAL_BLAST_RISK", "COMBINED_STRESS"
    deterministic_csi: float = Field(ge=0.0, le=1.0)
    supporting_feature_ids: List[str] = Field(default_factory=list)
    contradictory_evidence: List[str] = Field(default_factory=list)
    uncertainty_score: float = Field(ge=0.0, le=1.0)
    evidence_request: AgronomyEvidenceRequest


class AdvisoryProposalOutput(BaseModel):
    """Output contract for Agricultural Advisory Agent."""
    action_category: str       # "IRRIGATION", "SOIL_CONSERVATION", "FIELD_INSPECTION", "MONITORING"
    action_title: str
    action_body: str
    urgency: str               # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    cited_evidence_ids: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    when_to_seek_expert: str
    next_step: str


class CriticReviewOutput(BaseModel):
    """Output contract for Critic / Safety Agent."""
    verdict: CriticVerdict
    findings: List[str] = Field(default_factory=list)
    failed_checks: List[str] = Field(default_factory=list)
    target_agent_for_revision: Optional[str] = None
    revision_instructions: Optional[str] = None
    evidence_consistency_score: float = Field(ge=0.0, le=1.0)


class DeterministicSafetyResult(BaseModel):
    """Output contract for external deterministic non-LLM safety gates."""
    passed: bool
    gate_name: str
    violations: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Canonical Shared Investigation State
# =============================================================================

class InvestigationState(BaseModel):
    """Canonical shared investigation state maintained and validated by the Supervisor."""
    run_id: str
    alert_id: str
    field_id: str
    current_state: WorkflowState = WorkflowState.RECEIVED
    revision_count: int = 0
    max_revisions: int = 2
    candidate_alert: Dict[str, Any]
    sensor_reliability: Optional[SensorReliabilityOutput] = None
    field_context: Optional[FieldContextOutput] = None
    risk_assessment: Optional[CropRiskAnalystOutput] = None
    evidence_bundle: Optional[Dict[str, Any]] = None
    advisory_proposal: Optional[AdvisoryProposalOutput] = None
    critic_review: Optional[CriticReviewOutput] = None
    safety_gate_result: Optional[DeterministicSafetyResult] = None
    final_decision: str = "IN_PROGRESS"
    abstention_reason: Optional[str] = None
    audit_trail: List[Dict[str, Any]] = Field(default_factory=list)
    messages: List[AgentMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

