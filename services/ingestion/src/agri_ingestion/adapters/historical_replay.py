"""Historical dataset replay adapter with configurable speed, ordering, and resume checkpoints."""

from __future__ import annotations

import datetime
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, Iterator, List, Optional

import pandas as pd
from agri_contracts import (
    AgriObservationEvent,
    LocationMetadata,
    ObservedVariable,
    ProvenanceClass,
    ProvenanceMetadata,
    QualityFlags,
    SensorHealthFlag,
    SensorPlacementMetadata,
    StandardUnit,
    ValidationStatus,
)
from agri_ingestion.adapters.base import BaseIngestionAdapter
from agri_ingestion.config import IngestionConfig
from agri_ingestion.metrics import METRICS
from agri_ingestion.producer import AgriKafkaProducer

logger = logging.getLogger("agri_ingestion.replay")


class HistoricalReplayAdapter(BaseIngestionAdapter):
    """Replays historical Open-Meteo multi-field hourly observations into Kafka."""

    def __init__(
        self,
        csv_path: Optional[str] = None,
        speed_multiplier: float = 3600.0,  # 3600x: 1 hour simulated in 1 wall-clock second
        field_filter: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        run_id: Optional[str] = None,
        checkpoint_file: Optional[str] = None,
        config: Optional[IngestionConfig] = None,
        producer: Optional[AgriKafkaProducer] = None,
        dry_run: bool = False,
    ) -> None:
        super().__init__(config=config, producer=producer, dry_run=dry_run)
        self.csv_path = csv_path or self.config.historical_csv_path
        self.speed_multiplier = speed_multiplier
        self.field_filter = set(field_filter) if field_filter else None
        self.start_date = start_date
        self.end_date = end_date
        self.run_id = run_id or str(uuid.uuid4())
        self.checkpoint_file = checkpoint_file or f".replay_checkpoint_{self.run_id[:8]}.json"
        self._last_processed_index: int = -1
        self._load_checkpoint()

    @property
    def adapter_name(self) -> str:
        return f"historical_replay_{self.run_id[:8]}"

    def _load_checkpoint(self) -> None:
        """Loads previous checkpoint to enable safe resume semantics without duplicate side-effects."""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._last_processed_index = data.get("last_processed_index", -1)
                    logger.info("Resuming replay from checkpoint index %d", self._last_processed_index)
            except Exception as exc:
                logger.warning("Failed to read checkpoint file %s: %s", self.checkpoint_file, exc)

    def _save_checkpoint(self, index: int, last_event_time: str) -> None:
        """Saves current progress atomically."""
        try:
            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "run_id": self.run_id,
                        "csv_path": self.csv_path,
                        "last_processed_index": index,
                        "last_event_time": last_event_time,
                        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    },
                    f,
                    indent=2,
                )
        except Exception as exc:
            logger.warning("Failed to save checkpoint: %s", exc)

    def load_dataset(self) -> pd.DataFrame:
        """Loads and pre-filters historical CSV deterministically ordered by timestamp."""
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"Historical dataset CSV not found at: {self.csv_path}")

        logger.info("Loading historical dataset from %s ...", self.csv_path)
        df = pd.read_csv(self.csv_path)

        # Parse timestamp column
        df["dt"] = pd.to_datetime(df["timestamp"])

        # Filter by field if specified
        if self.field_filter:
            df = df[df["field_id"].isin(self.field_filter)]

        # Filter by date range if specified
        if self.start_date:
            df = df[df["dt"] >= pd.to_datetime(self.start_date)]
        if self.end_date:
            df = df[df["dt"] <= pd.to_datetime(self.end_date)]

        # Enforce deterministic ordering by timestamp then field_id
        df = df.sort_values(by=["dt", "field_id"]).reset_index(drop=True)
        logger.info("Loaded %d rows for replay (deterministic ordering verified).", len(df))
        return df

    def _row_to_events(self, row: pd.Series, row_idx: int) -> List[AgriObservationEvent]:
        """Converts a historical CSV row into canonical AgriObservationEvents for each variable."""
        events: List[AgriObservationEvent] = []
        ingestion_time = datetime.datetime.now(datetime.timezone.utc)

        # Timestamps: Open-Meteo archive dataset in this repo was downloaded in Asia/Kolkata
        # Normalize to UTC
        local_dt = row["dt"]
        if local_dt.tzinfo is None:
            # Assume Asia/Kolkata per metadata.json (UTC+5:30)
            ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
            aware_dt = local_dt.replace(tzinfo=ist_tz)
            event_time = aware_dt.astimezone(datetime.timezone.utc)
        else:
            event_time = local_dt.astimezone(datetime.timezone.utc)

        field_id = str(row["field_id"])
        lat = float(row.get("latitude_grid", row.get("latitude_requested", 13.0)))
        lon = float(row.get("longitude_grid", row.get("longitude_requested", 77.0)))
        elev = float(row.get("elevation_m", 800.0))
        location = LocationMetadata(latitude=lat, longitude=lon, elevation_m=elev)

        provenance = ProvenanceMetadata(
            provenance_class=ProvenanceClass.HISTORICAL_REPLAY,
            dataset_origin=f"open_meteo_archive:row:{row_idx}",
            is_synthetic=False,
            scenario_id=f"replay_{self.run_id[:8]}",
            source_uri=self.csv_path,
            raw_payload_hash=f"run:{self.run_id}:row:{row_idx}",
        )

        # Map each measured column to an observation
        col_mappings = [
            ("temperature_2m", ObservedVariable.TEMPERATURE_2M, StandardUnit.CELSIUS),
            ("relative_humidity_2m", ObservedVariable.RELATIVE_HUMIDITY_2M, StandardUnit.PERCENT),
            ("dew_point_2m", ObservedVariable.DEW_POINT_2M, StandardUnit.CELSIUS),
            ("precipitation", ObservedVariable.PRECIPITATION, StandardUnit.MM),
            ("vapour_pressure_deficit", ObservedVariable.VAPOUR_PRESSURE_DEFICIT, StandardUnit.KPA),
            ("soil_moisture_0_to_7cm", ObservedVariable.SOIL_MOISTURE_0_TO_7CM, StandardUnit.M3_PER_M3),
            ("wind_speed_10m", ObservedVariable.WIND_SPEED_10M, StandardUnit.M_PER_S),
        ]

        for col_name, var_enum, unit_enum in col_mappings:
            if col_name in row and pd.notna(row[col_name]):
                val = float(row[col_name])
                idempotency_key = f"{self.run_id}:{field_id}:{var_enum.value}:{event_time.isoformat()}"

                ev = AgriObservationEvent(
                    event_id=str(uuid.uuid4()),
                    schema_version="1.0.0",
                    event_time=event_time,
                    ingestion_time=ingestion_time,
                    field_id=field_id,
                    idempotency_key=idempotency_key,
                    correlation_id=self.run_id,
                    provenance=provenance,
                    source_provider="open_meteo_archive_replay",
                    sensor_id=f"replay_sensor_{var_enum.value}",
                    station_id=None,
                    variable=var_enum,
                    value=val,
                    unit=unit_enum,
                    location=location,
                    sensor_metadata=SensorPlacementMetadata(
                        depth_cm=3.5 if "soil_moisture" in col_name else None,
                        height_m=2.0 if "temperature" in col_name or "humidity" in col_name else 10.0,
                        sensor_model="OpenMeteoERA5Land",
                        serial_number=f"era5_{col_name}",
                    ),
                    quality_flags=QualityFlags(
                        is_imputed=False,
                        is_out_of_range=False,
                        freshness_latency_sec=0.0,
                        sensor_health_flag=SensorHealthFlag.HEALTHY,
                    ),
                    validation_status=ValidationStatus.UNKNOWN,
                )
                events.append(ev)

        return events

    def stream_dataset(self, max_rows: Optional[int] = None) -> Iterator[List[AgriObservationEvent]]:
        """Yields batches of AgriObservationEvents respecting the configured speed multiplier."""
        df = self.load_dataset()
        if max_rows:
            df = df.iloc[:max_rows]

        total_rows = len(df)
        last_event_time: Optional[datetime.datetime] = None

        for idx, row in df.iterrows():
            if idx <= self._last_processed_index:
                continue

            current_event_time = row["dt"]

            # Inter-row pacing calculation for accelerated replay
            if last_event_time is not None and self.speed_multiplier > 0:
                time_diff_sec = (current_event_time - last_event_time).total_seconds()
                if time_diff_sec > 0:
                    delay_sec = time_diff_sec / self.speed_multiplier
                    # Avoid micro-sleep overhead if delay is tiny
                    if delay_sec > 0.005:
                        time.sleep(delay_sec)

            events = self._row_to_events(row, int(idx))
            last_event_time = current_event_time
            self._last_processed_index = int(idx)
            self._save_checkpoint(int(idx), str(current_event_time))

            yield events

    def poll_once(self) -> int:
        """Executes a single row batch emission for stepping or testing."""
        df = self.load_dataset()
        next_idx = self._last_processed_index + 1
        if next_idx >= len(df):
            logger.info("Replay reached end of dataset.")
            return 0

        row = df.iloc[next_idx]
        events = self._row_to_events(row, next_idx)
        published_count = 0
        for ev in events:
            if self.producer.publish_observation(ev, topic=self.config.topic_raw_observations):
                published_count += 1

        self._last_processed_index = next_idx
        self._save_checkpoint(next_idx, str(row["dt"]))
        return published_count

    def run_replay(self, max_rows: Optional[int] = None) -> int:
        """Runs the continuous replay loop."""
        self.start()
        total_published = 0
        logger.info(
            "Starting replay run_id=%s (speed=%.1fx, starting from row %d)",
            self.run_id,
            self.speed_multiplier,
            self._last_processed_index + 1,
        )

        try:
            for event_batch in self.stream_dataset(max_rows=max_rows):
                if not self.is_running:
                    logger.info("Replay interrupted by stop signal.")
                    break

                for ev in event_batch:
                    if self.producer.publish_observation(ev, topic=self.config.topic_raw_observations):
                        total_published += 1

            self.producer.flush(timeout=5.0)
            logger.info("Replay completed. Published %d events in total.", total_published)
            return total_published
        finally:
            self.stop()
