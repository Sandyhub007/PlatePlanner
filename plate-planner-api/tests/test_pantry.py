"""
Tests for Pantry CRUD Endpoints.

Covers:
  - GET  /pantry (list pantry items)
  - POST /pantry/items (add items)
  - DELETE /pantry/items/{item_name} (remove item)
  - PUT  /pantry (replace entire pantry)
  - Unauthorized access returns 401
"""
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock, PropertyMock

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.database import models
from src.auth.security import get_current_active_user
from src.database.session import get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_user() -> models.User:
    return models.User(
        id=uuid.uuid4(),
        email="pantry_test@example.com",
        hashed_password="hashed",
        is_active=True,
        is_premium=False,
        onboarding_complete=True,
        auth_provider="email",
        profile_photo_url=None,
    )


@pytest.fixture
def fake_user():
    return _make_user()


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def authed_client(mock_db, fake_user):
    """TestClient with auth + DB overrides."""
    def override_get_db():
        yield mock_db
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = lambda: fake_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def unauthed_client():
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /pantry — unauthorized
# ---------------------------------------------------------------------------

class TestPantryUnauthorized:

    def test_get_pantry_unauthorized(self, unauthed_client):
        """GET /pantry without token should return 401."""
        response = unauthed_client.get("/pantry")
        assert response.status_code == 401

    def test_add_items_unauthorized(self, unauthed_client):
        """POST /pantry/items without token should return 401."""
        response = unauthed_client.post("/pantry/items", json={"items": ["garlic"]})
        assert response.status_code == 401

    def test_delete_item_unauthorized(self, unauthed_client):
        """DELETE /pantry/items/garlic without token should return 401."""
        response = unauthed_client.delete("/pantry/items/garlic")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /pantry — with auth
# ---------------------------------------------------------------------------

class TestGetPantry:

    def test_get_pantry_returns_items(self, authed_client, mock_db, fake_user):
        """GET /pantry should return the user's pantry items."""
        now = datetime.utcnow()
        mock_item = MagicMock()
        mock_item.item_name = "garlic"
        mock_item.created_at = now

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_item]

        response = authed_client.get("/pantry")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "garlic"

    def test_get_pantry_empty(self, authed_client, mock_db):
        """GET /pantry with no items should return an empty list."""
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        response = authed_client.get("/pantry")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []


# ---------------------------------------------------------------------------
# POST /pantry/items — add items
# ---------------------------------------------------------------------------

class TestAddPantryItems:

    def test_add_items_validation(self, authed_client):
        """POST /pantry/items with missing items field should return 422."""
        response = authed_client.post("/pantry/items", json={})
        assert response.status_code == 422

    def test_add_empty_items_list(self, authed_client, mock_db):
        """POST /pantry/items with empty list should succeed."""
        mock_db.commit = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        response = authed_client.post("/pantry/items", json={"items": []})
        assert response.status_code == 201


# ---------------------------------------------------------------------------
# DELETE /pantry/items/{item_name}
# ---------------------------------------------------------------------------

class TestDeletePantryItem:

    def test_delete_nonexistent_item_returns_404(self, authed_client, mock_db):
        """DELETE /pantry/items/nonexistent should return 404."""
        mock_db.query.return_value.filter.return_value.delete.return_value = 0
        mock_db.commit = MagicMock()

        response = authed_client.delete("/pantry/items/nonexistent_item")
        assert response.status_code == 404

    def test_delete_existing_item_returns_204(self, authed_client, mock_db):
        """DELETE /pantry/items/garlic should return 204."""
        mock_db.query.return_value.filter.return_value.delete.return_value = 1
        mock_db.commit = MagicMock()

        response = authed_client.delete("/pantry/items/garlic")
        assert response.status_code == 204


# ---------------------------------------------------------------------------
# PUT /pantry — replace entire pantry
# ---------------------------------------------------------------------------

class TestReplacePantry:

    def test_replace_pantry_validation(self, authed_client):
        """PUT /pantry with missing items field should return 422."""
        response = authed_client.put("/pantry", json={})
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
