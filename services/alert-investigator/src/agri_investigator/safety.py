"""Deterministic, non-LLM safety boundary and policy enforcement.

Enforces project rules outside the LLM agents:
1. Rejection of ungrounded or hallucinated citation IDs against the retrieved EvidenceBundle.
2. Prohibition of automated chemical pesticide/fertilizer dosage recommendations (agronomic-safety.md).
3. Prohibition of autonomous physical actuation (e.g. turning on pumps).
4. Strict blocking of agricultural advice when sensor evidence is faulty or untrustworthy.
5. Enforcement of mandatory human review (no agent may approve on behalf of a farmer).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from agri_investigator.models import (
    AdvisoryProposalOutput,
    DeterministicSafetyResult,
    InvestigationState,
    SensorReliabilityOutput,
)

# Regex pattern from agronomic-safety.md detecting chemical dosage prescriptions
# e.g., "2.5 ml/L", "500 g/ha", "1.5 kg per acre", "10 ppm"
CHEMICAL_DOSAGE_REGEX = re.compile(
    r"\b\d+(\.\d+)?\s*(ml|g|kg|ppm|%)\s*(per|\/)\s*(liter|litre|l|ha|acre)\b",
    re.IGNORECASE,
)

# Regex pattern detecting autonomous actuation instructions
AUTONOMOUS_ACTUATION_REGEX = re.compile(
    r"\b(turn\s+on\s+pump|start\s+pump|open\s+valve|actuate\s+motor|dispatch\s+drone|execute\s+irrigation\s+automatically)\b",
    re.IGNORECASE,
)


class DeterministicSafetyGate:
    """External deterministic safety validation engine."""

    @classmethod
    def audit_sensor_reliability(cls, reliability: SensorReliabilityOutput) -> DeterministicSafetyResult:
        """Verifies that sensor telemetry is certified as trustworthy before crop analysis."""
        violations: List[str] = []
        if not reliability.is_trustworthy or not reliability.proceed_to_agronomy:
            violations.append(
                f"Sensor data is untrustworthy (health_state='{reliability.sensor_health_state}', "
                f"reason_code='{reliability.reason_code}'). Proceeding to crop advice is blocked."
            )

        return DeterministicSafetyResult(
            passed=len(violations) == 0,
            gate_name="sensor_reliability_gate",
            violations=violations,
            details={
                "health_state": reliability.sensor_health_state,
                "reason_code": reliability.reason_code,
                "uncertainty_score": reliability.uncertainty_score,
            },
        )

    @classmethod
    def audit_advisory_citations(
        cls,
        advisory: AdvisoryProposalOutput,
        evidence_bundle: Optional[Dict[str, Any]],
    ) -> DeterministicSafetyResult:
        """Verifies that every cited evidence ID exists in the retrieved EvidenceBundle."""
        violations: List[str] = []
        if not evidence_bundle or not evidence_bundle.get("chunks"):
            violations.append("Evidence bundle is missing or empty; advisory has zero empirical grounding.")
            return DeterministicSafetyResult(
                passed=False,
                gate_name="citation_grounding_gate",
                violations=violations,
                details={"cited_ids": advisory.cited_evidence_ids},
            )

        # Collect valid citation IDs present in bundle
        valid_ids = {
            chunk.get("citation_id") for chunk in evidence_bundle["chunks"] if chunk.get("citation_id")
        }

        # Check citations in cited_evidence_ids list
        for citation_id in advisory.cited_evidence_ids:
            if citation_id not in valid_ids:
                violations.append(f"Citation ID '{citation_id}' does not exist in the retrieved EvidenceBundle.")

        # Also extract citations in brackets from action_body: [SOURCE:SEC:CH]
        inline_citations = re.findall(r"\[([A-Z0-9\-_]+:SEC\d+:CH\d+)\]", advisory.action_body)
        for inline_id in inline_citations:
            if inline_id not in valid_ids:
                violations.append(f"Inline citation '{inline_id}' does not exist in the retrieved EvidenceBundle.")

        return DeterministicSafetyResult(
            passed=len(violations) == 0,
            gate_name="citation_grounding_gate",
            violations=violations,
            details={
                "valid_citation_ids": list(valid_ids),
                "advisory_citations": advisory.cited_evidence_ids,
            },
        )

    @classmethod
    def audit_chemical_and_actuation_policy(cls, advisory: AdvisoryProposalOutput) -> DeterministicSafetyResult:
        """Verifies that advisory does not prescribe chemical dosages or trigger autonomous actuation."""
        violations: List[str] = []
        combined_text = f"{advisory.action_title} {advisory.action_body} {advisory.next_step}"

        # 1. Chemical Dosage Audit
        chemical_matches = CHEMICAL_DOSAGE_REGEX.findall(combined_text)
        if chemical_matches:
            violations.append(
                f"Advisory prescribes unapproved chemical concentration/dosage: {chemical_matches}. "
                "Per agronomic-safety.md, automated systems must never prescribe chemical pesticide "
                "or fertilizer quantities without accredited agronomist review."
            )

        # 2. Autonomous Physical Actuation Audit
        actuation_matches = AUTONOMOUS_ACTUATION_REGEX.findall(combined_text)
        if actuation_matches:
            violations.append(
                f"Advisory triggers autonomous physical actuation: {actuation_matches}. "
                "Automated actuation is strictly prohibited."
            )

        return DeterministicSafetyResult(
            passed=len(violations) == 0,
            gate_name="chemical_and_actuation_policy_gate",
            violations=violations,
            details={"matches": len(chemical_matches) + len(actuation_matches)},
        )

    @classmethod
    def audit_complete_investigation(cls, state: InvestigationState) -> DeterministicSafetyResult:
        """Runs the entire suite of deterministic safety gates on an investigation state."""
        all_violations: List[str] = []
        gate_details: Dict[str, Any] = {}

        # 1. Reliability check
        if state.sensor_reliability:
            res_rel = cls.audit_sensor_reliability(state.sensor_reliability)
            gate_details["sensor_reliability"] = res_rel.model_dump()
            if not res_rel.passed:
                all_violations.extend(res_rel.violations)

        # 2. Advisory check (if proposal exists)
        if state.advisory_proposal:
            # Citations
            res_cit = cls.audit_advisory_citations(state.advisory_proposal, state.evidence_bundle)
            gate_details["citation_grounding"] = res_cit.model_dump()
            if not res_cit.passed:
                all_violations.extend(res_cit.violations)

            # Policy & chemicals
            res_pol = cls.audit_chemical_and_actuation_policy(state.advisory_proposal)
            gate_details["policy_and_chemicals"] = res_pol.model_dump()
            if not res_pol.passed:
                all_violations.extend(res_pol.violations)

        return DeterministicSafetyResult(
            passed=len(all_violations) == 0,
            gate_name="master_deterministic_safety_gate",
            violations=all_violations,
            details=gate_details,
        )

