"""
Tests for Meal Plan CRUD endpoints added by Agent 2.

Covers:
  - GET  /meal-plans/weekly?week_start={date}
  - DELETE /meal-plans/{plan_id}/items/{item_id}
  - PUT    /meal-plans/{plan_id}/items  (bulk update)

Uses mock DB and patched auth to isolate endpoint logic.
"""
import uuid
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.database import models


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_user() -> models.User:
    user = models.User(
        id=uuid.uuid4(),
        email="test_crud@example.com",
        hashed_password="hashed",
        is_active=True,
    )
    return user


def _fake_meal_plan(user_id, week_start=None) -> models.MealPlan:
    ws = week_start or date.today()
    plan = models.MealPlan(
        id=uuid.uuid4(),
        user_id=user_id,
        week_start_date=ws,
        week_end_date=ws + timedelta(days=6),
        status="active",
        total_calories=7000,
        total_protein=350,
        total_carbs=700,
        total_fat=280,
        total_estimated_cost=70.0,
    )
    plan.items = []
    return plan


def _fake_item(plan_id) -> models.MealPlanItem:
    return models.MealPlanItem(
        id=uuid.uuid4(),
        plan_id=plan_id,
        day_of_week=0,
        meal_type="breakfast",
        recipe_id="recipe-abc",
        recipe_title="Oatmeal Bowl",
        servings=1,
        calories=400,
        protein=15,
        carbs=60,
        fat=10,
        estimated_cost=4.5,
        prep_time_minutes=10,
    )


@pytest.fixture
def fake_user():
    return _fake_user()


@pytest.fixture
def authed_client(db, fake_user):
    """TestClient with auth overridden to return our fake user."""
    from src.auth.security import get_current_active_user
    from src.database.session import get_db

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = lambda: fake_user

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /meal-plans/weekly
# ---------------------------------------------------------------------------

class TestGetWeeklyMealPlan:
    """Tests for GET /meal-plans/weekly?week_start={date}."""

    def test_returns_plan_for_valid_week_start(self, authed_client, fake_user):
        ws = date.today()
        plan = _fake_meal_plan(fake_user.id, ws)

        with patch("src.api.routers.meal_plans.meal_plan_service.get_meal_plan_by_week", return_value=plan):
            response = authed_client.get(f"/meal-plans/weekly?week_start={ws.isoformat()}")

        assert response.status_code == 200
        data = response.json()
        assert data["week_start_date"] == ws.isoformat()

    def test_returns_404_when_no_plan(self, authed_client):
        ws = date(2025, 1, 1)

        with patch("src.api.routers.meal_plans.meal_plan_service.get_meal_plan_by_week", return_value=None):
            response = authed_client.get(f"/meal-plans/weekly?week_start={ws.isoformat()}")

        assert response.status_code == 404

    def test_missing_week_start_param_returns_422(self, authed_client):
        response = authed_client.get("/meal-plans/weekly")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /meal-plans/{plan_id}/items/{item_id}
# ---------------------------------------------------------------------------

class TestDeleteMealPlanItem:
    """Tests for DELETE /meal-plans/{plan_id}/items/{item_id}."""

    def test_successful_delete_returns_204(self, authed_client, fake_user):
        plan = _fake_meal_plan(fake_user.id)
        item = _fake_item(plan.id)
        plan.items.append(item)

        with patch(
            "src.api.routers.meal_plans.meal_plan_service.delete_meal_plan_item",
            return_value=None,
        ):
            response = authed_client.delete(
                f"/meal-plans/{plan.id}/items/{item.id}"
            )

        assert response.status_code == 204

    def test_delete_nonexistent_item_returns_error(self, authed_client, fake_user):
        plan = _fake_meal_plan(fake_user.id)

        with patch(
            "src.api.routers.meal_plans.meal_plan_service.delete_meal_plan_item",
            side_effect=ValueError("Item not found in meal plan"),
        ):
            response = authed_client.delete(
                f"/meal-plans/{plan.id}/items/{uuid.uuid4()}"
            )

        assert response.status_code == 400

    def test_delete_unauthorized_returns_error(self, authed_client, fake_user):
        plan = _fake_meal_plan(uuid.uuid4())  # different user

        with patch(
            "src.api.routers.meal_plans.meal_plan_service.delete_meal_plan_item",
            side_effect=ValueError("Not authorized to modify this plan"),
        ):
            response = authed_client.delete(
                f"/meal-plans/{plan.id}/items/{uuid.uuid4()}"
            )

        assert response.status_code == 400


