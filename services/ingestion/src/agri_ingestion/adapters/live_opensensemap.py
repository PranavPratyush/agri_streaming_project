"""Live physical weather station adapter for openSenseMap citizen science network."""

from __future__ import annotations

import datetime
import hashlib
import logging
import uuid
from typing import Any, Dict, List, Optional

import requests
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
    wrap_in_dead_letter,
)
from agri_ingestion.adapters.base import BaseIngestionAdapter
from agri_ingestion.config import IngestionConfig
from agri_ingestion.metrics import METRICS
from agri_ingestion.producer import AgriKafkaProducer

logger = logging.getLogger("agri_ingestion.opensensemap")


class OpenSenseMapAdapter(BaseIngestionAdapter):
    """Polls openSenseMap REST API for verified physical station observations."""

    def __init__(
        self,
        station_id: Optional[str] = None,
        config: Optional[IngestionConfig] = None,
        producer: Optional[AgriKafkaProducer] = None,
        dry_run: bool = False,
    ) -> None:
        super().__init__(config=config, producer=producer, dry_run=dry_run)
        self.station_id = station_id or self.config.osm_primary_station_id
        self._session = requests.Session()
        self._last_seen_measurement_ids: Dict[str, str] = {}  # sensor_id -> last_timestamp

    @property
    def adapter_name(self) -> str:
        return f"opensensemap_{self.station_id}"

    def _map_sensor_title_to_variable(self, title: str, unit: str) -> tuple[Optional[ObservedVariable], Optional[StandardUnit]]:
        """Maps freeform senseBox sensor titles and units to canonical enums."""
        t_low = title.lower()
        u_low = unit.lower()

        if "temp" in t_low or "temperatur" in t_low:
            return ObservedVariable.TEMPERATURE_2M, StandardUnit.CELSIUS
        elif "hum" in t_low or "feuchte" in t_low or "%" in u_low:
            return ObservedVariable.RELATIVE_HUMIDITY_2M, StandardUnit.PERCENT
        elif "press" in t_low or "druck" in t_low or "luftdruck" in t_low or "baro" in t_low:
            return ObservedVariable.BAROMETRIC_PRESSURE, StandardUnit.HPA
        elif "rain" in t_low or "regen" in t_low or "niederschlag" in t_low or "precip" in t_low:
            return ObservedVariable.PRECIPITATION, StandardUnit.MM
        elif "wind" in t_low or "speed" in t_low or "geschwindigkeit" in t_low:
            return ObservedVariable.WIND_SPEED_10M, StandardUnit.M_PER_S
        elif "solar" in t_low or "radiation" in t_low or "strahlung" in t_low or "w/m" in u_low:
            return ObservedVariable.SOLAR_RADIATION, StandardUnit.W_PER_M2
        elif "uv" in t_low:
            return ObservedVariable.UV_INDEX, StandardUnit.UNITLESS

        return None, None

    def _fetch_box_data(self) -> Dict[str, Any]:
        """Queries the openSenseMap API for station metadata and latest sensor values."""
        url = f"{self.config.osm_base_url}/boxes/{self.station_id}"
        logger.debug("Fetching station data from %s", url)

        response = self._session.get(url, timeout=self.config.osm_request_timeout_sec)

        if response.status_code == 429:
            METRICS.record_rate_limit(self.adapter_name)
            raise requests.HTTPError(f"HTTP 429 Rate Limited by openSenseMap API for station {self.station_id}")

        response.raise_for_status()
        return response.json()

    def parse_station_payload(self, data: Dict[str, Any], raw_payload_str: str) -> List[AgriObservationEvent]:
        """Parses raw openSenseMap JSON into a list of canonical AgriObservationEvents."""
        events: List[AgriObservationEvent] = []
        ingestion_time = datetime.datetime.now(datetime.timezone.utc)

        # Extract coordinates
        loc_coords = data.get("currentLocation", {}).get("coordinates", [])
        lon = float(loc_coords[0]) if len(loc_coords) > 0 else self.config.openmeteo_kolar_lon
        lat = float(loc_coords[1]) if len(loc_coords) > 1 else self.config.openmeteo_kolar_lat
        location = LocationMetadata(latitude=lat, longitude=lon, elevation_m=None)

        sensors = data.get("sensors", [])
        if not sensors:
            logger.warning("Station %s returned zero sensors.", self.station_id)
            return events

        raw_hash = hashlib.sha256(raw_payload_str.encode("utf-8")).hexdigest()

        for sensor in sensors:
            sensor_id = str(sensor.get("_id", ""))
            sensor_title = str(sensor.get("title", ""))
            sensor_unit = str(sensor.get("unit", ""))
            sensor_type = str(sensor.get("sensorType", "Generic Sensor"))

            last_meas = sensor.get("lastMeasurement")
            if not last_meas:
                continue

            raw_value = last_meas.get("value")
            raw_time_str = last_meas.get("createdAt")
            if raw_value is None or not raw_time_str:
                continue

            try:
                numeric_val = float(raw_value)
            except (ValueError, TypeError):
                logger.warning("Unparseable sensor value '%s' for sensor %s", raw_value, sensor_id)
                continue

            # Deduplication: check if we already processed this exact reading
            if self._last_seen_measurement_ids.get(sensor_id) == raw_time_str:
                continue

            # Normalize event_time to UTC
            try:
                # Format: 2026-11-01T14:43:14.940Z
                if raw_time_str.endswith("Z"):
                    clean_time_str = raw_time_str[:-1] + "+00:00"
                else:
                    clean_time_str = raw_time_str
                event_time = datetime.datetime.fromisoformat(clean_time_str).astimezone(datetime.timezone.utc)
            except Exception as parse_err:
                logger.warning("Timestamp parse failure for %s (%s): %s", raw_time_str, sensor_id, parse_err)
                continue

            var_enum, unit_enum = self._map_sensor_title_to_variable(sensor_title, sensor_unit)
            if var_enum is None or unit_enum is None:
                # Unsupported variable in standard agronomy vocabulary (e.g. PM2.5), skip
                continue

            # Freshness calculation
            freshness_latency_sec = max(0.0, (ingestion_time - event_time).total_seconds())
            METRICS.record_freshness_latency(self.adapter_name, freshness_latency_sec)

            health_flag = SensorHealthFlag.HEALTHY
            val_status = ValidationStatus.UNKNOWN
            # If latency > 3 * polling interval (e.g. > 90s), mark DROPOUT / STALE
            if freshness_latency_sec > (3 * self.config.osm_poll_interval_sec):
                health_flag = SensorHealthFlag.DROPOUT
                val_status = ValidationStatus.STALE

            provenance = ProvenanceMetadata(
                provenance_class=ProvenanceClass.PHYSICAL_SENSOR,
                dataset_origin=f"openSenseMap:station:{self.station_id}",
                is_synthetic=False,
                scenario_id=None,
                source_uri=f"{self.config.osm_base_url}/boxes/{self.station_id}",
                raw_payload_hash=raw_hash,
            )

            idempotency_key = f"{self.station_id}:{sensor_id}:{event_time.isoformat()}"

            event = AgriObservationEvent(
                event_id=str(uuid.uuid4()),
                schema_version="1.0.0",
                event_time=event_time,
                ingestion_time=ingestion_time,
                field_id=self.config.default_field_id,
                idempotency_key=idempotency_key,
                correlation_id=None,
                provenance=provenance,
                source_provider="openSenseMap",
                sensor_id=sensor_id,
                station_id=self.station_id,
                variable=var_enum,
                value=numeric_val,
                unit=unit_enum,
                location=location,
                sensor_metadata=SensorPlacementMetadata(
                    depth_cm=None,
                    height_m=1.5,
                    sensor_model=sensor_title,
                    serial_number=sensor_id,
                ),
                quality_flags=QualityFlags(
                    is_imputed=False,
                    is_out_of_range=False,
                    freshness_latency_sec=freshness_latency_sec,
                    sensor_health_flag=health_flag,
                ),
                validation_status=val_status,
            )

            events.append(event)
            self._last_seen_measurement_ids[sensor_id] = raw_time_str

        return events

    def poll_once(self) -> int:
        """Polls the live station once and emits new observations to Kafka."""
        try:
            data = self.execute_with_retry(
                self._fetch_box_data,
                max_retries=self.config.osm_max_retries,
                initial_backoff=self.config.osm_backoff_base_sec,
                max_backoff=self.config.osm_backoff_max_sec,
            )
            raw_payload_str = str(data)
            events = self.parse_station_payload(data, raw_payload_str)

            published_count = 0
            for ev in events:
                if self.producer.publish_observation(ev, topic=self.config.topic_raw_observations):
                    published_count += 1

            logger.info("Adapter '%s' polled %d new observation events.", self.adapter_name, published_count)
            return published_count

        except Exception as exc:
            logger.error("Poll cycle failed for adapter '%s': %s", self.adapter_name, exc)
            METRICS.record_failure(self.adapter_name, exc.__class__.__name__)
            # Route failed payload to DLQ
            dlq_record = wrap_in_dead_letter(
                raw_payload=f"station_id:{self.station_id}",
                failed_topic=self.config.topic_raw_observations,
                error=exc,
            )
            self.producer.publish_dlq(dlq_record)
            return 0
