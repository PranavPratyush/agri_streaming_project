"""In-memory telemetry and source-level metric counters for the Ingestion Service."""

from __future__ import annotations

import threading
import time
from typing import Any, Dict


class IngestionMetrics:
    """Thread-safe source-level metrics tracker."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ingested_count: Dict[str, int] = {}
        self._failed_count: Dict[str, int] = {}
        self._rate_limit_hits: Dict[str, int] = {}
        self._freshness_latency: Dict[str, float] = {}
        self._start_time = time.time()

    def record_ingested(self, adapter: str, count: int = 1) -> None:
        with self._lock:
            self._ingested_count[adapter] = self._ingested_count.get(adapter, 0) + count

    def record_failure(self, adapter: str, error_type: str = "general") -> None:
        key = f"{adapter}:{error_type}"
        with self._lock:
            self._failed_count[key] = self._failed_count.get(key, 0) + 1

    def record_rate_limit(self, adapter: str) -> None:
        with self._lock:
            self._rate_limit_hits[adapter] = self._rate_limit_hits.get(adapter, 0) + 1

    def record_freshness_latency(self, adapter: str, latency_seconds: float) -> None:
        with self._lock:
            self._freshness_latency[adapter] = latency_seconds

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "uptime_seconds": round(time.time() - self._start_time, 2),
                "messages_ingested_total": dict(self._ingested_count),
                "messages_failed_total": dict(self._failed_count),
                "rate_limit_hits_total": dict(self._rate_limit_hits),
                "latest_freshness_latency_sec": dict(self._freshness_latency),
            }


# Singleton instance for service-wide metric recording
METRICS = IngestionMetrics()

