"""AgriKafka-Agent Ingestion Service package."""

from agri_ingestion.adapters import (
    BaseIngestionAdapter,
    HistoricalReplayAdapter,
    InjectedScenarioAdapter,
    OpenMeteoContextAdapter,
    OpenSenseMapAdapter,
)
from agri_ingestion.config import IngestionConfig
from agri_ingestion.metrics import METRICS
from agri_ingestion.producer import AgriKafkaProducer

__all__ = [
    "IngestionConfig",
    "AgriKafkaProducer",
    "METRICS",
    "BaseIngestionAdapter",
    "OpenSenseMapAdapter",
    "OpenMeteoContextAdapter",
    "HistoricalReplayAdapter",
    "InjectedScenarioAdapter",
]

