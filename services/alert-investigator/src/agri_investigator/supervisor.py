"""Supervisor / Coordinator implementation for the Multi-Agent Investigation Architecture.

Controls message routing, workflow transitions, parallel fan-out/fan-in, revision cycles,
deterministic safety gating, and state persistence.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from agri_investigator.agents.agricultural_advisory import AgriculturalAdvisoryAgent, AgriculturalAdvisoryInput
from agri_investigator.agents.agronomy_knowledge import AgronomyKnowledgeAgent, AgronomyKnowledgeInput, AgronomyKnowledgeOutput
from agri_investigator.agents.crop_risk_analyst import CropRiskAnalystAgent, CropRiskAnalystInput
from agri_investigator.agents.critic_safety import CriticSafetyAgent, CriticSafetyInput
from agri_investigator.agents.field_context import FieldContextAgent, FieldContextInput
from agri_investigator.agents.sensor_reliability import SensorReliabilityAgent, SensorReliabilityInput
from agri_investigator.models import (
    AdvisoryProposalOutput,
    AgentMessage,
    AgentRole,
    CropRiskAnalystOutput,
    CriticReviewOutput,
    CriticVerdict,
    FieldContextOutput,
    InvestigationState,
    MessageType,
    SensorReliabilityOutput,
    WorkflowState,
)
from agri_investigator.protocol import MessageRouter, create_agent_message
from agri_investigator.safety import DeterministicSafetyGate
from agri_investigator.state import transition_state
from agri_shared.metrics import (
    MULTI_AGENT_ABSTENTIONS_TOTAL,
    MULTI_AGENT_AGENT_DURATION_SECONDS,
    MULTI_AGENT_HANDOFFS_TOTAL,
    MULTI_AGENT_INVOCATIONS_TOTAL,
    MULTI_AGENT_REVISIONS_TOTAL,
    MULTI_AGENT_RUN_DURATION_SECONDS,
)

logger = logging.getLogger(__name__)


class MultiAgentSupervisor:
    """The central coordinator managing multi-agent investigation workflows."""

    def __init__(
        self,
        sensor_reliability_agent: Optional[SensorReliabilityAgent] = None,
        field_context_agent: Optional[FieldContextAgent] = None,
        crop_risk_analyst_agent: Optional[CropRiskAnalystAgent] = None,
        agronomy_knowledge_agent: Optional[AgronomyKnowledgeAgent] = None,
        agricultural_advisory_agent: Optional[AgriculturalAdvisoryAgent] = None,
        critic_safety_agent: Optional[CriticSafetyAgent] = None,
        persistence_repo: Optional[Any] = None,
        max_revisions: int = 2,
        chroma_dir: Optional[Path] = None,
    ) -> None:
        self.sensor_reliability = sensor_reliability_agent or SensorReliabilityAgent()
        self.field_context = field_context_agent or FieldContextAgent()
        self.crop_risk_analyst = crop_risk_analyst_agent or CropRiskAnalystAgent()
        self.agronomy_knowledge = agronomy_knowledge_agent or AgronomyKnowledgeAgent(chroma_dir=chroma_dir)
        self.agricultural_advisory = agricultural_advisory_agent or AgriculturalAdvisoryAgent()
        self.critic_safety = critic_safety_agent or CriticSafetyAgent()

        self.persistence = persistence_repo
        self.max_revisions = max_revisions
        self.router = MessageRouter()

    def _route_and_record(
        self,
        state: InvestigationState,
        from_agent: str,
        to_agent: str,
        message_type: MessageType,
        payload: Dict[str, Any],
        parent_id: Optional[str] = None,
    ) -> AgentMessage:
        """Creates, validates, and appends an AgentMessage to the run state."""
        msg = create_agent_message(
            run_id=state.run_id,
            correlation_id=state.candidate_alert.get("alert_id", state.run_id),
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            payload=payload,
            parent_message_id=parent_id,
            revision_count=state.revision_count,
        )
        self.router.check_and_register(msg)
        state.messages.append(msg)

        # Update metrics
        MULTI_AGENT_HANDOFFS_TOTAL.labels(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type.value,
        ).inc()

        # Persist message if DB repository is available
        if self.persistence:
            try:
                self.persistence.record_agent_message(msg.model_dump())
            except Exception as e:
                logger.warning("Failed persisting agent message: %s", e)

        return msg

    def _record_transition(
        self,
        state: InvestigationState,
        target_state: WorkflowState,
        reason: Optional[str] = None,
    ) -> None:
        """Transitions state machine and persists the record."""
        rec = transition_state(state, target_state, triggered_by=AgentRole.SUPERVISOR.value, reason=reason)
        if self.persistence:
            try:
                self.persistence.record_state_transition({
                    "run_id": state.run_id,
                    "from_state": rec.from_state.value,
                    "to_state": rec.to_state.value,
                    "triggered_by": rec.triggered_by,
                    "reason": rec.reason,
                })
            except Exception as e:
                logger.warning("Failed persisting state transition: %s", e)

    def _persist_state_snapshot(self, state: InvestigationState) -> None:
        """Persists current state snapshot to database repository."""
        if not self.persistence:
            return
        try:
            rel_score = (
                1.0 - state.sensor_reliability.uncertainty_score
                if state.sensor_reliability
                else None
            )
            conf_score = (
                state.advisory_proposal.confidence_score
                if state.advisory_proposal
                else None
            )

            run_dict = {
                "run_id": state.run_id,
                "alert_id": state.alert_id,
                "field_id": state.field_id,
                "current_state": state.current_state.value,
                "revision_count": state.revision_count,
                "max_revisions": state.max_revisions,
                "final_decision": state.final_decision,
                "abstention_reason": state.abstention_reason,
                "summary": state.advisory_proposal.action_title if state.advisory_proposal else None,
                "reliability_score": rel_score,
                "confidence_score": conf_score,
                "candidate_alert": state.candidate_alert,
                "state_payload": state.model_dump(mode="json"),
            }
            self.persistence.create_multi_agent_run(run_dict)
        except Exception as e:
            logger.warning("Failed persisting investigation run: %s", e)

    def investigate_alert(
        self,
        candidate_alert: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> InvestigationState:
        """Orchestrates an end-to-end multi-agent investigation run on a candidate alert."""
        run_start = time.perf_counter()
        run_id = str(uuid.uuid4())
        alert_id = str(candidate_alert.get("alert_id", uuid.uuid4()))
        field_id = str(candidate_alert.get("field_id", "field-kolar-001"))

        state = InvestigationState(
            run_id=run_id,
            alert_id=alert_id,
            field_id=field_id,
            candidate_alert=candidate_alert,
            max_revisions=self.max_revisions,
        )

        try:
            # 1. Received -> Queued
            self._record_transition(state, WorkflowState.QUEUED, reason="Candidate alert queued for multi-agent investigation.")
            self._persist_state_snapshot(state)

            # 2. Fan-out Step: Sensor Reliability and Field Context
            self._record_transition(state, WorkflowState.CHECKING_RELIABILITY, reason="Dispatching sensor reliability audit.")

            # Dispatch to Sensor Reliability Agent
            rel_task = self._route_and_record(
                state=state,
                from_agent=AgentRole.SUPERVISOR.value,
                to_agent=AgentRole.SENSOR_RELIABILITY.value,
                message_type=MessageType.TASK_REQUEST,
                payload=SensorReliabilityInput(
                    candidate_alert=candidate_alert,
                    sensor_health_results=candidate_alert.get("sensor_health_results", []),
                    recent_observations=candidate_alert.get("observations", []),
                    provenance=candidate_alert.get("provenance", "mixed"),
                ).model_dump(),
            )
            rel_resp, rel_dur, _ = self.sensor_reliability.process_task(rel_task)
            MULTI_AGENT_AGENT_DURATION_SECONDS.labels(agent_role=AgentRole.SENSOR_RELIABILITY.value).observe(rel_dur)
            MULTI_AGENT_INVOCATIONS_TOTAL.labels(agent_role=AgentRole.SENSOR_RELIABILITY.value, status=rel_resp.status).inc()
            self.router.check_and_register(rel_resp)
            state.messages.append(rel_resp)
            state.sensor_reliability = SensorReliabilityOutput.model_validate(rel_resp.payload)

            # Dispatch to Field Context Agent
            self._record_transition(state, WorkflowState.COLLECTING_FIELD_CONTEXT, reason="Dispatching field metadata retrieval.")
            ctx_task = self._route_and_record(
                state=state,
                from_agent=AgentRole.SUPERVISOR.value,
                to_agent=AgentRole.FIELD_CONTEXT.value,
                message_type=MessageType.TASK_REQUEST,
                payload=FieldContextInput(
                    field_id=field_id,
                    candidate_alert=candidate_alert,
                    time_window_hours=24,
                ).model_dump(),
            )
            ctx_resp, ctx_dur, _ = self.field_context.process_task(ctx_task)
            MULTI_AGENT_AGENT_DURATION_SECONDS.labels(agent_role=AgentRole.FIELD_CONTEXT.value).observe(ctx_dur)
            MULTI_AGENT_INVOCATIONS_TOTAL.labels(agent_role=AgentRole.FIELD_CONTEXT.value, status=ctx_resp.status).inc()
            self.router.check_and_register(ctx_resp)
            state.messages.append(ctx_resp)
            state.field_context = FieldContextOutput.model_validate(ctx_resp.payload)

            # 3. Sensor Reliability Gate Enforcement
            if not state.sensor_reliability.proceed_to_agronomy:
                abstain_reason = f"SENSOR_FAULT_SUPPRESSION: {state.sensor_reliability.reason_code}"
                state.abstention_reason = abstain_reason
                state.final_decision = "ABSTAINED_SENSOR_FAULT"
                MULTI_AGENT_ABSTENTIONS_TOTAL.labels(reason_code=state.sensor_reliability.reason_code).inc()
                self._record_transition(state, WorkflowState.ABSTAINED, reason=abstain_reason)
                self._persist_state_snapshot(state)
                return state

            # 4. Crop Risk Analysis Step
            self._record_transition(state, WorkflowState.ANALYSING_RISK, reason="Evaluating agronomic risk and formulating evidence request.")
            cf = candidate_alert.get("contributing_features", {})
            if isinstance(cf, list):
                cf = {
                    f.get("feature_name", f"feat_{i}"): f.get("severity", "TRIGGERED") if isinstance(f, dict) else str(f)
                    for i, f in enumerate(cf)
                }
            risk_task = self._route_and_record(
                state=state,
                from_agent=AgentRole.SUPERVISOR.value,
                to_agent=AgentRole.CROP_RISK_ANALYST.value,
                message_type=MessageType.TASK_REQUEST,
                payload=CropRiskAnalystInput(
                    candidate_alert=candidate_alert,
                    reliability_assessment=state.sensor_reliability,
                    field_context=state.field_context,
                    deterministic_risk_features=cf,
                ).model_dump(),
            )
            risk_resp, risk_dur, _ = self.crop_risk_analyst.process_task(risk_task)
            MULTI_AGENT_AGENT_DURATION_SECONDS.labels(agent_role=AgentRole.CROP_RISK_ANALYST.value).observe(risk_dur)
            MULTI_AGENT_INVOCATIONS_TOTAL.labels(agent_role=AgentRole.CROP_RISK_ANALYST.value, status=risk_resp.status).inc()
            self.router.check_and_register(risk_resp)
            state.messages.append(risk_resp)
            state.risk_assessment = CropRiskAnalystOutput.model_validate(risk_resp.payload)

            # 5. Agronomy Knowledge Retrieval Step
            self._record_transition(state, WorkflowState.RETRIEVING_EVIDENCE, reason="Querying Stage 15 RAG retrieval service.")
            know_task = self._route_and_record(
                state=state,
                from_agent=AgentRole.SUPERVISOR.value,
                to_agent=AgentRole.AGRONOMY_KNOWLEDGE.value,
                message_type=MessageType.TASK_REQUEST,
                payload=AgronomyKnowledgeInput(
                    evidence_request=state.risk_assessment.evidence_request,
                    field_context=state.field_context,
                ).model_dump(),
            )
            know_resp, know_dur, _ = self.agronomy_knowledge.process_task(know_task)
            MULTI_AGENT_AGENT_DURATION_SECONDS.labels(agent_role=AgentRole.AGRONOMY_KNOWLEDGE.value).observe(know_dur)
            MULTI_AGENT_INVOCATIONS_TOTAL.labels(agent_role=AgentRole.AGRONOMY_KNOWLEDGE.value, status=know_resp.status).inc()
            self.router.check_and_register(know_resp)
            state.messages.append(know_resp)
            know_output = AgronomyKnowledgeOutput.model_validate(know_resp.payload)
            state.evidence_bundle = know_output.model_dump()

            # 6. Advisory Formulation & Critic Revision Loop
            revision_instructions: Optional[str] = None

            while state.revision_count <= state.max_revisions:
                # 6a. Draft Advisory
                self._record_transition(
                    state,
                    WorkflowState.DRAFTING_ADVISORY,
                    reason=f"Drafting advisory proposal (cycle {state.revision_count}).",
                )
                adv_task = self._route_and_record(
                    state=state,
                    from_agent=AgentRole.SUPERVISOR.value,
                    to_agent=AgentRole.AGRICULTURAL_ADVISORY.value,
                    message_type=(
                        MessageType.REVISION_REQUEST
                        if revision_instructions
                        else MessageType.TASK_REQUEST
                    ),
                    payload=AgriculturalAdvisoryInput(
                        candidate_alert=candidate_alert,
                        risk_assessment=state.risk_assessment,
                        reliability_assessment=state.sensor_reliability,
                        field_context=state.field_context,
                        evidence_output=know_output,
                        revision_notes=revision_instructions,
                    ).model_dump(),
                )
                adv_resp, adv_dur, _ = self.agricultural_advisory.process_task(adv_task)
                MULTI_AGENT_AGENT_DURATION_SECONDS.labels(agent_role=AgentRole.AGRICULTURAL_ADVISORY.value).observe(adv_dur)
                MULTI_AGENT_INVOCATIONS_TOTAL.labels(agent_role=AgentRole.AGRICULTURAL_ADVISORY.value, status=adv_resp.status).inc()
                self.router.check_and_register(adv_resp)
                state.messages.append(adv_resp)
                state.advisory_proposal = AdvisoryProposalOutput.model_validate(adv_resp.payload)

                # 6b. Critic Audit
                self._record_transition(state, WorkflowState.CRITIC_REVIEW, reason="Critic agent evaluating consistency and safety.")
                critic_task = self._route_and_record(
                    state=state,
                    from_agent=AgentRole.SUPERVISOR.value,
                    to_agent=AgentRole.CRITIC_SAFETY.value,
                    message_type=MessageType.TASK_REQUEST,
                    payload=CriticSafetyInput(
                        proposed_advisory=state.advisory_proposal,
                        reliability_assessment=state.sensor_reliability,
                        field_context=state.field_context,
                        risk_assessment=state.risk_assessment,
                        evidence_output=know_output,
                    ).model_dump(),
                )
                critic_resp, critic_dur, _ = self.critic_safety.process_task(critic_task)
                MULTI_AGENT_AGENT_DURATION_SECONDS.labels(agent_role=AgentRole.CRITIC_SAFETY.value).observe(critic_dur)
                MULTI_AGENT_INVOCATIONS_TOTAL.labels(agent_role=AgentRole.CRITIC_SAFETY.value, status=critic_resp.status).inc()
                self.router.check_and_register(critic_resp)
                state.messages.append(critic_resp)
                state.critic_review = CriticReviewOutput.model_validate(critic_resp.payload)

                # 6c. Evaluate Critic Verdict
                if state.critic_review.verdict == CriticVerdict.APPROVED_FOR_HUMAN_REVIEW:
                    break

                if state.critic_review.verdict == CriticVerdict.REVISION_REQUIRED:
                    state.revision_count += 1
                    target_ag = state.critic_review.target_agent_for_revision or AgentRole.AGRICULTURAL_ADVISORY.value
                    reason_code = state.critic_review.failed_checks[0] if state.critic_review.failed_checks else "CRITIC_REVISION"
                    MULTI_AGENT_REVISIONS_TOTAL.labels(target_agent=target_ag, reason_code=reason_code).inc()

                    if state.revision_count > state.max_revisions:
                        abstain_msg = f"MAX_REVISIONS_EXCEEDED ({state.max_revisions} cycles exhausted). Terminating as abstained."
                        state.abstention_reason = abstain_msg
                        state.final_decision = "ABSTAINED_MAX_REVISIONS_EXCEEDED"
                        MULTI_AGENT_ABSTENTIONS_TOTAL.labels(reason_code="MAX_REVISIONS_EXCEEDED").inc()
                        self._record_transition(state, WorkflowState.ABSTAINED, reason=abstain_msg)
                        self._persist_state_snapshot(state)
                        return state

                    # Transition to REVISION_REQUESTED and loop
                    revision_instructions = state.critic_review.revision_instructions
                    self._record_transition(
                        state,
                        WorkflowState.REVISION_REQUESTED,
                        reason=f"Revision cycle {state.revision_count} requested by Critic: {revision_instructions}",
                    )
                    continue

                # Critic REJECT or ABSTAIN
                abstain_reason = f"CRITIC_{state.critic_review.verdict.value.upper()}: {', '.join(state.critic_review.failed_checks)}"
                state.abstention_reason = abstain_reason
                state.final_decision = f"ABSTAINED_{state.critic_review.verdict.value.upper()}"
                MULTI_AGENT_ABSTENTIONS_TOTAL.labels(reason_code=state.critic_review.verdict.value).inc()
                self._record_transition(state, WorkflowState.ABSTAINED, reason=abstain_reason)
                self._persist_state_snapshot(state)
                return state

            # 7. Non-LLM Deterministic Safety Gate Audit
            safety_res = DeterministicSafetyGate.audit_complete_investigation(state)
            state.safety_gate_result = safety_res

            if not safety_res.passed:
                rej_reason = f"DETERMINISTIC_SAFETY_VIOLATION: {', '.join(safety_res.violations)}"
                state.abstention_reason = rej_reason
                state.final_decision = "REJECTED_SAFETY_POLICY_VIOLATION"
                MULTI_AGENT_ABSTENTIONS_TOTAL.labels(reason_code="SAFETY_GATE_VIOLATION").inc()
                self._record_transition(state, WorkflowState.ABSTAINED, reason=rej_reason)
                self._persist_state_snapshot(state)
                return state

            # 8. All Gates Passed -> Awaiting Human Review
            self._record_transition(
                state,
                WorkflowState.AWAITING_HUMAN_REVIEW,
                reason="Advisory certified by Critic and passed all deterministic safety gates.",
            )
            state.final_decision = "AWAITING_HUMAN_REVIEW"
            self._persist_state_snapshot(state)

        except Exception as exc:
            logger.error("Supervisor unhandled exception during run %s: %s", run_id, exc, exc_info=True)
            state.final_decision = "FAILED_EXCEPTION"
            state.abstention_reason = str(exc)
            if state.current_state != WorkflowState.FAILED:
                self._record_transition(state, WorkflowState.FAILED, reason=f"Exception: {str(exc)}")
            self._persist_state_snapshot(state)

        run_dur = time.perf_counter() - run_start
        MULTI_AGENT_RUN_DURATION_SECONDS.labels(final_status=state.current_state.value).observe(run_dur)
        return state

    def submit_human_decision(
        self,
        state: InvestigationState,
        approved: bool,
        reviewer_id: str,
        comments: Optional[str] = None,
    ) -> InvestigationState:
        """Processes human approval or rejection of an advisory awaiting human review."""
        if state.current_state != WorkflowState.AWAITING_HUMAN_REVIEW:
            raise ValueError(
                f"Cannot process human review: Investigation is in state '{state.current_state.value}', "
                f"expected '{WorkflowState.AWAITING_HUMAN_REVIEW.value}'."
            )

        if approved:
            self._record_transition(
                state,
                WorkflowState.APPROVED_BY_HUMAN,
                reason=f"Approved by agronomist/farmer {reviewer_id}. Comments: {comments or 'None'}",
            )
            state.final_decision = "APPROVED_BY_HUMAN"
            self._record_transition(state, WorkflowState.COMPLETED, reason="Workflow completed successfully.")
        else:
            self._record_transition(
                state,
                WorkflowState.REJECTED_BY_HUMAN,
                reason=f"Rejected by agronomist/farmer {reviewer_id}. Comments: {comments or 'None'}",
            )
            state.final_decision = "REJECTED_BY_HUMAN"
            self._record_transition(state, WorkflowState.COMPLETED, reason="Workflow completed with human rejection.")

        self._persist_state_snapshot(state)
        return state
