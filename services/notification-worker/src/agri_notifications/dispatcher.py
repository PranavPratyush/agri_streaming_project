"""Notification dispatcher with compound idempotency, bounded retries, and dead-letter queue routing."""

from __future__ import annotations

import datetime
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from agri_notifications.config import notification_settings
from agri_notifications.models import (
    DeliveryStatus,
    NotificationChannel,
    NotificationDispatch,
    NotificationPayload,
)
from agri_notifications.policy import NotificationPolicyEvaluator
from agri_notifications.providers.base import BaseNotificationProvider
from agri_notifications.providers.mock import LocalMockNotificationProvider
from agri_notifications.providers.pwa import PwaPushProvider
from agri_notifications.providers.telegram import TelegramNotificationProvider

logger = logging.getLogger("agri.notifications.dispatcher")


class NotificationDispatcher:
    """Dispatches notifications across channels with idempotency, safety gates, and retries."""

    def __init__(
        self,
        repository: Any,
        policy_evaluator: Optional[NotificationPolicyEvaluator] = None,
        providers: Optional[Dict[str, BaseNotificationProvider]] = None,
        max_retries: Optional[int] = None,
        retry_backoff_base_sec: Optional[float] = None,
        retry_backoff_max_sec: Optional[float] = None,
    ):
        self.repo = repository
        self.policy = policy_evaluator or NotificationPolicyEvaluator()
        self.max_retries = max_retries if max_retries is not None else notification_settings.max_retries
        self.retry_backoff_base_sec = retry_backoff_base_sec if retry_backoff_base_sec is not None else notification_settings.retry_backoff_base_sec
        self.retry_backoff_max_sec = retry_backoff_max_sec if retry_backoff_max_sec is not None else notification_settings.retry_backoff_max_sec

        # Initialize providers
        self.providers: Dict[str, BaseNotificationProvider] = providers or {
            NotificationChannel.MOCK_CHANNEL.value: LocalMockNotificationProvider(),
            NotificationChannel.PWA_PUSH.value: PwaPushProvider(),
            NotificationChannel.TELEGRAM.value: TelegramNotificationProvider(),
        }

    def compute_idempotency_key(
        self,
        alert_id: str,
        advisory_version: int,
        recipient_id: str,
        channel: str,
    ) -> str:
        """Generates deterministic compound idempotency key."""
        return f"{alert_id}:{advisory_version}:{recipient_id}:{channel}"

    def dispatch_for_alert_and_advisory(
        self,
        alert: Dict[str, Any],
        recommendation: Dict[str, Any],
        recipient_id: str,
        channel: str = NotificationChannel.MOCK_CHANNEL.value,
        advisory_version: int = 1,
        sensor_health_state: Optional[str] = None,
        critic_decision: Optional[str] = None,
    ) -> NotificationDispatch:
        """Evaluates policy, checks compound idempotency, and delivers notification."""
        alert_id = str(alert.get("alert_id"))
        rec_id = str(recommendation.get("recommendation_id"))
        idempotency_key = self.compute_idempotency_key(alert_id, advisory_version, recipient_id, channel)

        # 1. Deduplication check via compound idempotency key
        existing = self.repo.get_notification_dispatch_by_idempotency(idempotency_key)
        if existing:
            if existing.get("status") in (DeliveryStatus.SENT.value, DeliveryStatus.DEAD_LETTER.value):
                logger.info("Deduplicated dispatch for key %s (status: %s)", idempotency_key, existing.get("status"))
                return NotificationDispatch(**existing)

        # 2. Safety and Qualification Policy Gate
        qualifies, reason = self.policy.evaluate_qualification(
            alert=alert,
            recommendation=recommendation,
            sensor_health_state=sensor_health_state,
            critic_decision=critic_decision,
        )

        dispatch_id = str(uuid.uuid4())
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if not qualifies:
            logger.info("Notification suppressed by policy: %s", reason)
            dead_letter_dispatch = NotificationDispatch(
                dispatch_id=dispatch_id,
                alert_id=alert_id,
                investigation_id=recommendation.get("investigation_id"),
                recommendation_id=rec_id,
                advisory_version=advisory_version,
                recipient_id=recipient_id,
                channel=NotificationChannel(channel),
                idempotency_key=idempotency_key,
                status=DeliveryStatus.DEAD_LETTER,
                attempts=1,
                max_retries=self.max_retries,
                payload={"suppression_reason": reason, "alert": alert, "recommendation": recommendation},
                error_message=f"Suppressed by policy: {reason}",
                created_at=now_iso,
                updated_at=now_iso,
            )
            self.repo.create_notification_dispatch(dead_letter_dispatch.model_dump())
            return dead_letter_dispatch

        # 3. Content safety check (chemical dosages and guarantees)
        is_safe, safety_reason, sanitized_rec = self.policy.sanitize_and_validate_content(recommendation)
        if not is_safe:
            logger.warning("Notification rejected by content safety gate: %s", safety_reason)
            dead_letter_dispatch = NotificationDispatch(
                dispatch_id=dispatch_id,
                alert_id=alert_id,
                investigation_id=recommendation.get("investigation_id"),
                recommendation_id=rec_id,
                advisory_version=advisory_version,
                recipient_id=recipient_id,
                channel=NotificationChannel(channel),
                idempotency_key=idempotency_key,
                status=DeliveryStatus.DEAD_LETTER,
                attempts=1,
                max_retries=self.max_retries,
                payload={"safety_violation": safety_reason, "recommendation": recommendation},
                error_message=f"Content safety violation: {safety_reason}",
                created_at=now_iso,
                updated_at=now_iso,
            )
            self.repo.create_notification_dispatch(dead_letter_dispatch.model_dump())
            return dead_letter_dispatch

        # 4. Construct payload
        payload = self.policy.build_notification_payload(alert, sanitized_rec, advisory_version=advisory_version)

        # 5. Delivery attempt with bounded retries
        provider = self.providers.get(channel)
        if not provider:
            raise ValueError(f"Unknown notification channel '{channel}'. Configured: {list(self.providers.keys())}")

        attempts = 0
        last_error = None
        provider_resp = None
        delivery_status = DeliveryStatus.PENDING

        while attempts < self.max_retries:
            attempts += 1
            try:
                provider_resp = provider.send(payload, recipient_id)
                delivery_status = DeliveryStatus.SENT
                break
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "Delivery attempt %d/%d failed for recipient %s on channel %s: %s",
                    attempts,
                    self.max_retries,
                    recipient_id,
                    channel,
                    exc,
                )
                if attempts < self.max_retries:
                    # Bounded exponential backoff
                    backoff = min(
                        self.retry_backoff_base_sec * (2 ** (attempts - 1)),
                        self.retry_backoff_max_sec,
                    )
                    if backoff > 0:
                        time.sleep(backoff)

        if delivery_status != DeliveryStatus.SENT:
            delivery_status = DeliveryStatus.DEAD_LETTER

        now_done_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        dispatch_record = NotificationDispatch(
            dispatch_id=dispatch_id,
            alert_id=alert_id,
            investigation_id=recommendation.get("investigation_id"),
            recommendation_id=rec_id,
            advisory_version=advisory_version,
            recipient_id=recipient_id,
            channel=NotificationChannel(channel),
            idempotency_key=idempotency_key,
            status=delivery_status,
            attempts=attempts,
            max_retries=self.max_retries,
            delivered_at=now_done_iso if delivery_status == DeliveryStatus.SENT else None,
            payload=payload.model_dump(),
            provider_response=provider_resp,
            error_message=last_error if delivery_status != DeliveryStatus.SENT else None,
            created_at=now_iso,
            updated_at=now_done_iso,
        )

        self.repo.create_notification_dispatch(dispatch_record.model_dump())
        return dispatch_record
