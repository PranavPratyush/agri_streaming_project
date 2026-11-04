"""Command-line interface for the Multi-Agent Investigation Architecture."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from pathlib import Path

# Ensure package is on sys.path when invoked directly
PKG_ROOT = Path(__file__).resolve().parent.parent
if str(PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(PKG_ROOT))

REPO_ROOT = Path(__file__).resolve().parents[4]
for extra_path in [
    REPO_ROOT / "packages" / "event-contracts" / "src",
    REPO_ROOT / "packages" / "shared-python" / "src",
    REPO_ROOT / "packages" / "agronomy-rag" / "src",
    REPO_ROOT / "packages" / "database-client" / "src",
]:
    if str(extra_path) not in sys.path:
        sys.path.insert(0, str(extra_path))

from agri_investigator.supervisor import MultiAgentSupervisor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("agri_investigator.cli")


def cmd_investigate(args: argparse.Namespace) -> int:
    """Executes a multi-agent investigation on a candidate alert JSON or fixture."""
    if args.alert_file:
        alert_path = Path(args.alert_file)
        if not alert_path.exists():
            print(f"Error: Alert file not found: {alert_path}", file=sys.stderr)
            return 1
        candidate_alert = json.loads(alert_path.read_text(encoding="utf-8"))
    else:
        # Default representative dry-down stress scenario
        candidate_alert = {
            "alert_id": str(uuid.uuid4()),
            "field_id": args.field_id,
            "crop_variety": "Finger Millet (Ragi GPU-28)",
            "growth_stage": "Flowering / Grain Filling",
            "risk_type": "SOIL_MOISTURE_DEPLETION",
            "severity": args.severity,
            "composite_stress_index": 0.74,
            "sensor_health_state": args.sensor_health,
            "observations": [
                {"sensor_id": "soil-probe-01", "variable": "soil_moisture", "numeric_value": 0.12, "unit": "m3/m3"},
                {"sensor_id": "temp-probe-01", "variable": "ambient_temp", "numeric_value": 31.5, "unit": "celsius"},
            ],
            "sensor_health_results": [
                {"sensor_id": "soil-probe-01", "health_state": args.sensor_health, "reason_code": "ALL_SENSORS_VALID" if args.sensor_health == "HEALTHY" else "STUCK_VALUE"},
            ],
        }

    supervisor = MultiAgentSupervisor(max_revisions=args.max_revisions)
    state = supervisor.investigate_alert(candidate_alert)

    print("\n================ MULTI-AGENT INVESTIGATION REPORT ================")
    print(f"Run ID:            {state.run_id}")
    print(f"Alert ID:          {state.alert_id}")
    print(f"Field ID:          {state.field_id}")
    print(f"Workflow State:    {state.current_state.value}")
    print(f"Final Decision:    {state.final_decision}")
    print(f"Revision Cycles:   {state.revision_count} / {state.max_revisions}")
    print(f"Total Messages:    {len(state.messages)}")

    if state.abstention_reason:
        print(f"\n[Abstention / Rejection Reason]:\n  {state.abstention_reason}")

    if state.advisory_proposal:
        print(f"\n[Proposed Advisory]:")
        print(f"  Category: {state.advisory_proposal.action_category}")
        print(f"  Title:    {state.advisory_proposal.action_title}")
        print(f"  Urgency:  {state.advisory_proposal.urgency}")
        print(f"  Body:     {state.advisory_proposal.action_body}")
        print(f"  Citations: {state.advisory_proposal.cited_evidence_ids}")
        print(f"  Next Step: {state.advisory_proposal.next_step}")

    if state.critic_review:
        print(f"\n[Critic Review]:")
        print(f"  Verdict:  {state.critic_review.verdict.value}")
        print(f"  Findings: {state.critic_review.findings}")

    if state.safety_gate_result:
        print(f"\n[Deterministic Safety Gate]:")
        print(f"  Passed:     {state.safety_gate_result.passed}")
        print(f"  Violations: {state.safety_gate_result.violations}")

    print("==================================================================\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="AgriKafka Multi-Agent Investigation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_inv = subparsers.add_parser("investigate", help="Run multi-agent investigation on candidate alert")
    p_inv.add_argument("--alert-file", help="Path to candidate alert JSON file")
    p_inv.add_argument("--field-id", default="field-kolar-001", help="Target field parcel identifier")
    p_inv.add_argument("--severity", default="HIGH", help="Alert severity (LOW, MEDIUM, HIGH, CRITICAL)")
    p_inv.add_argument("--sensor-health", default="HEALTHY", choices=["HEALTHY", "SUSPECT", "FAULTY", "DEGRADED"], help="Sensor health state")
    p_inv.add_argument("--max-revisions", type=int, default=2, help="Maximum revision cycles allowed")
    p_inv.set_defaults(func=cmd_investigate)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
