"""Telegram notification provider with token redaction and safety suppression."""

from __future__ import annotations

import logging
import urllib.request
import json
from typing import Any, Dict, Optional
from agri_notifications.config import notification_settings
from agri_notifications.models import NotificationPayload
from agri_notifications.providers.base import BaseNotificationProvider

logger = logging.getLogger("agri.notifications.telegram")


def _redact_token(token: str) -> str:
    if not token or len(token) < 8:
        return "***"
    return f"{token[:4]}...{token[-4:]}"


class TelegramNotificationProvider(BaseNotificationProvider):
    """Telegram Bot API provider with strict outbound suppression in testing and token redaction."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        enable_live_dispatch: Optional[bool] = None,
    ):
        self.bot_token = bot_token if bot_token is not None else notification_settings.telegram_bot_token
        self.chat_id = chat_id if chat_id is not None else notification_settings.telegram_chat_id
        self.enable_live = enable_live_dispatch if enable_live_dispatch is not None else notification_settings.enable_telegram

    def get_channel_name(self) -> str:
        return "telegram"

    def format_message(self, payload: NotificationPayload) -> str:
        """Formats an agronomically clear, safety-compliant message with Kannada hint."""
        return (
            f"🚨 *AgriKafka Alert: {payload.title}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📌 *Field:* `{payload.field_id}`\n"
            f"⚡ *Urgency:* *{payload.urgency}*\n\n"
            f"📝 *Advisory Action:*\n{payload.summary}\n\n"
            f"🔍 *Data Provenance:*\n_{payload.provenance_caveat}_\n\n"
            f"⚠️ *Limitations:*\n" + "\n".join(f"• {lim}" for lim in payload.limitations[:2]) + "\n\n"
            f"📱 *Open in AgriKafka PWA:*\n{payload.pwa_deep_link}\n\n"
            f"_(ಕನ್ನಡ: ಈ ಸಲಹೆಯನ್ನು ಪರಿಶೀಲಿಸಲು ಮೇಲಿನ ಲಿಂಕ್ ತೆರೆಯಿರಿ)_"
        )

    def send(self, payload: NotificationPayload, recipient_id: str) -> Dict[str, Any]:
        target_chat = recipient_id or self.chat_id
        message_text = self.format_message(payload)

        # Safety boundary: If live dispatch is disabled (standard test/dev environment), mock cleanly
        if not self.enable_live or not self.bot_token:
            logger.info(
                "[TelegramNotificationProvider] Live dispatch suppressed (enable_telegram=False). Mocking delivery to chat %s. Token: %s",
                target_chat,
                _redact_token(self.bot_token),
            )
            return {
                "status": "mock_delivered",
                "channel": "telegram",
                "recipient_chat_id": target_chat,
                "message_length": len(message_text),
                "live_suppressed": True,
            }

        # Outbound HTTP POST to Telegram Bot API when explicitly enabled
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        req_body = {
            "chat_id": target_chat,
            "text": message_text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(req_body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                return {
                    "status": "delivered",
                    "channel": "telegram",
                    "telegram_message_id": resp_data.get("result", {}).get("message_id"),
                }
        except Exception as exc:
            logger.error("Failed to deliver Telegram notification to %s: %s", target_chat, str(exc))
            raise RuntimeError(f"Telegram API delivery failed: {str(exc)}") from exc

