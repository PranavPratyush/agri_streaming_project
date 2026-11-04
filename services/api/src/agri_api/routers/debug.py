"""Local development admin and debug endpoints."""

from __future__ import annotations

import sys
from typing import Any, Dict
from fastapi import APIRouter, Depends

from agri_api.auth import AuthenticatedUser, get_current_user, require_admin
from agri_api.dependencies import get_repository

router = APIRouter(prefix="/admin/debug", tags=["Admin Debug"])


@router.get("/state", summary="Inspect low-level debugging state (Admin only)")
def get_debug_state(
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> Dict[str, Any]:
    require_admin(current_user)
    return {
        "python_version": sys.version,
        "repository_adapter": type(repo).__name__,
        "user_context": current_user.model_dump(),
        "registered_fields_count": len(repo.list_field_profiles()),
        "cached_investigations_count": len(getattr(repo, "investigations", {})),
    }

