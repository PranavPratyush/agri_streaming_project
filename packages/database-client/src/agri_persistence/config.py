"""Database configuration models for AgriKafka-Agent persistence layer."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DatabaseConfig:
    """Connection configuration for primary read/write database user."""
    host: str = field(default_factory=lambda: os.environ.get("POSTGRES_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.environ.get("POSTGRES_PORT", "5432")))
    dbname: str = field(default_factory=lambda: os.environ.get("POSTGRES_DB", "agrikafka"))
    user: str = field(default_factory=lambda: os.environ.get("POSTGRES_USER", "agri_admin"))
    password: str = field(default_factory=lambda: os.environ.get("POSTGRES_PASSWORD", "agri_dev_password_insecure"))
    
    # Pool parameters
    min_size: int = 2
    max_size: int = 10
    timeout_sec: float = 30.0
    max_idle_sec: float = 300.0
    
    # Retry parameters
    max_retries: int = 3
    retry_base_delay_sec: float = 0.5
    retry_max_delay_sec: float = 5.0

    @property
    def conninfo(self) -> str:
        """Returns standard PostgreSQL connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"


@dataclass(frozen=True)
class ReadOnlyDatabaseConfig:
    """Connection configuration for restricted read-only role (for MCP / agent inspection)."""
    host: str = field(default_factory=lambda: os.environ.get("POSTGRES_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.environ.get("POSTGRES_PORT", "5432")))
    dbname: str = field(default_factory=lambda: os.environ.get("POSTGRES_DB", "agrikafka"))
    user: str = field(default_factory=lambda: os.environ.get("AGRI_READONLY_USER", "agri_readonly"))
    password: str = field(default_factory=lambda: os.environ.get("AGRI_READONLY_PASSWORD", "agri_readonly_password_insecure"))
    
    min_size: int = 1
    max_size: int = 5
    timeout_sec: float = 15.0

    @property
    def conninfo(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"

