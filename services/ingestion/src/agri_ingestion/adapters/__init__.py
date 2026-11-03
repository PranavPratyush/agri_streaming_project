"""Ingestion adapters package."""

from agri_ingestion.adapters.base import BaseIngestionAdapter
from agri_ingestion.adapters.historical_replay import HistoricalReplayAdapter
from agri_ingestion.adapters.injected_scenarios import InjectedScenarioAdapter
from agri_ingestion.adapters.live_opensensemap import OpenSenseMapAdapter
from agri_ingestion.adapters.openmeteo_context import OpenMeteoContextAdapter

__all__ = [
    "BaseIngestionAdapter",
    "OpenSenseMapAdapter",
    "OpenMeteoContextAdapter",
    "HistoricalReplayAdapter",
    "InjectedScenarioAdapter",
]

