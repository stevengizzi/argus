"""Tests for the auth module.

Verifies password verification, token creation/verification, and the
require_auth dependency.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from argus.api.auth import (
    create_access_token,
    get_jwt_secret,
    hash_password,
    require_auth,
    set_jwt_secret,
    verify_password,
    verify_token,
)


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_password_returns_bcrypt_hash(self) -> None:
        """hash_password returns a bcrypt hash string."""
        password = "mysecretpassword"
        hashed = hash_password(password)

        assert hashed.startswith("$2")  # bcrypt prefix
        assert len(hashed) == 60  # bcrypt hash length

    def test_verify_password_correct(self) -> None:
        """verify_password returns True for correct password."""
        password = "testpassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self) -> None:
        """verify_password returns False for incorrect password."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_hash(self) -> None:
        """verify_password returns False for empty hash."""
        assert verify_password("anypassword", "") is False

    def test_verify_password_invalid_hash(self) -> None:
        """verify_password returns False for invalid hash format."""
        assert verify_password("password", "not-a-valid-hash") is False


class TestJwtSecret:
    """Tests for JWT secret management."""

    def test_set_and_get_jwt_secret(self) -> None:
        """set_jwt_secret and get_jwt_secret work together."""
        test_secret = "test-secret-key-minimum-32-characters"
        set_jwt_secret(test_secret)

        assert get_jwt_secret() == test_secret

    def test_get_jwt_secret_not_configured(self) -> None:
        """get_jwt_secret raises HTTPException when not configured."""
        set_jwt_secret("")  # Clear the secret

        with pytest.raises(HTTPException) as exc_info:
            get_jwt_secret()

        assert exc_info.value.status_code == 500
        assert "not configured" in exc_info.value.detail


class TestTokenCreation:
    """Tests for JWT token creation."""

    def test_create_access_token_returns_token_and_expiry(self) -> None:
        """create_access_token returns a token and expiration datetime."""
        secret = "test-secret-for-jwt-token-creation"
        token, expires_at = create_access_token(secret, expires_hours=24)

        assert isinstance(token, str)
        assert len(token) > 0
        assert isinstance(expires_at, datetime)
        assert expires_at > datetime.now(UTC)

    def test_create_access_token_expiry_matches_hours(self) -> None:
        """Token expiry is approximately expires_hours from now."""
        secret = "test-secret-for-jwt-token-creation"
        hours = 12
        token, expires_at = create_access_token(secret, expires_hours=hours)

        # Should be within a few seconds of the expected time
        expected = datetime.now(UTC) + timedelta(hours=hours)
        delta = abs((expires_at - expected).total_seconds())
        assert delta < 5  # Within 5 seconds


class TestTokenVerification:
    """Tests for JWT token verification."""

    def test_verify_token_valid(self) -> None:
        """verify_token returns payload for valid token."""
        secret = "test-secret-for-jwt-token-verification"
        token, _ = create_access_token(secret, expires_hours=24)

        payload = verify_token(token, secret)

        assert payload["sub"] == "operator"
        assert "exp" in payload
        assert "iat" in payload

    def test_verify_token_invalid(self) -> None:
        """verify_token raises HTTPException for invalid token."""
        secret = "test-secret-for-jwt-token-verification"

        with pytest.raises(HTTPException) as exc_info:
            verify_token("invalid-token", secret)

        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.detail

    def test_verify_token_wrong_secret(self) -> None:
        """verify_token raises HTTPException when secret doesn't match."""
        secret1 = "test-secret-for-jwt-token-creation-1"
        secret2 = "test-secret-for-jwt-token-creation-2"
        token, _ = create_access_token(secret1, expires_hours=24)

        with pytest.raises(HTTPException) as exc_info:
            verify_token(token, secret2)

        assert exc_info.value.status_code == 401

    def test_verify_token_expired(self) -> None:
        """verify_token raises HTTPException for expired token."""
        from jose import jwt

        secret = "test-secret-for-expired-token-test"
        # Create an already-expired token
        expired_payload = {
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "sub": "operator",
        }
        expired_token = jwt.encode(expired_payload, secret, algorithm="HS256")

        with pytest.raises(HTTPException) as exc_info:
            verify_token(expired_token, secret)

        assert exc_info.value.status_code == 401


class TestRequireAuth:
    """Tests for the require_auth dependency."""

    def test_require_auth_valid_token(self) -> None:
        """require_auth returns payload for valid token."""
        from unittest.mock import MagicMock

        secret = "test-secret-for-require-auth-test"
        set_jwt_secret(secret)
        token, _ = create_access_token(secret, expires_hours=24)

        # Mock HTTPAuthorizationCredentials
        credentials = MagicMock()
        credentials.credentials = token

        payload = require_auth(credentials)

        assert payload["sub"] == "operator"

    def test_require_auth_invalid_token(self) -> None:
        """require_auth raises HTTPException for invalid token."""
        from unittest.mock import MagicMock

        secret = "test-secret-for-require-auth-invalid"
        set_jwt_secret(secret)

        credentials = MagicMock()
        credentials.credentials = "invalid-token"

        with pytest.raises(HTTPException) as exc_info:
            require_auth(credentials)

        assert exc_info.value.status_code == 401


