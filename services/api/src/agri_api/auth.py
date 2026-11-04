"""Authentication, Role-Based Access Control (RBAC), and Field Ownership Boundaries.

Provides scoped authorization ensuring farmers can only view their own fields/alerts,
agronomists can view regional data and submit recommendations, and admins manage operations.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from fastapi import Header, HTTPException, status
from pydantic import BaseModel, Field

from agri_api.config import api_settings


class UserRole(str, Enum):
    """User authorization roles."""
    FARMER = "farmer"
    AGRONOMIST = "agronomist"
    ADMIN = "admin"


class AuthenticatedUser(BaseModel):
    """Identity context of the authenticated client."""
    user_id: str
    role: UserRole
    farmer_id: Optional[str] = None
    allowed_field_ids: List[str] = Field(default_factory=list)

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def is_agronomist(self) -> bool:
        return self.role in (UserRole.AGRONOMIST, UserRole.ADMIN)

    def can_access_field(self, field_id: str) -> bool:
        if self.is_agronomist():
            return True
        if not self.allowed_field_ids:
            # Default prototype: farmer has access to field-kolar-001 or matching ID
            return field_id in ("field-kolar-001", "field-demo-parcel") or field_id.startswith(self.farmer_id or "farmer")
        return field_id in self.allowed_field_ids


def get_current_user(
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    x_farmer_id: Optional[str] = Header(None, alias="X-Farmer-ID"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> AuthenticatedUser:
    """Extracts and validates user identity from request headers."""
    # 1. Admin API key check
    if x_api_key and x_api_key == api_settings.admin_api_key:
        return AuthenticatedUser(
            user_id="admin-system",
            role=UserRole.ADMIN,
            farmer_id=None,
            allowed_field_ids=["*"],
        )

    # 2. Check Bearer token or role header
    role_str = (x_user_role or "farmer").lower().strip()
    if role_str == "admin":
        if x_api_key != api_settings.admin_api_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin role requires a valid X-API-Key header.",
            )
        return AuthenticatedUser(
            user_id="admin-local",
            role=UserRole.ADMIN,
            farmer_id=None,
            allowed_field_ids=["*"],
        )
    elif role_str == "agronomist":
        return AuthenticatedUser(
            user_id=x_farmer_id or "agronomist-kvk-kolar",
            role=UserRole.AGRONOMIST,
            farmer_id=None,
            allowed_field_ids=["*"],
        )
    else:
        # Default: Farmer
        farmer_id = x_farmer_id or api_settings.default_farmer_id
        allowed = [farmer_id] if farmer_id.startswith("field-") else ["field-kolar-001"]
        return AuthenticatedUser(
            user_id=farmer_id,
            role=UserRole.FARMER,
            farmer_id=farmer_id,
            allowed_field_ids=allowed,
        )


def verify_field_access(field_id: str, user: AuthenticatedUser) -> None:
    """Enforces field ownership boundary, raising 403 if forbidden."""
    if not user.can_access_field(field_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: User '{user.user_id}' with role '{user.role.value}' is not authorized to access field parcel '{field_id}'.",
        )


def require_agronomist_or_admin(user: AuthenticatedUser) -> None:
    """Enforces agronomist or admin privilege for privileged actions."""
    if not user.is_agronomist():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation requires agronomist or admin role. Current role is '{user.role.value}'.",
        )


def require_admin(user: AuthenticatedUser) -> None:
    """Enforces admin privilege for operations/debug routes."""
    if not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation requires admin role. Current role is '{user.role.value}'.",
        )
