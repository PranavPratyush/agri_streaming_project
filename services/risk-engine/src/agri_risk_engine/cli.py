"""CLI interface for AgriRiskEngine sensor health forensics and threshold auditing."""

import argparse
import json
import sys

from agri_contracts.enums import ObservedVariable, StandardUnit
from agri_risk_engine.health import (
    DeterministicSensorHealthEvaluator,
    HealthThresholdsConfig,
)


def print_thresholds_audit() -> None:
    """Print full threshold provenance audit table."""
    cfg = HealthThresholdsConfig()
    print("==========================================================================================")
    print("AgriKafka-Agent: Deterministic Sensor Health Thresholds Audit")
    print("==========================================================================================")
    print(f"{'Parameter':<32} | {'Value':<12} | {'Unit':<15} | {'Provenance'}")
    print("-" * 90)
    for p in [cfg.cadence_multiplier, cfg.max_acceptable_age_sec, cfg.clock_skew_tolerance_sec, cfg.stuck_window_hours, cfg.stuck_variance_epsilon, cfg.stuck_min_consecutive_identical, cfg.drift_sigma_threshold, cfg.drift_min_history_samples]:
        print(f"{p.name:<32} | {str(p.value):<12} | {p.unit:<15} | {p.provenance}")
    print("\nRate of Change Limits:")
    print("-" * 90)
    for var, p in cfg.max_rate_of_change_per_minute.items():
        print(f"{var.value:<32} | {str(p.value):<12} | {p.unit:<15} | {p.provenance}")
    print("==========================================================================================")


def main() -> None:
    parser = argparse.ArgumentParser(description="AgriRiskEngine Sensor Health Forensic CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("audit-thresholds", help="Display all configured threshold limits with provenance")

    eval_parser = subparsers.add_parser("evaluate-sample", help="Evaluate a sample observation reading")
    eval_parser.add_argument("--variable", default="temperature_2m", help="Observed variable")
    eval_parser.add_argument("--value", type=float, required=True, help="Numeric value to evaluate")
    eval_parser.add_argument("--unit", default="celsius", help="Measurement unit")
    eval_parser.add_argument("--previous-value", type=float, default=None, help="Previous reading value")
    eval_parser.add_argument("--delta-sec", type=float, default=300.0, help="Seconds elapsed since previous reading")

    args = parser.parse_args()

    if args.command == "audit-thresholds":
        print_thresholds_audit()
        sys.exit(0)
    elif args.command == "evaluate-sample":
        evaluator = DeterministicSensorHealthEvaluator()
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        var_enum = ObservedVariable(args.variable)
        prev_time = datetime.fromtimestamp(now.timestamp() - args.delta_sec, tz=timezone.utc) if args.previous_value is not None else None

        result = evaluator.evaluate_observation(
            event_id="cli-sample-01",
            field_id="field_kolar_01",
            sensor_id="probe_01",
            variable=var_enum,
            value=args.value,
            unit=args.unit,
            event_time=now,
            now=now,
            previous_value=args.previous_value,
            previous_event_time=prev_time,
        )
        print(json.dumps(result.model_dump(mode="json"), indent=2))
        sys.exit(0)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

