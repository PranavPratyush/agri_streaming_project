"""CLI interface for AgriKafka notification worker and review operations."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from agri_notifications.config import notification_settings
from agri_notifications.dispatcher import NotificationDispatcher
from agri_notifications.feedback import FeedbackProcessor
from agri_notifications.lifecycle import HumanReviewLifecycleManager
from agri_notifications.models import (
    HumanReviewActionRequest,
    ReviewAction,
    StructuredFeedbackInput,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("agri.notifications.cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AgriKafka Notification Worker and Human Review CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # Subcommand: dispatch
    dispatch_p = subparsers.add_parser("dispatch", help="Test dispatch of a notification")
    dispatch_p.add_argument("--alert-id", required=True, help="Crop candidate alert UUID")
    dispatch_p.add_argument("--recommendation-id", required=True, help="Advisory recommendation UUID")
    dispatch_p.add_argument("--field-id", default="field-kolar-001", help="Field identifier")
    dispatch_p.add_argument("--recipient-id", default="farmer-01", help="Recipient user or chat ID")
    dispatch_p.add_argument("--channel", default="mock_channel", help="Notification channel (mock_channel, pwa_push, telegram)")
    dispatch_p.add_argument("--alert-type", default="SOIL_MOISTURE_DEPLETION", help="Alert category")
    dispatch_p.add_argument("--urgency", default="HIGH", help="Advisory urgency")

    # Subcommand: review
    review_p = subparsers.add_parser("review", help="Execute human review decision")
    review_p.add_argument("--recommendation-id", required=True, help="Recommendation UUID")
    review_p.add_argument("--action", required=True, choices=["APPROVE", "REJECT", "ACKNOWLEDGE", "REQUEST_INSPECTION"], help="Action to take")
    review_p.add_argument("--reviewer-id", default="agronomist-01", help="Reviewer identifier")
    review_p.add_argument("--reason", default="Agronomist field review", help="Justification notes")

    # Subcommand: feedback
    feedback_p = subparsers.add_parser("feedback", help="Record structured feedback")
    feedback_p.add_argument("--recommendation-id", required=True, help="Recommendation UUID")
    feedback_p.add_argument("--field-id", default="field-kolar-001", help="Field identifier")
    feedback_p.add_argument("--rating", type=int, default=5, help="1-5 utility rating")
    feedback_p.add_argument("--comments", default="Helpful advisory", help="Farmer comments")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # Import repo
    try:
        from agri_persistence.pool import DatabasePoolManager
        from agri_persistence.repository import PersistenceRepository
        pool_mgr = DatabasePoolManager()
        if pool_mgr.check_health():
            repo = PersistenceRepository(pool_mgr)
        else:
            raise RuntimeError("Database unavailable")
    except Exception:
        from agri_api.dependencies import LocalMemoryRepository
        repo = LocalMemoryRepository()

    if args.subcommand == "dispatch":
        dispatcher = NotificationDispatcher(repository=repo)
        alert = {
            "alert_id": args.alert_id,
            "field_id": args.field_id,
            "alert_type": args.alert_type,
            "severity": args.urgency,
        }
        recommendation = {
            "recommendation_id": args.recommendation_id,
            "field_id": args.field_id,
            "action_title": "Field Irrigation Advisory",
            "action_body": "Apply deficit drip irrigation to root zone.",
            "urgency": args.urgency,
            "action_category": "IRRIGATION",
        }
        dispatch = dispatcher.dispatch_for_alert_and_advisory(
            alert=alert,
            recommendation=recommendation,
            recipient_id=args.recipient_id,
            channel=args.channel,
        )
        print(json.dumps(dispatch.model_dump(), indent=2))

    elif args.subcommand == "review":
        lifecycle = HumanReviewLifecycleManager(repository=repo)
        req = HumanReviewActionRequest(
            action=ReviewAction(args.action),
            reviewer_id=args.reviewer_id,
            reason=args.reason,
        )
        success, resp, status_code = lifecycle.apply_action(args.recommendation_id, req)
        print(f"Status {status_code}: {json.dumps(resp.model_dump(), indent=2)}")
        return 0 if success else 1

    elif args.subcommand == "feedback":
        processor = FeedbackProcessor(repository=repo)
        fb_input = StructuredFeedbackInput(
            recommendation_id=args.recommendation_id,
            field_id=args.field_id,
            rating=args.rating,
            feedback_comments=args.comments,
        )
        success, record, msg = processor.record_feedback(fb_input)
        print(f"Feedback ({msg}): {json.dumps(record, indent=2)}")
        return 0 if success else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

