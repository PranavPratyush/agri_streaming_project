"""Stream validation rules, boundary filtering, and Dead-Letter Queue (DLQ) formatting."""

from __future__ import annotations

import json
import math
from typing import Any
import uuid
from datetime import datetime, timezone

from pyspark.sql import Column, DataFrame
import pyspark.sql.functions as F

from agri_contracts.enums import ObservedVariable, StandardUnit
from agri_contracts.validation import VARIABLE_BOUNDS


def validate_observation_dict(record: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate a raw observation dictionary against contract requirements and agronomic bounds.
    
    Returns (is_valid, error_reason_if_invalid).
    """
    # 1. Base required fields
    required_keys = ["event_id", "schema_version", "event_time", "field_id", "idempotency_key", "variable", "value", "unit"]
    for key in required_keys:
        if key not in record or record[key] is None:
            return False, f"Missing required field '{key}'"

    # 2. Value must be finite numeric
    val = record["value"]
    if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
        return False, f"Observation value must be a finite number, got {val}"

    # 3. Variable recognition
    var_str = record["variable"]
    try:
        var_enum = ObservedVariable(var_str)
    except ValueError:
        return False, f"Unknown observed variable '{var_str}'"

    # 4. Agronomic bounds check
    if var_enum in VARIABLE_BOUNDS:
        min_v, max_v, expected_unit = VARIABLE_BOUNDS[var_enum]
        unit_str = record.get("unit")
        if unit_str != expected_unit.value:
            return False, f"Unit mismatch for '{var_str}': expected '{expected_unit.value}', got '{unit_str}'"
        if val < min_v or val > max_v:
            return False, f"Value {val} out of plausible agronomic range [{min_v}, {max_v}] for '{var_str}'"

    return True, None


def create_dead_letter_dict(
    raw_payload: str,
    failed_topic: str,
    error_reason: str,
    error_class: str = "ValidationError",
    correlation_id: str | None = None,
    partition: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    """Build a DeadLetterRecordEvent dictionary conforming to the canonical DLQ contract."""
    return {
        "dlq_id": str(uuid.uuid4()),
        "failed_topic": failed_topic,
        "source_partition": partition,
        "source_offset": offset,
        "error_reason": error_reason,
        "error_class": error_class,
        "raw_payload": raw_payload,
        "failed_at": datetime.now(timezone.utc).isoformat(),
        "retry_count": 0,
        "correlation_id": correlation_id,
    }


def spark_observation_range_check_expr() -> Column:
    """Build PySpark boolean expression asserting physical boundary compliance."""
    cond = F.lit(True)
    # Check variable boundaries defined in VARIABLE_BOUNDS
    for var_enum, (min_val, max_val, expected_unit) in VARIABLE_BOUNDS.items():
        var_cond = (F.col("parsed.variable") == F.lit(var_enum.value))
        range_cond = (F.col("parsed.value") >= F.lit(min_val)) & (F.col("parsed.value") <= F.lit(max_val))
        unit_cond = (F.col("parsed.unit") == F.lit(expected_unit.value))
        cond = cond & (~var_cond | (range_cond & unit_cond))
    return cond


def spark_filter_valid_observations(parsed_df: DataFrame) -> DataFrame:
    """Filter DataFrame to retain only strictly valid observations."""
    base_valid = (
        F.col("parsed").isNotNull()
        & F.col("parsed.event_id").isNotNull()
        & F.col("parsed.field_id").isNotNull()
        & F.col("parsed.event_time").isNotNull()
        & F.col("parsed.value").isNotNull()
        & ~F.isnan(F.col("parsed.value"))
    )
    range_valid = spark_observation_range_check_expr()
    return parsed_df.filter(base_valid & range_valid)


def spark_filter_invalid_observations(parsed_df: DataFrame, source_topic: str) -> DataFrame:
    """Filter DataFrame for invalid or malformed records, formatting for DLQ output."""
    base_invalid = (
        F.col("parsed").isNull()
        | F.col("parsed.event_id").isNull()
        | F.col("parsed.field_id").isNull()
        | F.col("parsed.event_time").isNull()
        | F.col("parsed.value").isNull()
        | F.isnan(F.col("parsed.value"))
    )
    range_invalid = ~spark_observation_range_check_expr()

    invalid_df = parsed_df.filter(base_invalid | range_invalid)

    reason_expr = F.when(F.col("parsed").isNull(), F.lit("JSON deserialization failure or schema mismatch")) \
                   .when(F.col("parsed.value").isNull() | F.isnan(F.col("parsed.value")), F.lit("Non-finite or null numeric value")) \
                   .when(range_invalid, F.lit("Value out of plausible agronomic boundary or unit mismatch")) \
                   .otherwise(F.lit("Missing mandatory contract fields"))

    return invalid_df.select(
        F.expr("uuid()").alias("dlq_id"),
        F.lit(source_topic).alias("failed_topic"),
        F.col("partition").alias("source_partition"),
        F.col("offset").alias("source_offset"),
        reason_expr.alias("error_reason"),
        F.lit("StreamValidationError").alias("error_class"),
        F.col("raw_value").alias("raw_payload"),
        F.current_timestamp().alias("failed_at"),
        F.lit(0).alias("retry_count"),
        F.col("parsed.correlation_id").alias("correlation_id"),
    )

