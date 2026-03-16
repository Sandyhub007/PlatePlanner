"""
Tests for the core FastAPI application (src.api.app / src.main).

Covers:
  - Health check endpoint (GET /)
  - CORS headers
  - App metadata (title, version)
  - Router registration (key prefixes are mounted)
"""
import pytest
from fastapi.testclient import TestClient

from src.api.app import app


client = TestClient(app)


class TestHealthCheck:
    """GET / — basic health probe."""

    def test_root_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_json_with_message(self):
        response = client.get("/")
        data = response.json()
        assert "message" in data
        assert isinstance(data["message"], str)

    def test_root_message_non_empty(self):
        response = client.get("/")
        assert len(response.json()["message"]) > 0


class TestAppMetadata:
    """Verify FastAPI app metadata is correctly set."""

    def test_app_title(self):
        assert app.title == "Plate Planner Backend"

    def test_app_version(self):
        assert app.version is not None
        assert len(app.version) > 0


class TestCORSHeaders:
    """Verify CORS middleware is attached."""

    def test_cors_allows_origin(self):
        response = client.get("/", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        # CORS middleware should set Access-Control-Allow-Origin
        assert "access-control-allow-origin" in response.headers

    def test_cors_preflight(self):
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200


class TestRouterRegistration:
    """Verify key routers are mounted."""

    def _route_paths(self) -> set[str]:
        return {route.path for route in app.routes}

    def test_auth_router_registered(self):
        paths = self._route_paths()
        assert any("/auth" in p for p in paths), "Auth router not registered"

    def test_meal_plans_router_registered(self):
        paths = self._route_paths()
        assert any("/meal-plans" in p for p in paths), "Meal plans router not registered"

    def test_nutrition_router_registered(self):
        paths = self._route_paths()
        assert any("/nutrition" in p for p in paths), "Nutrition router not registered"

    def test_shopping_lists_router_registered(self):
        paths = self._route_paths()
        assert any("/shopping-lists" in p for p in paths), "Shopping lists router not registered"

    def test_users_router_registered(self):
        paths = self._route_paths()
        assert any("/users" in p for p in paths), "Users router not registered"

    def test_pantry_router_registered(self):
        paths = self._route_paths()
        assert any("/pantry" in p for p in paths), "Pantry router not registered"

    def test_suggest_recipes_endpoint_registered(self):
        paths = self._route_paths()
        assert "/suggest_recipes" in paths, "suggest_recipes endpoint not registered"

    def test_substitute_endpoint_registered(self):
        paths = self._route_paths()
        assert "/substitute" in paths, "substitute endpoint not registered"


class TestOpenAPISchema:
    """Verify the OpenAPI schema is correctly generated."""

    def test_openapi_schema_available(self):
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_openapi_schema_has_paths(self):
        response = client.get("/openapi.json")
        data = response.json()
        assert "paths" in data
        assert len(data["paths"]) > 0

    def test_openapi_schema_has_info(self):
        response = client.get("/openapi.json")
        data = response.json()
        assert "info" in data
        assert data["info"]["title"] == "Plate Planner Backend"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
