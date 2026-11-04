"""Candidate agricultural alerts and streaming evidence endpoints."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from agri_api.auth import AuthenticatedUser, get_current_user, verify_field_access
from agri_api.dependencies import get_repository
from agri_api.models.alerts import AlertEvidenceResponse, CandidateAlertResponse
from agri_api.models.common import PaginatedResponse

router = APIRouter(prefix="/alerts", tags=["Candidate Alerts"])


@router.get("", response_model=PaginatedResponse[CandidateAlertResponse], summary="List streaming candidate alerts")
def list_alerts(
    field_id: Optional[str] = Query(None, description="Filter by field parcel"),
    severity: Optional[str] = Query(None, description="Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)"),
    hours: int = Query(72, ge=1, le=720),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    if field_id:
        verify_field_access(field_id, current_user)

    alerts = repo.list_recent_alerts(field_id=field_id, hours=hours, limit=limit + offset)

    # Enforce field ownership filter for farmers
    if not current_user.is_agronomist():
        alerts = [a for a in alerts if current_user.can_access_field(a["field_id"])]

    if severity:
        alerts = [a for a in alerts if a.get("severity") == severity]

    total = len(alerts)
    sliced = alerts[offset : offset + limit]
    return PaginatedResponse(
        items=[CandidateAlertResponse.model_validate(a) for a in sliced],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.get("/{alert_id}", response_model=CandidateAlertResponse, summary="Get candidate alert details")
def get_alert(
    alert_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    alert = repo.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate alert '{alert_id}' not found.",
        )
    verify_field_access(alert["field_id"], current_user)
    return CandidateAlertResponse.model_validate(alert)


@router.get("/{alert_id}/evidence", response_model=AlertEvidenceResponse, summary="Get corroborating evidence for a candidate alert")
def get_alert_evidence(
    alert_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    alert = repo.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate alert '{alert_id}' not found.",
        )
    verify_field_access(alert["field_id"], current_user)

    obs = repo.get_field_observations(field_id=alert["field_id"], limit=10)
    health = repo.get_field_sensor_health(field_id=alert["field_id"], limit=1)

    return AlertEvidenceResponse(
        alert_id=alert["alert_id"],
        field_id=alert["field_id"],
        event_time=alert["event_time"],
        alert_type=alert["alert_type"],
        severity=alert["severity"],
        composite_stress_index=alert["composite_stress_index"],
        contributing_features=alert.get("contributing_features", []),
        telemetry_readings=obs,
        sensor_health_diagnosis=health[0] if health else {"status": "HEALTHY", "reason": "ALL_SENSORS_VALID"},
    )

