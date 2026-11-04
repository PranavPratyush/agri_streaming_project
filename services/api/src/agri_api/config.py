"""Configuration settings for the AgriKafka FastAPI service."""

from __future__ import annotations

import os
from typing import List
from pydantic import BaseModel, Field


class ApiConfig(BaseModel):
    """Centralized API configuration loaded from environment."""
    title: str = "AgriKafka-Agent Backend API"
    version: str = "1.0.0"
    description: str = (
        "Asynchronous REST API for the AgriKafka-Agent streaming agricultural risk "
        "monitoring, multi-agent alert investigation, and human-in-the-loop decision platform."
    )
    api_prefix: str = "/api/v1"
    host: str = Field(default_factory=lambda: os.getenv("API_HOST", "127.0.0.1"))
    port: int = Field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    cors_origins: List[str] = Field(
        default_factory=lambda: os.getenv(
            "API_CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
    )
    admin_api_key: str = Field(default_factory=lambda: os.getenv("AGRI_ADMIN_API_KEY", "agri-admin-secret-key"))
    default_farmer_id: str = "farmer-kolar-01"
    request_timeout_seconds: float = 15.0
    max_page_limit: int = 100
    max_time_window_hours: int = 720  # 30 days max


api_settings = ApiConfig()