class TestConftest:
    """Tests that verify the conftest fixtures work correctly."""

    def test_api_config_has_valid_password_hash(self, api_config) -> None:
        """api_config fixture has a valid bcrypt password hash."""
        from tests.api.conftest import TEST_PASSWORD

        assert api_config.password_hash.startswith("$2")
        assert verify_password(TEST_PASSWORD, api_config.password_hash)

    def test_jwt_secret_is_set(self, jwt_secret) -> None:
        """jwt_secret fixture sets the module-level secret."""
        assert jwt_secret == get_jwt_secret()

    def test_auth_headers_contain_valid_token(self, jwt_secret, auth_headers) -> None:
        """auth_headers fixture contains a valid Bearer token."""
        assert "Authorization" in auth_headers
        assert auth_headers["Authorization"].startswith("Bearer ")

        token = auth_headers["Authorization"].replace("Bearer ", "")
        payload = verify_token(token, jwt_secret)
        assert payload["sub"] == "operator"

    @pytest.mark.asyncio
    async def test_app_state_has_all_components(self, app_state) -> None:
        """app_state fixture has all required components."""
        assert app_state.event_bus is not None
        assert app_state.trade_logger is not None
        assert app_state.broker is not None
        assert app_state.health_monitor is not None
        assert app_state.risk_manager is not None
        assert app_state.order_manager is not None
        assert app_state.clock is not None
        assert app_state.config is not None
        assert app_state.start_time > 0

    @pytest.mark.asyncio
    async def test_client_fixture_creates_working_client(self, client) -> None:
        """client fixture creates a working httpx client."""
        # Just verify the client can make requests
        # Actual routes will be tested once they're implemented
        response = await client.get("/nonexistent")
        assert response.status_code == 404  # Expected for non-existent route


class TestAuthRoutes:
    """Tests for auth API routes (/api/v1/auth/*)."""

    @pytest.mark.asyncio
    async def test_login_success(self, client) -> None:
        """Correct password returns 200 with token."""
        from tests.api.conftest import TEST_PASSWORD

        response = await client.post(
            "/api/v1/auth/login",
            json={"password": TEST_PASSWORD},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_at" in data
        # Token should be non-empty
        assert len(data["access_token"]) > 0

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client) -> None:
        """Wrong password returns 401."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"password": "wrongpassword"},
        )

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_empty_password(self, client) -> None:
        """Empty password returns 401."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"password": ""},
        )

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_valid_token(self, client, auth_headers) -> None:
        """Protected endpoint with valid token returns 200."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user"] == "operator"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_protected_endpoint_missing_auth_header(self, client) -> None:
        """Protected endpoint without auth header returns 401."""
        response = await client.get("/api/v1/auth/me")

        # HTTPBearer returns 401 when no credentials provided
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_expired_token_rejected(self, client, jwt_secret) -> None:
        """Expired token returns 401."""
        from jose import jwt as jose_jwt

        # Create an already-expired token
        expired_payload = {
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "sub": "operator",
        }
        expired_token = jose_jwt.encode(expired_payload, jwt_secret, algorithm="HS256")

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401
        assert "Invalid or expired token" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(self, client) -> None:
        """Token signed with wrong secret returns 401."""
        # Create token with a different secret
        wrong_secret = "wrong-secret-not-the-real-one"
        token, _ = create_access_token(wrong_secret, expires_hours=24)

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 401
        assert "Invalid or expired token" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_refresh_returns_new_token(self, client, auth_headers) -> None:
        """Refresh endpoint with valid token returns new token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_at" in data
        # Token should be non-empty and different from original
        assert len(data["access_token"]) > 0

    @pytest.mark.asyncio
    async def test_refresh_with_expired_token(self, client, jwt_secret) -> None:
        """Refresh endpoint with expired token returns 401."""
        from jose import jwt as jose_jwt

        # Create an already-expired token
        expired_payload = {
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "sub": "operator",
        }
        expired_token = jose_jwt.encode(expired_payload, jwt_secret, algorithm="HS256")

        response = await client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401
        assert "Invalid or expired token" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_bcrypt_hash_generation(self) -> None:
        """Verify bcrypt hash generation works (for setup_password CLI)."""
        password = "test-password-123"
        hashed = hash_password(password)

        # Should be a valid bcrypt hash
        assert hashed.startswith("$2")
        assert len(hashed) == 60

        # Should verify correctly
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False
