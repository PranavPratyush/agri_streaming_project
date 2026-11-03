"""Base Ingestion Adapter with lifecycle, exponential backoff, and graceful shutdown."""

from __future__ import annotations

import abc
import logging
import random
import signal
import time
from typing import Any, Callable, Optional, TypeVar

from agri_ingestion.config import IngestionConfig
from agri_ingestion.producer import AgriKafkaProducer

logger = logging.getLogger("agri_ingestion.adapter")

T = TypeVar("T")


class BaseIngestionAdapter(abc.ABC):
    """Abstract base class for all AgriKafka-Agent data ingestion adapters."""

    def __init__(
        self,
        config: Optional[IngestionConfig] = None,
        producer: Optional[AgriKafkaProducer] = None,
        dry_run: bool = False,
    ) -> None:
        self.config = config or IngestionConfig()
        self.producer = producer or AgriKafkaProducer(config=self.config, dry_run=dry_run)
        self.dry_run = dry_run
        self._is_running: bool = False

    @property
    @abc.abstractmethod
    def adapter_name(self) -> str:
        """Unique identifier for this adapter (used in logs, metrics, and audit)."""
        pass

    @abc.abstractmethod
    def poll_once(self) -> int:
        """Executes a single extraction and ingestion cycle. Returns count of published events."""
        pass

    def start(self) -> None:
        """Starts the ingestion loop until stopped or interrupted."""
        self._is_running = True
        self._setup_signals()
        logger.info("Started adapter '%s' (dry_run=%s)", self.adapter_name, self.dry_run)

    def stop(self) -> None:
        """Signals the adapter loop to terminate gracefully."""
        if self._is_running:
            logger.info("Stopping adapter '%s' gracefully...", self.adapter_name)
            self._is_running = False
            self.producer.flush(timeout=5.0)

    @property
    def is_running(self) -> bool:
        return self._is_running

    def _setup_signals(self) -> None:
        try:
            signal.signal(signal.SIGINT, lambda s, f: self.stop())
            signal.signal(signal.SIGTERM, lambda s, f: self.stop())
        except (ValueError, AttributeError):
            # Not in main thread or on platform without standard signal handlers
            pass

    def execute_with_retry(
        self,
        func: Callable[[], T],
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        max_backoff: float = 30.0,
        backoff_factor: float = 2.0,
    ) -> T:
        """Executes a callable with bounded exponential backoff and jitter."""
        attempt = 0
        backoff = initial_backoff

        while True:
            attempt += 1
            try:
                return func()
            except Exception as exc:
                if attempt > max_retries:
                    logger.error(
                        "Adapter '%s' exhausted %d retries. Failing with: %s",
                        self.adapter_name,
                        max_retries,
                        exc,
                    )
                    raise

                # Add full jitter: random value between 0 and current backoff
                sleep_duration = random.uniform(0.5 * backoff, backoff)
                logger.warning(
                    "Adapter '%s' attempt %d/%d failed (%s). Retrying in %.2fs...",
                    self.adapter_name,
                    attempt,
                    max_retries,
                    exc,
                    sleep_duration,
                )
                time.sleep(sleep_duration)
                backoff = min(backoff * backoff_factor, max_backoff)

