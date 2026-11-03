"""PySpark StructType schemas for AgriKafka canonical event contracts."""

from pyspark.sql.types import (
    BooleanType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)


def get_location_schema() -> StructType:
    """Location coordinates schema."""
    return StructType([
        StructField("latitude", DoubleType(), True),
        StructField("longitude", DoubleType(), True),
        StructField("elevation_m", DoubleType(), True),
    ])


def get_sensor_placement_schema() -> StructType:
    """Physical hardware deployment metadata schema."""
    return StructType([
        StructField("depth_cm", DoubleType(), True),
        StructField("height_m", DoubleType(), True),
        StructField("canopy_position", StringType(), True),
        StructField("sensor_model", StringType(), True),
        StructField("serial_number", StringType(), True),
    ])


def get_quality_flags_schema() -> StructType:
    """Quality and sensor health assessment indicators schema."""
    return StructType([
        StructField("is_imputed", BooleanType(), False),
        StructField("is_out_of_range", BooleanType(), False),
        StructField("freshness_latency_sec", DoubleType(), True),
        StructField("sensor_health_flag", StringType(), False),
    ])


def get_provenance_schema() -> StructType:
    """Audit metadata tracking data lineage and isolation schema."""
    return StructType([
        StructField("provenance_class", StringType(), False),
        StructField("dataset_origin", StringType(), False),
        StructField("is_synthetic", BooleanType(), False),
        StructField("scenario_id", StringType(), True),
        StructField("source_uri", StringType(), True),
        StructField("raw_payload_hash", StringType(), True),
    ])


def get_observation_schema() -> StructType:
    """Canonical PySpark schema for AgriObservationEvent (topic: agri.sensor-readings)."""
    return StructType([
        # Base event contract fields
        StructField("event_id", StringType(), False),
        StructField("schema_version", StringType(), False),
        StructField("event_time", TimestampType(), False),
        StructField("ingestion_time", TimestampType(), False),
        StructField("field_id", StringType(), False),
        StructField("idempotency_key", StringType(), False),
        StructField("correlation_id", StringType(), True),
        StructField("provenance", get_provenance_schema(), False),
        # Observation payload fields
        StructField("source_provider", StringType(), False),
        StructField("sensor_id", StringType(), True),
        StructField("station_id", StringType(), True),
        StructField("variable", StringType(), False),
        StructField("value", DoubleType(), False),
        StructField("unit", StringType(), False),
        StructField("location", get_location_schema(), True),
        StructField("sensor_metadata", get_sensor_placement_schema(), True),
        StructField("quality_flags", get_quality_flags_schema(), False),
        StructField("validation_status", StringType(), False),
    ])


def get_weather_schema() -> StructType:
    """Canonical PySpark schema for WeatherContextEvent (topic: agri.weather-data)."""
    return StructType([
        # Base event contract fields
        StructField("event_id", StringType(), False),
        StructField("schema_version", StringType(), False),
        StructField("event_time", TimestampType(), False),
        StructField("ingestion_time", TimestampType(), False),
        StructField("field_id", StringType(), False),
        StructField("idempotency_key", StringType(), False),
        StructField("correlation_id", StringType(), True),
        StructField("provenance", get_provenance_schema(), False),
        # Weather context fields
        StructField("source_provider", StringType(), False),
        StructField("forecast_reference_time", TimestampType(), True),
        StructField("forecast_horizon_hours", IntegerType(), False),
        StructField("temperature_2m_c", DoubleType(), True),
        StructField("relative_humidity_2m_pct", DoubleType(), True),
        StructField("dew_point_2m_c", DoubleType(), True),
        StructField("precipitation_mm", DoubleType(), True),
        StructField("wind_speed_10m_mps", DoubleType(), True),
        StructField("solar_radiation_w_m2", DoubleType(), True),
        StructField("reanalysis_soil_moisture_0_7cm", DoubleType(), True),
        StructField("location", get_location_schema(), False),
    ])


def get_dead_letter_schema() -> StructType:
    """Canonical PySpark schema for DeadLetterRecordEvent (topic: agri.dead-letter-queue)."""
    return StructType([
        StructField("dlq_id", StringType(), False),
        StructField("failed_topic", StringType(), False),
        StructField("source_partition", IntegerType(), True),
        StructField("source_offset", LongType(), True),
        StructField("error_reason", StringType(), False),
        StructField("error_class", StringType(), False),
        StructField("raw_payload", StringType(), False),
        StructField("failed_at", TimestampType(), False),
        StructField("retry_count", IntegerType(), False),
        StructField("correlation_id", StringType(), True),
    ])

