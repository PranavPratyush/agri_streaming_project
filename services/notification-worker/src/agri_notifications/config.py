"""Configuration settings for the AgriKafka Notification Worker and Review Service."""

from __future__ import annotations

import os
from pydantic import BaseModel, Field


class NotificationSettings(BaseModel):
    """Centralized configuration loaded from environment."""
    service_name: str = "agri-notification-worker"
    version: str = "1.0.0"
    default_channel: str = Field(default_factory=lambda: os.getenv("NOTIFICATION_DEFAULT_CHANNEL", "mock_channel"))
    max_retries: int = Field(default_factory=lambda: int(os.getenv("NOTIFICATION_MAX_RETRIES", "3")))
    retry_backoff_base_sec: float = Field(default_factory=lambda: float(os.getenv("NOTIFICATION_BACKOFF_BASE_SEC", "1.0")))
    retry_backoff_max_sec: float = Field(default_factory=lambda: float(os.getenv("NOTIFICATION_BACKOFF_MAX_SEC", "30.0")))
    enable_telegram: bool = Field(default_factory=lambda: os.getenv("ENABLE_TELEGRAM_NOTIFICATIONS", "false").lower() in ("true", "1", "yes"))
    telegram_bot_token: str = Field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = Field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))
    pwa_base_url: str = Field(default_factory=lambda: os.getenv("FARMER_PWA_URL", "http://localhost:5173"))
    kafka_bootstrap_servers: str = Field(default_factory=lambda: os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092"))
    actions_topic: str = "agri.agent-actions"
    feedback_topic: str = "agri.feedback"


notification_settings = NotificationSettings()

