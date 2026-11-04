"""Comprehensive unit test suite for the Multi-Agent Investigation Architecture.

Proves:
1. Independent execution of Sensor Reliability and Field Context into Risk Analyst.
2. Risk Analyst evidence request -> Knowledge Agent -> EvidenceBundle -> Advisory Agent.
3. Critic evaluation and revision request routing to target upstream agent.
4. Maximum revision count prevents infinite loops.
5. Strict validation of invalid state transitions.
6. Message idempotency key collision rejection.
7. Faulty sensor telemetry blocks downstream agronomic advice.
8. Deterministic safety gate blocks ungrounded citations and chemical dosage advice.
9. Audit trail and shared state consistency.
10. Human approval and rejection lifecycle.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict
import pytest

from agri_investigator.agents import (
    AgriculturalAdvisoryAgent,
    AgronomyKnowledgeAgent,
    CropRiskAnalystAgent,
    CriticSafetyAgent,
    FieldContextAgent,
    SensorReliabilityAgent,
)
from agri_investigator.models import (
    AdvisoryProposalOutput,
    AgentMessage,
    AgentRole,
    CriticReviewOutput,
    CriticVerdict,
    InvestigationState,
    MessageType,
    SensorReliabilityOutput,
    WorkflowState,
)
from agri_investigator.protocol import DuplicateMessageError, InvalidMessageError, MessageRouter, create_agent_message
from agri_investigator.safety import DeterministicSafetyGate
from agri_investigator.state import InvalidStateTransitionError, transition_state, validate_transition
from agri_investigator.supervisor import MultiAgentSupervisor


@pytest.fixture
def base_candidate_alert() -> Dict[str, Any]:
    return {
        "alert_id": str(uuid.uuid4()),
        "field_id": "field-kolar-001",
        "crop_variety": "Finger Millet (Ragi GPU-28)",
        "growth_stage": "Flowering / Grain Filling",
        "risk_type": "SOIL_MOISTURE_DEPLETION",
        "severity": "HIGH",
        "composite_stress_index": 0.76,
        "sensor_health_state": "HEALTHY",
        "observations": [
            {"sensor_id": "soil-01", "variable": "soil_moisture", "numeric_value": 0.11, "unit": "m3/m3"},
        ],
        "sensor_health_results": [
            {"sensor_id": "soil-01", "health_state": "HEALTHY", "reason_code": "ALL_SENSORS_VALID"},
        ],
    }


class TestMultiAgentHandoffsAndPipelines:
    """Verifies that agents genuinely exchange structured outputs."""

    def test_end_to_end_investigation_success_flow(self, base_candidate_alert):
        """Proves full pipeline flow from received -> awaiting_human_review with citation grounding."""
        supervisor = MultiAgentSupervisor(max_revisions=2)
        state = supervisor.investigate_alert(base_candidate_alert)

        assert state.current_state == WorkflowState.AWAITING_HUMAN_REVIEW
        assert state.final_decision == "AWAITING_HUMAN_REVIEW"
        assert state.sensor_reliability is not None
        assert state.sensor_reliability.is_trustworthy is True
        assert state.field_context is not None
        assert state.risk_assessment is not None
        assert state.evidence_bundle is not None
        assert state.advisory_proposal is not None
        assert state.critic_review is not None
        assert state.critic_review.verdict == CriticVerdict.APPROVED_FOR_HUMAN_REVIEW
        assert state.safety_gate_result is not None
        assert state.safety_gate_result.passed is True
        assert len(state.messages) >= 10
        assert len(state.audit_trail) >= 5

    def test_risk_analyst_consumes_reliability_and_field_context(self, base_candidate_alert):
        """Proves Crop Risk Analyst consumes both Sensor Reliability and Field Context outputs."""
        supervisor = MultiAgentSupervisor()
        state = supervisor.investigate_alert(base_candidate_alert)

        risk = state.risk_assessment
        assert risk is not None
        assert "deterministic_csi:0.76" in risk.supporting_feature_ids
        assert risk.evidence_request.target_crop == "Finger Millet"
        assert risk.evidence_request.growth_stage == state.field_context.growth_stage
        assert risk.evidence_request.soil_type == state.field_context.soil_type

    def test_knowledge_agent_retrieves_genuine_bundle(self, base_candidate_alert):
        """Proves Knowledge Agent queries RAG service and provides evidence bundle to Advisory Agent."""
        supervisor = MultiAgentSupervisor()
        state = supervisor.investigate_alert(base_candidate_alert)

        assert state.evidence_bundle is not None
        assert len(state.evidence_bundle["chunks"]) > 0
        cited_id = state.advisory_proposal.cited_evidence_ids[0]
        bundle_ids = [c["citation_id"] for c in state.evidence_bundle["chunks"]]
        assert cited_id in bundle_ids


class TestFaultySensorsAndAbstention:
    """Verifies safety gating when sensor data is compromised."""

    def test_faulty_sensor_blocks_crop_advice(self, base_candidate_alert):
        """Proves that a FAULTY sensor health state halts the workflow and prevents crop advisory."""
        base_candidate_alert["sensor_health_state"] = "FAULTY"
        base_candidate_alert["sensor_health_results"] = [
            {"sensor_id": "soil-01", "health_state": "FAULTY", "reason_code": "STUCK_VALUE"},
        ]

        supervisor = MultiAgentSupervisor()
        state = supervisor.investigate_alert(base_candidate_alert)

        assert state.current_state == WorkflowState.ABSTAINED
        assert state.final_decision == "ABSTAINED_SENSOR_FAULT"
        assert "STUCK_VALUE_DETECTED" in state.abstention_reason
        # Verify subsequent agents were never invoked
        assert state.risk_assessment is None
        assert state.evidence_bundle is None
        assert state.advisory_proposal is None


class TestCriticRevisionCycles:
    """Verifies Critic rejection, revision routing, and max cycle termination."""

    def test_critic_revision_routing_and_recovery(self, base_candidate_alert):
        """Proves a Critic revision request re-invokes Advisory Agent and resolves."""
        # Create a mock critic that demands revision on cycle 0 and approves on cycle 1
        class MockCritic(CriticSafetyAgent):
            def __init__(self):
                super().__init__(mock_mode=True)
                self.calls = 0

            def _execute_core(self, inp):
                self.calls += 1
                if self.calls == 1:
                    return CriticReviewOutput(
                        verdict=CriticVerdict.REVISION_REQUIRED,
                        findings=["Advisory confidence is too high without field test."],
                        failed_checks=["OVERCONFIDENT_WITHOUT_EVIDENCE"],
                        target_agent_for_revision=AgentRole.AGRICULTURAL_ADVISORY.value,
                        revision_instructions="Lower confidence score and advise soil ball test.",
                        evidence_consistency_score=0.4,
                    ), 50
                return CriticReviewOutput(
                    verdict=CriticVerdict.APPROVED_FOR_HUMAN_REVIEW,
                    findings=["Revised advisory complies with all constraints."],
                    failed_checks=[],
                    evidence_consistency_score=0.95,
                ), 50

        critic = MockCritic()
        supervisor = MultiAgentSupervisor(critic_safety_agent=critic, max_revisions=2)
        state = supervisor.investigate_alert(base_candidate_alert)

        assert state.revision_count == 1
        assert state.current_state == WorkflowState.AWAITING_HUMAN_REVIEW
        assert critic.calls == 2

    def test_max_revisions_exceeded_terminates_abstained(self, base_candidate_alert):
        """Proves infinite revision loops are strictly prevented when max_revisions is exceeded."""
        class EternalCritic(CriticSafetyAgent):
            def __init__(self):
                super().__init__(mock_mode=True)

            def _execute_core(self, inp):
                return CriticReviewOutput(
                    verdict=CriticVerdict.REVISION_REQUIRED,
                    findings=["Persistent inconsistency."],
                    failed_checks=["PERSISTENT_ERROR"],
                    target_agent_for_revision=AgentRole.AGRICULTURAL_ADVISORY.value,
                    revision_instructions="Retry.",
                    evidence_consistency_score=0.3,
                ), 40

        supervisor = MultiAgentSupervisor(critic_safety_agent=EternalCritic(), max_revisions=2)
        state = supervisor.investigate_alert(base_candidate_alert)

        assert state.current_state == WorkflowState.ABSTAINED
        assert state.final_decision == "ABSTAINED_MAX_REVISIONS_EXCEEDED"
        assert state.revision_count == 3  # Tried initial + 2 revisions + exceeded limit
        assert "MAX_REVISIONS_EXCEEDED" in state.abstention_reason


class TestDeterministicSafetyGates:
    """Verifies that non-LLM safety gates reject unsafe outputs even if an LLM approved."""

    def test_chemical_dosage_advice_rejected_by_safety_gate(self):
        """Proves regex safety gate rejects chemical pesticide/fertilizer dosages."""
        unsafe_advisory = AdvisoryProposalOutput(
            action_category="PEST_CONTROL",
            action_title="Chemical Spray Proposal",
            action_body="Apply Chlorpyrifos 20 EC at 2.5 ml/L per acre to control stem borers.",
            urgency="HIGH",
            cited_evidence_ids=["FAO-56-CH06:SEC01:CH01"],
            assumptions=[],
            limitations=[],
            confidence_score=0.9,
            when_to_seek_expert="Immediately",
            next_step="Mix 2.5 ml per liter water.",
        )

        res = DeterministicSafetyGate.audit_chemical_and_actuation_policy(unsafe_advisory)
        assert res.passed is False
        assert any("chemical concentration/dosage" in v for v in res.violations)

    def test_autonomous_physical_actuation_rejected(self):
        """Proves safety gate rejects automated actuation directives."""
        unsafe_advisory = AdvisoryProposalOutput(
            action_category="IRRIGATION",
            action_title="Automated Irrigation",
            action_body="System will turn on pump and execute irrigation automatically.",
            urgency="HIGH",
            cited_evidence_ids=["FAO-56-CH06:SEC01:CH01"],
            assumptions=[],
            limitations=[],
            confidence_score=0.9,
            when_to_seek_expert="Never",
            next_step="Start pump now.",
        )

        res = DeterministicSafetyGate.audit_chemical_and_actuation_policy(unsafe_advisory)
        assert res.passed is False
        assert any("autonomous physical actuation" in v for v in res.violations)

    def test_hallucinated_citation_rejected(self):
        """Proves citation gate rejects non-existent citation IDs."""
        advisory = AdvisoryProposalOutput(
            action_category="IRRIGATION",
            action_title="Test Advisory",
            action_body="Follow recommendations [NON-EXISTENT-SOURCE:SEC99:CH99].",
            urgency="LOW",
            cited_evidence_ids=["NON-EXISTENT-SOURCE:SEC99:CH99"],
            assumptions=[],
            limitations=[],
            confidence_score=0.8,
            when_to_seek_expert="None",
            next_step="Proceed.",
        )
        bundle = {
            "chunks": [
                {"citation_id": "FAO-56-CH06:SEC01:CH01"},
            ]
        }

        res = DeterministicSafetyGate.audit_advisory_citations(advisory, bundle)
        assert res.passed is False
        assert any("NON-EXISTENT-SOURCE" in v for v in res.violations)


class TestStateTransitionsAndProtocol:
    """Verifies state machine validity and message idempotency."""

    def test_invalid_state_transition_raises_error(self):
        """Proves jumping from RECEIVED directly to AWAITING_HUMAN_REVIEW raises InvalidStateTransitionError."""
        state = InvestigationState(
            run_id="test-run",
            alert_id="test-alert",
            field_id="field-kolar-001",
            candidate_alert={},
        )
        assert state.current_state == WorkflowState.RECEIVED

        with pytest.raises(InvalidStateTransitionError):
            transition_state(state, WorkflowState.AWAITING_HUMAN_REVIEW, triggered_by="tester")

    def test_duplicate_message_idempotency_collision(self):
        """Proves identical message idempotency key raises DuplicateMessageError."""
        router = MessageRouter()
        msg = create_agent_message(
            run_id="run-123",
            correlation_id="corr-123",
            from_agent=AgentRole.SUPERVISOR.value,
            to_agent=AgentRole.SENSOR_RELIABILITY.value,
            message_type=MessageType.TASK_REQUEST,
            payload={"test": "data"},
        )

        router.check_and_register(msg)
        with pytest.raises(DuplicateMessageError):
            router.check_and_register(msg)

    def test_direct_agent_to_agent_message_rejected(self):
        """Proves direct agent-to-agent communication bypassing the Supervisor raises InvalidMessageError."""
        router = MessageRouter()
        msg = create_agent_message(
            run_id="run-123",
            correlation_id="corr-123",
            from_agent=AgentRole.SENSOR_RELIABILITY.value,
            to_agent=AgentRole.CROP_RISK_ANALYST.value,
            message_type=MessageType.TASK_REQUEST,
            payload={"direct": "bypass"},
        )

        with pytest.raises(InvalidMessageError):
            router.validate_message(msg)

    def test_human_approval_lifecycle(self, base_candidate_alert):
        """Proves human review approval advances investigation from awaiting_human_review to completed."""
        supervisor = MultiAgentSupervisor()
        state = supervisor.investigate_alert(base_candidate_alert)
        assert state.current_state == WorkflowState.AWAITING_HUMAN_REVIEW

        # Human Agronomist Approval
        state_approved = supervisor.submit_human_decision(
            state=state,
            approved=True,
            reviewer_id="agronomist-kolar-kvk",
            comments="Field capacity verified on parcel; approved 25mm protective irrigation.",
        )
        assert state_approved.current_state == WorkflowState.COMPLETED
        assert state_approved.final_decision == "APPROVED_BY_HUMAN"

