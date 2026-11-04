"""PWA Push notification provider for the farmer responsive web app."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List
from agri_notifications.models import NotificationPayload
from agri_notifications.providers.base import BaseNotificationProvider

logger = logging.getLogger("agri.notifications.pwa")


class PwaPushProvider(BaseNotificationProvider):
    """Delivers in-app push payloads directing farmers to the PWA."""

    def __init__(self):
        self._sent_payloads: List[Dict[str, Any]] = []

    def get_channel_name(self) -> str:
        return "pwa_push"

    def send(self, payload: NotificationPayload, recipient_id: str) -> Dict[str, Any]:
        push_message = {
            "title": f"🌾 {payload.title}",
            "body": payload.summary,
            "data": {
                "url": payload.pwa_deep_link,
                "alert_id": payload.alert_id,
                "urgency": payload.urgency,
                "advisory_id": payload.advisory_id,
            },
            "recipient_id": recipient_id,
            "dispatched_at": time.time(),
        }
        self._sent_payloads.append(push_message)
        logger.info("[PwaPushProvider] Dispatched push to recipient %s -> link: %s", recipient_id, payload.pwa_deep_link)
        return {
            "status": "pwa_push_queued",
            "channel": "pwa_push",
            "push_id": f"pwa-{len(self._sent_payloads)}",
            "deep_link": payload.pwa_deep_link,
        }

