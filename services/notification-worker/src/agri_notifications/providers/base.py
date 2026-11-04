"""Base abstract notification provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict
from agri_notifications.models import NotificationPayload


class BaseNotificationProvider(ABC):
    """Abstract interface implemented by all notification channels."""

    @abstractmethod
    def get_channel_name(self) -> str:
        """Returns the canonical channel identifier."""
        raise NotImplementedError

    @abstractmethod
    def send(self, payload: NotificationPayload, recipient_id: str) -> Dict[str, Any]:
        """Delivers the payload to the recipient.
        
        Returns provider response metadata or raises an exception on failure.
        """
        raise NotImplementedError

