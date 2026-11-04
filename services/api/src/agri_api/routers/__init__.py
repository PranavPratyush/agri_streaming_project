"""API Routers export."""

from agri_api.routers.fields import router as fields_router
from agri_api.routers.telemetry import router as telemetry_router
from agri_api.routers.alerts import router as alerts_router
from agri_api.routers.investigations import router as investigations_router
from agri_api.routers.advisories import router as advisories_router
from agri_api.routers.operations import router as operations_router
from agri_api.routers.debug import router as debug_router

__all__ = [
    "fields_router",
    "telemetry_router",
    "alerts_router",
    "investigations_router",
    "advisories_router",
    "operations_router",
    "debug_router",
]

