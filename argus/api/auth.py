"""JWT authentication for the Command Center API.

Provides password verification, token creation/verification, and FastAPI
dependencies for protecting routes.

Usage:
    # Verify password on login
    if verify_password(plain_password, stored_hash):
        token, expires_at = create_access_token(jwt_secret, expires_hours=api_config.jwt_expiry_hours)

    # Protect a route
    @router.get("/protected")
    async def protected_route(_auth: dict = Depends(require_auth)):
        return {"message": "authenticated"}
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

if TYPE_CHECKING:
    from argus.core.config import ApiConfig

ALGORITHM = "HS256"

# HTTPBearer extracts the token from "Authorization: Bearer <token>" header
security = HTTPBearer(auto_error=False)

# Module-level JWT secret, set during app startup via set_jwt_secret()
_jwt_secret: str = ""


def set_jwt_secret(secret: str) -> None:
    """Set the JWT secret for token verification.

    Called during app startup to inject the secret from config/env.

    Args:
        secret: The JWT signing secret.
    """
    global _jwt_secret
    _jwt_secret = secret


def get_jwt_secret() -> str:
    """Get the current JWT secret.

    Returns:
        The JWT signing secret.

    Raises:
        HTTPException: If the secret is not configured.
    """
    if not _jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT secret not configured",
        )
    return _jwt_secret


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash.

    Args:
        plain_password: The plaintext password to verify.
        hashed_password: The bcrypt hash to verify against.

    Returns:
        True if the password matches, False otherwise.
    """
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        # Invalid hash format or other error
        return False


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: The plaintext password to hash.

    Returns:
        The bcrypt hash of the password.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def create_access_token(jwt_secret: str, expires_hours: int) -> tuple[str, datetime]:
    """Create a JWT access token.

    Args:
        jwt_secret: The secret key for signing the token.
        expires_hours: Hours until the token expires. Required — every call
            site passes ``api_config.jwt_expiry_hours``; no implicit default.

    Returns:
        Tuple of (token string, expiration datetime).
    """
    expires_at = datetime.now(UTC) + timedelta(hours=expires_hours)
    payload = {
        "exp": expires_at,
        "iat": datetime.now(UTC),
        "sub": "operator",  # Single user system
    }
    token = jwt.encode(payload, jwt_secret, algorithm=ALGORITHM)
    return token, expires_at


def verify_token(token: str, jwt_secret: str) -> dict:
    """Verify and decode a JWT token.

    Args:
        token: The JWT token to verify.
        jwt_secret: The secret key used to sign the token.

    Returns:
        The decoded token payload.

    Raises:
        HTTPException: If the token is invalid or expired.
    """
    try:
        return jwt.decode(token, jwt_secret, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from None


def resolve_jwt_secret(api_config: ApiConfig) -> str:
    """Resolve JWT secret from environment variable named in config.

    Args:
        api_config: The API configuration containing jwt_secret_env.

    Returns:
        The JWT secret from the environment variable.

    Raises:
        HTTPException: If the environment variable is not set.
    """
    secret = os.environ.get(api_config.jwt_secret_env, "")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"JWT secret not configured (env var: {api_config.jwt_secret_env})",
        )
    return secret


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),  # noqa: B008
) -> dict:
    """FastAPI dependency that validates JWT from Authorization header.

    Usage:
        @router.get("/protected")
        async def protected(_auth: dict = Depends(require_auth)):
            # _auth contains the decoded token payload
            return {"user": _auth["sub"]}

    Args:
        credentials: The HTTP Bearer credentials extracted by FastAPI.

    Returns:
        The decoded token payload (dict with "sub", "iat", "exp").

    Raises:
        HTTPException: If no token provided, token is invalid, or expired.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    jwt_secret = get_jwt_secret()
    return verify_token(credentials.credentials, jwt_secret)
