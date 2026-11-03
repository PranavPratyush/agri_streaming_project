"""Weather and forecast context adapter for Open-Meteo API."""

from __future__ import annotations

import datetime
import hashlib
import logging
import uuid
from typing import Any, Dict, List, Optional

import requests
from agri_contracts import (
    LocationMetadata,
    ProvenanceClass,
    ProvenanceMetadata,
    WeatherContextEvent,
    wrap_in_dead_letter,
)
from agri_ingestion.adapters.base import BaseIngestionAdapter
from agri_ingestion.config import IngestionConfig
from agri_ingestion.metrics import METRICS
from agri_ingestion.producer import AgriKafkaProducer

logger = logging.getLogger("agri_ingestion.openmeteo")


class OpenMeteoContextAdapter(BaseIngestionAdapter):
    """Fetches real-time environmental context and forecasts for Kolar, Karnataka from Open-Meteo."""

    def __init__(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        field_id: Optional[str] = None,
        config: Optional[IngestionConfig] = None,
        producer: Optional[AgriKafkaProducer] = None,
        dry_run: bool = False,
    ) -> None:
        super().__init__(config=config, producer=producer, dry_run=dry_run)
        self.lat = lat if lat is not None else self.config.openmeteo_kolar_lat
        self.lon = lon if lon is not None else self.config.openmeteo_kolar_lon
        self.field_id = field_id or self.config.default_field_id
        self._session = requests.Session()

    @property
    def adapter_name(self) -> str:
        return f"openmeteo_context_{self.field_id}"

    def _fetch_forecast_data(self) -> Dict[str, Any]:
        """Queries Open-Meteo Forecast API for current weather and short-horizon forecasts."""
        params = {
            "latitude": self.lat,
            "longitude": self.lon,
            "current": "temperature_2m,relative_humidity_2m,dew_point_2m,precipitation,wind_speed_10m,soil_moisture_0_to_1cm",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,direct_normal_irradiance",
            "forecast_days": 1,
            "timezone": "UTC",
        }

        response = self._session.get(
            self.config.openmeteo_api_url,
            params=params,
            timeout=self.config.openmeteo_request_timeout_sec,
        )

        if response.status_code == 429:
            METRICS.record_rate_limit(self.adapter_name)
            raise requests.HTTPError(f"HTTP 429 Rate Limited by Open-Meteo API for {self.lat},{self.lon}")

        response.raise_for_status()
        return response.json()

    def parse_weather_payload(self, data: Dict[str, Any], raw_payload_str: str) -> List[WeatherContextEvent]:
        """Maps Open-Meteo JSON to canonical WeatherContextEvent instances."""
        events: List[WeatherContextEvent] = []
        ingestion_time = datetime.datetime.now(datetime.timezone.utc)
        raw_hash = hashlib.sha256(raw_payload_str.encode("utf-8")).hexdigest()

        elevation = float(data.get("elevation", self.config.openmeteo_elevation_m))
        location = LocationMetadata(latitude=self.lat, longitude=self.lon, elevation_m=elevation)

        current = data.get("current", {})
        if current:
            cur_time_str = current.get("time")
            # Parse ISO UTC timestamp
            if cur_time_str:
                if not cur_time_str.endswith("Z") and "+" not in cur_time_str:
                    cur_time_str += "+00:00"
                event_time = datetime.datetime.fromisoformat(cur_time_str).astimezone(datetime.timezone.utc)
            else:
                event_time = ingestion_time

            # Invariant: Open-Meteo is strictly MODELLED_REANALYSIS or NUMERICAL_FORECAST
            # Never label topsoil moisture as physical sensor!
            provenance = ProvenanceMetadata(
                provenance_class=ProvenanceClass.MODELLED_REANALYSIS,
                dataset_origin="open_meteo_forecast_api:current",
                is_synthetic=False,
                scenario_id=None,
                source_uri=self.config.openmeteo_api_url,
                raw_payload_hash=raw_hash,
            )

            idempotency_key = f"openmeteo:current:{self.field_id}:{event_time.isoformat()}"

            cur_event = WeatherContextEvent(
                event_id=str(uuid.uuid4()),
                schema_version="1.0.0",
                event_time=event_time,
                ingestion_time=ingestion_time,
                field_id=self.field_id,
                idempotency_key=idempotency_key,
                correlation_id=None,
                provenance=provenance,
                source_provider="Open-Meteo",
                forecast_reference_time=event_time,
                forecast_horizon_hours=0,
                temperature_2m_c=float(current.get("temperature_2m", 25.0)),
                relative_humidity_2m_pct=float(current.get("relative_humidity_2m", 60.0)),
                dew_point_2m_c=float(current.get("dew_point_2m", 18.0)),
                precipitation_mm=float(current.get("precipitation", 0.0)),
                wind_speed_10m_mps=float(current.get("wind_speed_10m", 2.0)),
                solar_radiation_w_m2=None,
                reanalysis_soil_moisture_0_7cm=float(current.get("soil_moisture_0_to_1cm", 0.25)),
                location=location,
            )
            events.append(cur_event)

        # Process next 6 hours of forecast if present
        hourly = data.get("hourly", {})
        hourly_times = hourly.get("time", [])
        hourly_temps = hourly.get("temperature_2m", [])
        hourly_rhs = hourly.get("relative_humidity_2m", [])
        hourly_precips = hourly.get("precipitation", [])
        hourly_solars = hourly.get("direct_normal_irradiance", [])

        ref_time = events[0].event_time if events else ingestion_time

        for i in range(min(6, len(hourly_times))):
            f_time_str = hourly_times[i]
            if not f_time_str.endswith("Z") and "+" not in f_time_str:
                f_time_str += "+00:00"
            f_event_time = datetime.datetime.fromisoformat(f_time_str).astimezone(datetime.timezone.utc)

            # Skip past forecast hours
            horizon_hours = int((f_event_time - ref_time).total_seconds() // 3600)
            if horizon_hours < 1:
                continue

            f_provenance = ProvenanceMetadata(
                provenance_class=ProvenanceClass.FORECAST,
                dataset_origin="open_meteo_forecast_api:hourly",
                is_synthetic=False,
                scenario_id=None,
                source_uri=self.config.openmeteo_api_url,
                raw_payload_hash=raw_hash,
            )

            f_idempotency_key = f"openmeteo:forecast:{self.field_id}:{ref_time.isoformat()}:h{horizon_hours}"

            f_event = WeatherContextEvent(
                event_id=str(uuid.uuid4()),
                schema_version="1.0.0",
                event_time=f_event_time,
                ingestion_time=ingestion_time,
                field_id=self.field_id,
                idempotency_key=f_idempotency_key,
                correlation_id=None,
                provenance=f_provenance,
                source_provider="Open-Meteo",
                forecast_reference_time=ref_time,
                forecast_horizon_hours=horizon_hours,
                temperature_2m_c=float(hourly_temps[i]) if i < len(hourly_temps) else 25.0,
                relative_humidity_2m_pct=float(hourly_rhs[i]) if i < len(hourly_rhs) else 60.0,
                dew_point_2m_c=None,
                precipitation_mm=float(hourly_precips[i]) if i < len(hourly_precips) else 0.0,
                wind_speed_10m_mps=None,
                solar_radiation_w_m2=float(hourly_solars[i]) if i < len(hourly_solars) else None,
                reanalysis_soil_moisture_0_7cm=None,
                location=location,
            )
            events.append(f_event)

        return events

    def poll_once(self) -> int:
        """Polls Open-Meteo once and emits weather context events."""
        try:
            data = self.execute_with_retry(
                self._fetch_forecast_data,
                max_retries=2,
                initial_backoff=1.5,
                max_backoff=10.0,
            )
            raw_payload_str = str(data)
            events = self.parse_weather_payload(data, raw_payload_str)

            published_count = 0
            for ev in events:
                if self.producer.publish_weather_context(ev, topic=self.config.topic_weather_data):
                    published_count += 1

            logger.info("Adapter '%s' published %d weather context events.", self.adapter_name, published_count)
            return published_count

        except Exception as exc:
            logger.error("Poll cycle failed for adapter '%s': %s", self.adapter_name, exc)
            METRICS.record_failure(self.adapter_name, exc.__class__.__name__)
            dlq_record = wrap_in_dead_letter(
                raw_payload=f"openmeteo_lat:{self.lat}_lon:{self.lon}",
                failed_topic=self.config.topic_weather_data,
                error=exc,
            )
            self.producer.publish_dlq(dlq_record)
            return 0
