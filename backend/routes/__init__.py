"""Backend API routes package."""

from backend.routes.scenarios import router as scenarios_router
from backend.routes.telemetry import router as telemetry_router

__all__ = ["scenarios_router", "telemetry_router"]
