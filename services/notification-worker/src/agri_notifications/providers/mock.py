"""Mock and in-memory notification providers for automated testing and offline development."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
from agri_notifications.models import NotificationPayload
from agri_notifications.providers.base import BaseNotificationProvider

logger = logging.getLogger("agri.notifications.mock")


class LocalMockNotificationProvider(BaseNotificationProvider):
    """Local mock provider for standard offline local development."""

    def __init__(self, channel_name: str = "mock_channel"):
        self._channel_name = channel_name
        self.dispatches: List[Dict[str, Any]] = []

    def get_channel_name(self) -> str:
        return self._channel_name

    def send(self, payload: NotificationPayload, recipient_id: str) -> Dict[str, Any]:
        record = {
            "channel": self._channel_name,
            "recipient_id": recipient_id,
            "title": payload.title,
            "summary": payload.summary,
            "deep_link": payload.pwa_deep_link,
            "sent_at": time.time(),
        }
        self.dispatches.append(record)
        logger.info("[LocalMockNotificationProvider] Delivered notification to %s: %s", recipient_id, payload.title)
        return {"status": "ok", "provider": "local_mock", "delivery_id": f"mock-{len(self.dispatches)}"}


class InMemoryNotificationProvider(BaseNotificationProvider):
    """Deterministic in-memory notification provider with simulated failures for unit tests."""

    def __init__(self, failure_count: int = 0, permanent_failure: bool = False, channel_name: str = "mock_channel"):
        self._channel_name = channel_name
        self.failure_count = failure_count
        self.permanent_failure = permanent_failure
        self.attempts = 0
        self.delivered_messages: List[Dict[str, Any]] = []

    def get_channel_name(self) -> str:
        return self._channel_name

    def send(self, payload: NotificationPayload, recipient_id: str) -> Dict[str, Any]:
        self.attempts += 1
        if self.permanent_failure:
            raise ConnectionError(f"Simulated permanent provider outage on attempt {self.attempts}")

        if self.attempts <= self.failure_count:
            raise TimeoutError(f"Simulated transient timeout (attempt {self.attempts}/{self.failure_count})")

        delivery_info = {
            "channel": self._channel_name,
            "recipient_id": recipient_id,
            "payload": payload.model_dump(),
            "delivered_at": time.time(),
            "attempt": self.attempts,
        }
        self.delivered_messages.append(delivery_info)
        return {
            "status": "delivered",
            "provider": "in_memory",
            "attempt": self.attempts,
            "delivery_timestamp": delivery_info["delivered_at"],
        }

