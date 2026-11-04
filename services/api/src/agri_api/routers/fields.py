"""Farm and field profile management endpoints."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from agri_api.auth import AuthenticatedUser, get_current_user, require_agronomist_or_admin, verify_field_access
from agri_api.dependencies import get_repository
from agri_api.models.common import ActionStatusResponse, PaginatedResponse
from agri_api.models.fields import FieldProfileCreate, FieldProfileResponse, FieldProfileUpdate, FieldStatusResponse

router = APIRouter(prefix="/fields", tags=["Fields & Parcels"])


@router.get("", response_model=PaginatedResponse[FieldProfileResponse], summary="List farm and field profiles")
def list_fields(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    all_fields = repo.list_field_profiles(is_active=is_active)
    # Enforce field ownership boundary for farmer role
    if not current_user.is_agronomist():
        all_fields = [f for f in all_fields if current_user.can_access_field(f["field_id"])]

    total = len(all_fields)
    sliced = all_fields[offset : offset + limit]
    return PaginatedResponse(
        items=[FieldProfileResponse.model_validate(f) for f in sliced],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.post("", response_model=ActionStatusResponse, status_code=status.HTTP_201_CREATED, summary="Register a field parcel")
def create_field(
    payload: FieldProfileCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    require_agronomist_or_admin(current_user)
    repo.upsert_field_profile(payload.model_dump())
    repo.record_system_audit(
        action="REGISTER_FIELD",
        actor=current_user.user_id,
        entity_type="field_profile",
        entity_id=payload.field_id,
        details={"name": payload.name, "variety": payload.variety},
    )
    return ActionStatusResponse(
        success=True,
        action="REGISTER_FIELD",
        entity_id=payload.field_id,
        message=f"Field parcel '{payload.field_id}' successfully registered.",
    )


@router.get("/{field_id}", response_model=FieldProfileResponse, summary="Get field parcel profile")
def get_field(
    field_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    verify_field_access(field_id, current_user)
    profile = repo.get_field_profile(field_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Field parcel '{field_id}' not found.",
        )
    return FieldProfileResponse.model_validate(profile)


@router.patch("/{field_id}", response_model=ActionStatusResponse, summary="Update field parcel metadata")
@router.put("/{field_id}", response_model=ActionStatusResponse, summary="Update field parcel metadata")
def update_field(
    field_id: str,
    payload: FieldProfileUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    verify_field_access(field_id, current_user)
    profile = repo.get_field_profile(field_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Field parcel '{field_id}' not found.",
        )

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    profile.update(updates)
    repo.upsert_field_profile(profile)
    repo.record_system_audit(
        action="UPDATE_FIELD",
        actor=current_user.user_id,
        entity_type="field_profile",
        entity_id=field_id,
        details=updates,
    )
    return ActionStatusResponse(
        success=True,
        action="UPDATE_FIELD",
        entity_id=field_id,
        message=f"Field parcel '{field_id}' updated successfully.",
    )


@router.get("/{field_id}/status", response_model=FieldStatusResponse, summary="Get real-time operational status and data freshness")
def get_field_status(
    field_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
):
    verify_field_access(field_id, current_user)
    profile = repo.get_field_profile(field_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Field parcel '{field_id}' not found.",
        )

    freshness_list = repo.get_sensor_freshness(field_id)
    latest_latency = min([f.get("latency_seconds") or 30.0 for f in freshness_list]) if freshness_list else 15.0

    # Determine freshness status
    if latest_latency <= 60.0:
        freshness_status = "FRESH"
    elif latest_latency <= 300.0:
        freshness_status = "WARM"
    else:
        freshness_status = "STALE"

    alerts = repo.list_recent_alerts(field_id=field_id, hours=24)
    active_alerts = [a for a in alerts if a.get("status") in ("CANDIDATE", "ACTIVE")]
    recs = repo.list_farmer_recommendations(field_id=field_id, approval_status="PROPOSED")

    csi = float(active_alerts[0].get("composite_stress_index", 0.35)) if active_alerts else 0.25
    severity = active_alerts[0].get("severity", "NORMAL") if active_alerts else "NORMAL"
    health_state = active_alerts[0].get("sensor_health_state", "HEALTHY") if active_alerts else "HEALTHY"

    obs = repo.get_field_observations(field_id=field_id, limit=5)
    soil_val = next((o["numeric_value"] for o in obs if o["observed_variable"] == "soil_moisture"), 0.14)
    temp_val = next((o["numeric_value"] for o in obs if o["observed_variable"] == "ambient_temp"), 30.5)

    return FieldStatusResponse(
        field_id=field_id,
        crop_variety=profile.get("variety", "GPU-28"),
        growth_stage=profile.get("current_growth_stage", "flowering"),
        composite_stress_index=csi,
        risk_level=severity,
        sensor_health_overall=health_state,
        latest_soil_moisture=soil_val,
        latest_ambient_temp=temp_val,
        telemetry_latency_seconds=latest_latency,
        active_alerts_count=len(active_alerts),
        pending_advisories_count=len(recs),
        data_freshness_status=freshness_status,
    )
