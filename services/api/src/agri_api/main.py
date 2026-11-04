"""Main FastAPI application entrypoint for AgriKafka-Agent."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agri_api.config import api_settings
from agri_api.models.common import ErrorResponse
from agri_api.routers import (
    advisories_router,
    alerts_router,
    debug_router,
    fields_router,
    investigations_router,
    operations_router,
    telemetry_router,
)

logger = logging.getLogger("agri_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown procedures."""
    logger.info("Starting AgriKafka-Agent Backend API service...")
    yield
    logger.info("Shutting down AgriKafka-Agent Backend API service...")


def create_app() -> FastAPI:
    """Factory function initializing the FastAPI application."""
    app = FastAPI(
        title=api_settings.title,
        version=api_settings.version,
        description=api_settings.description,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Custom Exception Handlers
    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error_code=f"HTTP_{exc.status_code}",
                message=exc.detail if isinstance(exc.detail, str) else "Request error",
                details=exc.detail if isinstance(exc.detail, dict) else None,
                request_id=request.headers.get("X-Request-ID"),
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled API exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error_code="INTERNAL_SERVER_ERROR",
                message="An unexpected server error occurred. Please contact system operations.",
                details={"error_type": type(exc).__name__},
                request_id=request.headers.get("X-Request-ID"),
            ).model_dump(),
        )

    # 3. Mount Routers
    # Root level operations (liveness, readiness, metrics)
    app.include_router(operations_router)

    # Versioned API routes under /api/v1
    v1_prefix = api_settings.api_prefix
    app.include_router(fields_router, prefix=v1_prefix)
    app.include_router(telemetry_router, prefix=v1_prefix)
    app.include_router(alerts_router, prefix=v1_prefix)
    app.include_router(investigations_router, prefix=v1_prefix)
    app.include_router(advisories_router, prefix=v1_prefix)
    app.include_router(debug_router, prefix=v1_prefix)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agri_api.main:app", host=api_settings.host, port=api_settings.port, reload=True)