# ---------------------------------------------------------------------------
# PUT /meal-plans/{plan_id}/items  (bulk update)
# ---------------------------------------------------------------------------

class TestBulkUpdateMealPlanItems:
    """Tests for PUT /meal-plans/{plan_id}/items."""

    def test_bulk_update_with_valid_items(self, authed_client, fake_user):
        plan = _fake_meal_plan(fake_user.id)

        updated_plan = _fake_meal_plan(fake_user.id)
        updated_plan.id = plan.id
        item1 = _fake_item(plan.id)
        item1.meal_type = "lunch"
        updated_plan.items = [item1]

        payload = {
            "items": [
                {
                    "day_of_week": 0,
                    "meal_type": "lunch",
                    "recipe_id": "recipe-xyz",
                    "recipe_title": "Grilled Chicken Salad",
                    "servings": 2,
                    "calories": 550,
                    "protein": 40,
                    "carbs": 30,
                    "fat": 20,
                    "estimated_cost": 8.5,
                    "prep_time_minutes": 25,
                }
            ]
        }

        with patch(
            "src.api.routers.meal_plans.meal_plan_service.update_meal_plan_items",
            return_value=updated_plan,
        ):
            response = authed_client.put(
                f"/meal-plans/{plan.id}/items",
                json=payload,
            )

        assert response.status_code == 200

    def test_bulk_update_with_empty_items_list(self, authed_client, fake_user):
        plan = _fake_meal_plan(fake_user.id)
        empty_plan = _fake_meal_plan(fake_user.id)
        empty_plan.id = plan.id
        empty_plan.items = []

        with patch(
            "src.api.routers.meal_plans.meal_plan_service.update_meal_plan_items",
            return_value=empty_plan,
        ):
            response = authed_client.put(
                f"/meal-plans/{plan.id}/items",
                json={"items": []},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    def test_bulk_update_nonexistent_plan_returns_error(self, authed_client):
        with patch(
            "src.api.routers.meal_plans.meal_plan_service.update_meal_plan_items",
            side_effect=ValueError("Meal plan not found"),
        ):
            response = authed_client.put(
                f"/meal-plans/{uuid.uuid4()}/items",
                json={"items": []},
            )

        assert response.status_code == 400

    def test_bulk_update_unauthorized_returns_error(self, authed_client):
        with patch(
            "src.api.routers.meal_plans.meal_plan_service.update_meal_plan_items",
            side_effect=ValueError("Not authorized to modify this plan"),
        ):
            response = authed_client.put(
                f"/meal-plans/{uuid.uuid4()}/items",
                json={"items": []},
            )

        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Service-layer unit tests
# ---------------------------------------------------------------------------

class TestMealPlanServiceCRUD:
    """Unit tests for the service-layer CRUD functions."""

    def test_get_meal_plan_by_week_queries_correct_filters(self):
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None

        from src.services.meal_plan_service import get_meal_plan_by_week

        result = get_meal_plan_by_week(mock_db, "user-123", date(2026, 3, 9))
        assert result is None
        mock_db.query.assert_called_once()

    def test_delete_meal_plan_item_raises_on_wrong_user(self):
        from src.services.meal_plan_service import delete_meal_plan_item

        plan = _fake_meal_plan(uuid.uuid4())  # owned by a different user
        item = _fake_item(plan.id)
        plan.items = [item]

        mock_db = MagicMock()

        with patch("src.services.meal_plan_service.get_meal_plan", return_value=plan):
            with pytest.raises(ValueError, match="Not authorized"):
                delete_meal_plan_item(mock_db, str(uuid.uuid4()), str(plan.id), str(item.id))

    def test_delete_meal_plan_item_raises_on_missing_item(self):
        from src.services.meal_plan_service import delete_meal_plan_item

        user_id = uuid.uuid4()
        plan = _fake_meal_plan(user_id)
        plan.items = []

        mock_db = MagicMock()

        with patch("src.services.meal_plan_service.get_meal_plan", return_value=plan):
            with pytest.raises(ValueError, match="Item not found"):
                delete_meal_plan_item(mock_db, str(user_id), str(plan.id), str(uuid.uuid4()))

    def test_update_meal_plan_items_raises_on_wrong_user(self):
        from src.services.meal_plan_service import update_meal_plan_items

        plan = _fake_meal_plan(uuid.uuid4())
        plan.items = []

        mock_db = MagicMock()

        with patch("src.services.meal_plan_service.get_meal_plan", return_value=plan):
            with pytest.raises(ValueError, match="Not authorized"):
                update_meal_plan_items(mock_db, str(uuid.uuid4()), str(plan.id), [])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
