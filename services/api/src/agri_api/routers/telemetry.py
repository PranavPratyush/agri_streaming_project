"""Telemetry, observation time-series, and sensor-health endpoints."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from agri_api.auth import AuthenticatedUser, get_current_user, verify_field_access
from agri_api.config import api_settings
from agri_api.dependencies import get_repository
from agri_api.models.common import PaginatedResponse
from agri_api.models.telemetry import (
    FieldTrendsResponse,
    ObservationResponse,
    SensorFreshnessResponse,
    SensorHealthEventResponse,
)

router = APIRouter(tags=["Telemetry & Sensors"])


@router.get("/fields/{field_id}/observations", response_model=PaginatedResponse[ObservationResponse], summary="Get time-series observations")
def get_field_observations(
    field_id: str,
    variable: Optional[str] = Query(None, description="Filter by variable (e.g. soil_moisture, ambient_temp)"),
    hours: int = Query(24, ge=1, le=api_settings.max_time_window_hours),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    verify_field_access(field_id, current_user)
    obs = repo.get_field_observations(field_id=field_id, variable=variable, hours=hours, limit=limit + offset)
    total = len(obs)
    sliced = obs[offset : offset + limit]
    return PaginatedResponse(
        items=[ObservationResponse.model_validate(o) for o in sliced],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.get("/fields/{field_id}/trends", response_model=FieldTrendsResponse, summary="Get aggregated field temporal trends")
def get_field_trends(
    field_id: str,
    hours: int = Query(24, ge=1, le=api_settings.max_time_window_hours),
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    verify_field_access(field_id, current_user)
    obs = repo.get_field_observations(field_id=field_id, hours=hours, limit=500)
    soil_vals = [o["numeric_value"] for o in obs if o["observed_variable"] == "soil_moisture"]
    temp_vals = [o["numeric_value"] for o in obs if o["observed_variable"] == "ambient_temp"]

    min_soil = min(soil_vals) if soil_vals else None
    avg_soil = round(sum(soil_vals) / len(soil_vals), 4) if soil_vals else None
    max_temp = max(temp_vals) if temp_vals else None

    # Determine simple trend from earliest to latest reading
    trend = "STABLE"
    if len(soil_vals) >= 2:
        diff = soil_vals[0] - soil_vals[-1]  # index 0 is most recent
        if diff < -0.01:
            trend = "DEPLETING"
        elif diff > 0.01:
            trend = "RECOVERING"

    return FieldTrendsResponse(
        field_id=field_id,
        time_window_hours=hours,
        data_points=len(obs),
        soil_moisture_trend=trend,
        min_soil_moisture=min_soil,
        avg_soil_moisture=avg_soil,
        max_ambient_temp=max_temp,
        accumulated_rain_mm=0.0,
    )


@router.get("/fields/{field_id}/sensor-health", response_model=PaginatedResponse[SensorHealthEventResponse], summary="Get forensic sensor health events")
def get_field_sensor_health(
    field_id: str,
    hours: int = Query(24, ge=1, le=api_settings.max_time_window_hours),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    verify_field_access(field_id, current_user)
    events = repo.get_field_sensor_health(field_id=field_id, hours=hours, limit=limit + offset)
    total = len(events)
    sliced = events[offset : offset + limit]
    return PaginatedResponse(
        items=[SensorHealthEventResponse.model_validate(e) for e in sliced],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.get("/sensors/freshness", response_model=List[SensorFreshnessResponse], summary="Get platform sensor freshness status")
def get_sensors_freshness(
    field_id: Optional[str] = Query(None, description="Optional field ID filter"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    if field_id:
        verify_field_access(field_id, current_user)

    freshness_list = repo.get_sensor_freshness(field_id=field_id)
    if not current_user.is_agronomist():
        freshness_list = [f for f in freshness_list if current_user.can_access_field(f["field_id"])]

    results = []
    for f in freshness_list:
        lat = f.get("latency_seconds") or 30.0
        if lat <= 60.0:
            cat = "FRESH"
        elif lat <= 300.0:
            cat = "WARM"
        elif lat <= 3600.0:
            cat = "STALE"
        else:
            cat = "OFFLINE"

        results.append(
            SensorFreshnessResponse(
                sensor_id=f["sensor_id"],
                field_id=f["field_id"],
                sensor_model=f.get("sensor_model", "Standard-Sensor"),
                measured_variable=f.get("measured_variable", "telemetry"),
                unit=f.get("unit", ""),
                provenance_type=f.get("provenance_type", "physical_sensor"),
                last_event_time=f.get("last_event_time"),
                last_value=f.get("last_value"),
                latency_seconds=lat,
                health_state=f.get("health_state", "HEALTHY"),
                reason_code=f.get("reason_code", "ALL_SENSORS_VALID"),
                freshness_category=cat,
            )
        )
    return results

