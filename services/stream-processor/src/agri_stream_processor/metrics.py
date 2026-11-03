"""Streaming query metrics listener and progress monitor for PySpark Structured Streaming."""

from __future__ import annotations

import json
import logging
from typing import Any
from pyspark.sql.streaming import StreamingQueryListener

logger = logging.getLogger("agri_stream_processor.metrics")


class AgriStreamingMetricsListener(StreamingQueryListener):
    """Listens to PySpark Structured Streaming query progress and emits structured metrics."""

    def __init__(self) -> None:
        super().__init__()
        self.query_stats: dict[str, dict[str, Any]] = {}
        self.total_input_rows: int = 0
        self.total_batches_processed: int = 0

    def onQueryStarted(self, event: Any) -> None:
        query_id = str(event.id)
        query_name = str(event.name) if event.name else "unnamed_query"
        logger.info(
            f"Streaming query started: name='{query_name}', id='{query_id}', runId='{event.runId}'"
        )
        self.query_stats[query_id] = {
            "name": query_name,
            "status": "RUNNING",
            "batches": 0,
            "input_rows": 0,
            "latest_duration_ms": 0,
            "watermark": None,
        }

    def onQueryProgress(self, event: Any) -> None:
        progress = event.progress
        query_id = str(progress.id)
        query_name = str(progress.name) if progress.name else "unnamed_query"
        num_input_rows = progress.numInputRows
        batch_id = progress.batchId
        duration_ms = progress.durationMs.get("triggerExecution", 0) if progress.durationMs else 0
        watermark = progress.eventTime.get("watermark") if progress.eventTime else None

        self.total_input_rows += num_input_rows
        self.total_batches_processed += 1

        stats = self.query_stats.setdefault(query_id, {})
        stats.update({
            "name": query_name,
            "status": "ACTIVE",
            "batches": batch_id,
            "input_rows": stats.get("input_rows", 0) + num_input_rows,
            "latest_duration_ms": duration_ms,
            "input_rows_per_sec": progress.inputRowsPerSecond,
            "processed_rows_per_sec": progress.processedRowsPerSecond,
            "watermark": watermark,
        })

        if num_input_rows > 0 or batch_id % 10 == 0:
            logger.info(
                f"[Metrics] Query '{query_name}' (Batch {batch_id}): "
                f"input_rows={num_input_rows}, duration={duration_ms}ms, "
                f"rate={progress.processedRowsPerSecond:.1f} rows/s, watermark={watermark}"
            )

    def onQueryTerminated(self, event: Any) -> None:
        query_id = str(event.id)
        exc = event.exception
        stats = self.query_stats.get(query_id, {})
        stats["status"] = "TERMINATED"
        if exc:
            logger.error(f"Streaming query {query_id} terminated with error: {exc}")
            stats["error"] = str(exc)
        else:
            logger.info(f"Streaming query {query_id} terminated gracefully.")

    def get_summary(self) -> dict[str, Any]:
        """Return cumulative metrics snapshot."""
        return {
            "total_input_rows": self.total_input_rows,
            "total_batches_processed": self.total_batches_processed,
            "queries": self.query_stats,
        }

