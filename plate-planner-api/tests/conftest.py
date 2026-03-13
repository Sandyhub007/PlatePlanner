"""
Shared pytest fixtures for all tests.
"""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.api.app import app
from src.database.session import get_db


@pytest.fixture()
def db():
    """
    Provide a MagicMock database session.

    Tests that need real DB operations (auth, meal plans) should set up their
    own PostgreSQL test database. For unit-level API tests, a mock is sufficient
    since the endpoints are tested via patching their service dependencies.
    """
    return MagicMock()


@pytest.fixture()
def client(db):
    """FastAPI TestClient with db dependency overridden."""
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
