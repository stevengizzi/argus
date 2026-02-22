"""API route handlers.

Each module defines a router that is aggregated into the main api_router.
All routes are mounted under /api/v1 prefix.
"""

from fastapi import APIRouter

from argus.api.routes.auth import router as auth_router

# Main API router that aggregates all route modules
api_router = APIRouter()

# Mount auth routes
api_router.include_router(auth_router, prefix="/auth")
