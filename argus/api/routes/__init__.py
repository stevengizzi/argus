"""API route handlers.

Each module defines a router that is aggregated into the main api_router.
All routes are mounted under /api/v1 prefix.
"""

from fastapi import APIRouter

from argus.api.routes.account import router as account_router
from argus.api.routes.auth import router as auth_router
from argus.api.routes.controls import router as controls_router
from argus.api.routes.health import router as health_router
from argus.api.routes.orchestrator import router as orchestrator_router
from argus.api.routes.performance import router as performance_router
from argus.api.routes.positions import router as positions_router
from argus.api.routes.strategies import router as strategies_router
from argus.api.routes.trades import router as trades_router

# Main API router that aggregates all route modules
api_router = APIRouter()

# Mount all route modules
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(account_router, tags=["account"])
api_router.include_router(positions_router, prefix="/positions", tags=["positions"])
api_router.include_router(trades_router, prefix="/trades", tags=["trades"])
api_router.include_router(performance_router, prefix="/performance", tags=["performance"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(strategies_router, prefix="/strategies", tags=["strategies"])
api_router.include_router(controls_router, prefix="/controls", tags=["controls"])
api_router.include_router(orchestrator_router, prefix="/orchestrator", tags=["orchestrator"])
