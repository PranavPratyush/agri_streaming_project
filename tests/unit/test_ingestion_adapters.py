"""Comprehensive unit test suite for AgriKafka-Agent Ingestion Layer adapters, retry, and DLQ routing."""

import datetime
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import requests
from agri_contracts import (
    AgriObservationEvent,
    ObservedVariable,
    ProvenanceClass,
    SensorHealthFlag,
    StandardUnit,
    ValidationStatus,
    WeatherContextEvent,
)
from agri_ingestion.adapters.historical_replay import HistoricalReplayAdapter
from agri_ingestion.adapters.injected_scenarios import InjectedScenarioAdapter
from agri_ingestion.adapters.live_opensensemap import OpenSenseMapAdapter
from agri_ingestion.adapters.openmeteo_context import OpenMeteoContextAdapter
from agri_ingestion.config import IngestionConfig
from agri_ingestion.metrics import METRICS
from agri_ingestion.producer import AgriKafkaProducer


# ---------------------------------------------------------------------------
# Mock Payloads
# ---------------------------------------------------------------------------
MOCK_OPENSENSEMAP_BOX = {
    "_id": "689b2bdc569c2d0007586ae9",
    "name": "Sarvamangalam",
    "currentLocation": {"coordinates": [79.804492, 11.995079]},
    "sensors": [
        {
            "_id": "689b2bdc569c2d0007586aea",
            "title": "Temperatur",
            "unit": "°C",
            "sensorType": "Generic temperature sensor",
            "lastMeasurement": {
                "createdAt": "2026-11-01T14:43:14.940Z",
                "value": "25.39",
            },
        },
        {
            "_id": "689b2bdc569c2d0007586aeb",
            "title": "rel. Luftfeuchte",
            "unit": "%",
            "sensorType": "Generic humidity sensor",
            "lastMeasurement": {
                "createdAt": "2026-11-01T14:43:14.940Z",
                "value": "93.0",
            },
        },
        {
            "_id": "689b2bdc569c2d0007586aec",
            "title": "Luftdruck",
            "unit": "hPa",
            "sensorType": "Generic pressure sensor",
            "lastMeasurement": {
                "createdAt": "2026-11-01T14:43:14.940Z",
                "value": "1016.8",
            },
        },
        {
            "_id": "689b2bdc569c2d0007586aed",
            "title": "Niederschlag",
            "unit": "mm",
            "sensorType": "Generic rain gauge",
            "lastMeasurement": {
                "createdAt": "2026-11-01T14:43:14.940Z",
                "value": "0.0",
            },
        },
    ],
}

