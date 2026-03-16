"""
Tests for Authentication Endpoints — POST /auth/register, POST /auth/login.

Covers:
  - Registration with valid data
  - Registration with duplicate email returns 400
  - Login with valid credentials returns token
  - Login with wrong password returns 401
  - Login with non-existent user returns 401
  - Password is hashed (not stored plain)
  - Token format
"""
import uuid
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.database import models
from src.database.session import get_db
from src.auth import security


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def client_with_mock_db(mock_db):
    """TestClient with DB overridden (no auth override — tests auth flow)."""
    def override_get_db():
        yield mock_db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

class TestRegisterEndpoint:

    def test_register_new_user_success(self, client_with_mock_db, mock_db):
        """Registering a new user should return the user object."""
        from datetime import datetime
        # No existing user
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        def _fake_refresh(obj):
            if isinstance(obj, models.User):
                obj.id = uuid.uuid4()
                obj.created_at = datetime(2025, 1, 1)
                obj.updated_at = datetime(2025, 1, 1)
                obj.is_active = True
                obj.is_premium = False
                obj.onboarding_complete = False
                obj.auth_provider = "email"
                obj.profile_photo_url = None
                obj.preferences = None

        mock_db.refresh = MagicMock(side_effect=_fake_refresh)

        response = client_with_mock_db.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "full_name": "New User",
            },
        )

        # The endpoint creates a user and calls db.add, db.commit, db.refresh
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"

    def test_register_duplicate_email_returns_400(self, client_with_mock_db, mock_db):
        """Registering with an existing email should return 400."""
        existing_user = models.User(
            id=uuid.uuid4(),
            email="existing@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user

        response = client_with_mock_db.post(
            "/auth/register",
            json={
                "email": "existing@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_missing_email_returns_422(self, client_with_mock_db):
        """Missing email field should return 422."""
        response = client_with_mock_db.post(
            "/auth/register",
            json={"password": "SecurePass123!"},
        )
        assert response.status_code == 422

    def test_register_short_password_returns_422(self, client_with_mock_db):
        """Password shorter than 8 chars should be rejected."""
        response = client_with_mock_db.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "short"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

class TestLoginEndpoint:

    def test_login_wrong_password_returns_401(self, client_with_mock_db, mock_db):
        """Login with wrong password should return 401."""
        hashed = security.get_password_hash("CorrectPassword1!")
        user = models.User(
            id=uuid.uuid4(),
            email="login@example.com",
            hashed_password=hashed,
            is_active=True,
        )
        mock_db.query.return_value.filter.return_value.first.return_value = user

        response = client_with_mock_db.post(
            "/auth/login",
            data={"username": "login@example.com", "password": "WrongPassword!"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user_returns_401(self, client_with_mock_db, mock_db):
        """Login with non-existent email should return 401."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client_with_mock_db.post(
            "/auth/login",
            data={"username": "nobody@example.com", "password": "SomePassword1!"},
        )
        assert response.status_code == 401

    def test_login_success_returns_token(self, client_with_mock_db, mock_db):
        """Login with valid credentials should return an access token."""
        password = "CorrectPassword1!"
        hashed = security.get_password_hash(password)
        user = models.User(
            id=uuid.uuid4(),
            email="loginok@example.com",
            hashed_password=hashed,
            is_active=True,
        )
        mock_db.query.return_value.filter.return_value.first.return_value = user

        response = client_with_mock_db.post(
            "/auth/login",
            data={"username": "loginok@example.com", "password": password},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 20

    def test_login_missing_fields_returns_422(self, client_with_mock_db):
        """Login without username/password should return 422."""
        response = client_with_mock_db.post("/auth/login", data={})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Security utility unit tests
# ---------------------------------------------------------------------------

class TestSecurityUtils:

    def test_password_hash_not_equal_to_plain(self):
        plain = "myPassword123"
        hashed = security.get_password_hash(plain)
        assert hashed != plain
        assert len(hashed) > 20

    def test_verify_password_correct(self):
        plain = "myPassword123"
        hashed = security.get_password_hash(plain)
        assert security.verify_password(plain, hashed) is True

    def test_verify_password_wrong(self):
        hashed = security.get_password_hash("myPassword123")
        assert security.verify_password("wrongPassword", hashed) is False

    def test_create_access_token_returns_string(self):
        token = security.create_access_token(data={"sub": "test@example.com"})
        assert isinstance(token, str)
        assert len(token) > 20

    def test_create_access_token_with_expiry(self):
        from datetime import timedelta
        token = security.create_access_token(
            data={"sub": "test@example.com"},
            expires_delta=timedelta(minutes=60),
        )
        assert isinstance(token, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
