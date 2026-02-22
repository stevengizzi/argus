"""Authentication routes for the Command Center API.

Provides login and token refresh endpoints.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from argus.api.auth import (
    create_access_token,
    require_auth,
    resolve_jwt_secret,
    verify_password,
)
from argus.api.dependencies import AppState, get_app_state

if TYPE_CHECKING:
    pass

router = APIRouter(tags=["auth"])


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """Login request body."""

    password: str


class TokenResponse(BaseModel):
    """Token response for login and refresh endpoints."""

    access_token: str
    token_type: str = "bearer"
    expires_at: str  # ISO 8601 UTC timestamp


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> TokenResponse:
    """Authenticate with password and receive a JWT token.

    Args:
        request: Login request containing password.
        state: Application state with config.

    Returns:
        TokenResponse with access token and expiration.

    Raises:
        HTTPException 401: If password is invalid.
        HTTPException 500: If auth not configured.
    """
    # Validate config exists
    if not state.config or not state.config.api:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API configuration not available",
        )

    api_config = state.config.api

    # Check password
    if not verify_password(request.password, api_config.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Get JWT secret and create token
    jwt_secret = resolve_jwt_secret(api_config)
    token, expires_at = create_access_token(jwt_secret, api_config.jwt_expiry_hours)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_at=expires_at.isoformat(),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> TokenResponse:
    """Refresh an existing valid token with a new one.

    Requires a valid (non-expired) token in the Authorization header.

    Args:
        _auth: Decoded token payload (validated by require_auth).
        state: Application state with config.

    Returns:
        TokenResponse with new access token and expiration.
    """
    if not state.config or not state.config.api:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API configuration not available",
        )

    api_config = state.config.api

    # Get JWT secret and create new token
    jwt_secret = resolve_jwt_secret(api_config)
    token, expires_at = create_access_token(jwt_secret, api_config.jwt_expiry_hours)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_at=expires_at.isoformat(),
    )


@router.get("/me")
async def get_current_user(
    _auth: dict = Depends(require_auth),  # noqa: B008
) -> dict:
    """Get current authenticated user info.

    This is a simple endpoint to verify authentication works.
    Returns the token subject ("operator" for single-user system).

    Args:
        _auth: Decoded token payload (validated by require_auth).

    Returns:
        Dict with user info and timestamp.
    """
    return {
        "user": _auth.get("sub", "unknown"),
        "timestamp": datetime.now(UTC).isoformat(),
    }