MOCK_OPENMETEO_FORECAST = {
    "latitude": 13.137,
    "longitude": 78.129,
    "elevation": 822.0,
    "current": {
        "time": "2026-11-01T15:00",
        "temperature_2m": 24.8,
        "relative_humidity_2m": 65.0,
        "dew_point_2m": 17.6,
        "precipitation": 0.0,
        "wind_speed_10m": 3.1,
        "soil_moisture_0_to_1cm": 0.28,
    },
    "hourly": {
        "time": [
            "2026-11-01T16:00",
            "2026-11-01T17:00",
            "2026-11-01T18:00",
        ],
        "temperature_2m": [24.0, 23.1, 22.0],
        "relative_humidity_2m": [68.0, 72.0, 75.0],
        "precipitation": [0.0, 0.0, 0.2],
        "direct_normal_irradiance": [450.0, 150.0, 0.0],
    },
}


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------
class TestOpenSenseMapAdapter:
    """Tests for the live physical station adapter."""

    def test_parse_station_payload_success(self):
        config = IngestionConfig()
        producer = AgriKafkaProducer(config=config, dry_run=True)
        adapter = OpenSenseMapAdapter(station_id="689b2bdc569c2d0007586ae9", config=config, producer=producer, dry_run=True)

        events = adapter.parse_station_payload(MOCK_OPENSENSEMAP_BOX, json.dumps(MOCK_OPENSENSEMAP_BOX))
        assert len(events) == 4

        # Verify temperature event
        temp_ev = next(e for e in events if e.variable == ObservedVariable.TEMPERATURE_2M)
        assert temp_ev.value == 25.39
        assert temp_ev.unit == StandardUnit.CELSIUS
        assert temp_ev.provenance.provenance_class == ProvenanceClass.PHYSICAL_SENSOR
        assert temp_ev.provenance.is_synthetic is False
        assert temp_ev.station_id == "689b2bdc569c2d0007586ae9"
        assert temp_ev.sensor_id == "689b2bdc569c2d0007586aea"
        assert temp_ev.field_id == "FIELD-KA-KOLAR-001"
        assert temp_ev.event_time.tzinfo == datetime.timezone.utc
        assert temp_ev.location.latitude == 11.995079
        assert temp_ev.location.longitude == 79.804492

        # Verify deduplication on re-parse of same measurement
        events_dup = adapter.parse_station_payload(MOCK_OPENSENSEMAP_BOX, json.dumps(MOCK_OPENSENSEMAP_BOX))
        assert len(events_dup) == 0

    def test_stale_detection(self):
        config = IngestionConfig()
        producer = AgriKafkaProducer(config=config, dry_run=True)
        adapter = OpenSenseMapAdapter(config=config, producer=producer, dry_run=True)

        # Measurement from 2 hours ago
        stale_payload = {
            "sensors": [
                {
                    "_id": "s1",
                    "title": "Temperatur",
                    "unit": "°C",
                    "lastMeasurement": {
                        "createdAt": "2026-11-01T10:00:00Z",
                        "value": "20.0",
                    },
                }
            ]
        }
        events = adapter.parse_station_payload(stale_payload, json.dumps(stale_payload))
        assert len(events) == 1
        assert events[0].quality_flags.sensor_health_flag == SensorHealthFlag.DROPOUT
        assert events[0].validation_status == ValidationStatus.STALE
        assert events[0].quality_flags.freshness_latency_sec > 90.0

    @patch("requests.Session.get")
    def test_poll_once_with_mocked_http(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_OPENSENSEMAP_BOX
        mock_get.return_value = mock_resp

        producer = AgriKafkaProducer(dry_run=True)
        adapter = OpenSenseMapAdapter(producer=producer, dry_run=True)

        published = adapter.poll_once()
        assert published == 4
        assert len(producer.get_published_history()) == 4

    @patch("requests.Session.get")
    def test_rate_limit_and_dlq_on_error(self, mock_get):
        # Return 429 then 500
        mock_resp_429 = MagicMock()
        mock_resp_429.status_code = 429
        mock_resp_429.raise_for_status.side_effect = requests.HTTPError("429 Rate Limit")
        mock_get.return_value = mock_resp_429

        producer = AgriKafkaProducer(dry_run=True)
        adapter = OpenSenseMapAdapter(producer=producer, dry_run=True)

        # Should fail retries and route to DLQ
        published = adapter.poll_once()
        assert published == 0

        # DLQ should have received a failure record
        history = producer.get_published_history()
        assert len(history) == 1
        assert history[0]["topic"] == "agri.dead-letter-queue"
        assert "429" in history[0]["data"].error_reason


class TestOpenMeteoContextAdapter:
    """Tests for the weather context and forecast adapter."""

    def test_parse_weather_payload_success(self):
        config = IngestionConfig()
        producer = AgriKafkaProducer(config=config, dry_run=True)
        adapter = OpenMeteoContextAdapter(config=config, producer=producer, dry_run=True)

        events = adapter.parse_weather_payload(MOCK_OPENMETEO_FORECAST, json.dumps(MOCK_OPENMETEO_FORECAST))
        assert len(events) >= 1

        # Check current observation
        cur = events[0]
        assert isinstance(cur, WeatherContextEvent)
        assert cur.temperature_2m_c == 24.8
        assert cur.relative_humidity_2m_pct == 65.0
        assert cur.reanalysis_soil_moisture_0_7cm == 0.28
        assert cur.forecast_horizon_hours == 0
        assert cur.provenance.provenance_class == ProvenanceClass.MODELLED_REANALYSIS
        assert cur.provenance.is_synthetic is False

        # Verify hourly forecast horizons
        forecasts = [e for e in events if e.forecast_horizon_hours > 0]
        for f in forecasts:
            assert f.provenance.provenance_class == ProvenanceClass.FORECAST
            assert f.forecast_horizon_hours in (1, 2, 3)

    @patch("requests.Session.get")
    def test_poll_once_with_mocked_http(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_OPENMETEO_FORECAST
        mock_get.return_value = mock_resp

        producer = AgriKafkaProducer(dry_run=True)
        adapter = OpenMeteoContextAdapter(producer=producer, dry_run=True)

        published = adapter.poll_once()
        assert published >= 1
        assert producer.get_published_history()[0]["topic"] == "agri.weather-data"


class TestHistoricalReplayAdapter:
    """Tests for the historical Open-Meteo CSV dataset replay adapter."""

    def test_replay_streaming_and_ordering(self):
        producer = AgriKafkaProducer(dry_run=True)
        adapter = HistoricalReplayAdapter(
            speed_multiplier=0.0,  # instantaneous
            producer=producer,
            dry_run=True,
        )

        batches = list(adapter.stream_dataset(max_rows=3))
        assert len(batches) == 3

        # Each row yields 7 variables
        assert len(batches[0]) == 7
        ev0 = batches[0][0]
        assert isinstance(ev0, AgriObservationEvent)
        assert ev0.provenance.provenance_class == ProvenanceClass.HISTORICAL_REPLAY
        assert ev0.provenance.is_synthetic is False
        assert ev0.source_provider == "open_meteo_archive_replay"

    def test_checkpoint_save_and_resume(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_checkpoint = tmp.name

        try:
            producer = AgriKafkaProducer(dry_run=True)
            # Run first 2 rows
            adapter1 = HistoricalReplayAdapter(
                speed_multiplier=0.0,
                checkpoint_file=tmp_checkpoint,
                producer=producer,
                dry_run=True,
            )
            count1 = adapter1.run_replay(max_rows=2)
            assert count1 == 14

            # Resume with new adapter instance pointing to same checkpoint
            adapter2 = HistoricalReplayAdapter(
                speed_multiplier=0.0,
                checkpoint_file=tmp_checkpoint,
                producer=producer,
                dry_run=True,
            )
            # Replay up to 4 rows total (should only emit rows 2 and 3 = 14 events)
            count2 = adapter2.run_replay(max_rows=4)
            assert count2 == 14
        finally:
            if os.path.exists(tmp_checkpoint):
                os.remove(tmp_checkpoint)


class TestInjectedScenarioAdapter:
    """Tests for deterministic stress and fault injection scenarios."""

    @pytest.mark.parametrize("scenario_type", InjectedScenarioAdapter.SCENARIO_TYPES)
    def test_scenario_generation(self, scenario_type):
        producer = AgriKafkaProducer(dry_run=True)
        adapter = InjectedScenarioAdapter(
            scenario_type=scenario_type,
            steps=5,
            producer=producer,
            dry_run=True,
        )

        events = adapter.generate_events()
        assert len(events) == 5

        for ev in events:
            assert ev.provenance.provenance_class == ProvenanceClass.INJECTED_SCENARIO
            assert ev.provenance.is_synthetic is True
            assert ev.provenance.scenario_id == scenario_type
            assert ev.source_provider == "scenario_injection_harness"
            assert ev.field_id == "FIELD-KA-KOLAR-001"

    def test_stuck_value_sensor_fault(self):
        adapter = InjectedScenarioAdapter(scenario_type="sensor_stuck_value", steps=4, dry_run=True)
        events = adapter.generate_events()
        # All values should be identical
        vals = [e.value for e in events]
        assert len(set(vals)) == 1
        assert events[0].quality_flags.sensor_health_flag == SensorHealthFlag.STUCK_VALUE

    def test_drought_drydown_ragi(self):
        adapter = InjectedScenarioAdapter(scenario_type="drought_drydown_ragi", steps=5, dry_run=True)
        events = adapter.generate_events()
        vals = [e.value for e in events]
        # Soil moisture strictly decreasing
        assert vals[0] > vals[-1]
        assert events[0].variable == ObservedVariable.SOIL_MOISTURE_15CM
