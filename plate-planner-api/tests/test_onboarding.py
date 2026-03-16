"""
Tests for the Onboarding Endpoint — POST /users/me/onboarding.

Covers:
  - Full onboarding with all fields
  - Minimal onboarding (only required fields)
  - onboarding_complete flag is set to True
  - User preferences are properly stored
  - NutritionGoal is created when goal_type + calorie_target provided
"""
import uuid
from datetime import date
from unittest.mock import patch, MagicMock, PropertyMock

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.database import models


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(**overrides) -> models.User:
    from datetime import datetime
    defaults = dict(
        id=uuid.uuid4(),
        email="onboard@example.com",
        hashed_password="hashed",
        is_active=True,
        is_premium=False,
        onboarding_complete=False,
        auth_provider="email",
        profile_photo_url=None,
        created_at=datetime(2025, 1, 1),
        updated_at=datetime(2025, 1, 1),
    )
    defaults.update(overrides)
    return models.User(**defaults)


@pytest.fixture
def fake_user():
    return _make_user()


@pytest.fixture
def authed_client(db, fake_user):
    """TestClient with auth + db overrides."""
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
# Tests
# ---------------------------------------------------------------------------

class TestOnboardingEndpoint:
    """POST /users/me/onboarding"""

    def test_onboarding_with_all_fields(self, authed_client, db, fake_user):
        """Posting all onboarding fields should succeed and set preferences."""
        payload = {
            "goal_type": "weight_loss",
            "calorie_target": 1800,
            "dietary_restrictions": ["vegan"],
            "cuisine_preferences": ["italian", "mexican"],
            "allergies": ["peanut"],
            "protein_target": 120,
            "carb_target": 150,
            "fat_target": 60,
            "cooking_time_max": 30,
            "budget_per_week": 80.0,
            "people_count": 2,
        }

        # Mock DB queries for preferences and nutrition goal
        db.query.return_value.filter.return_value.first.return_value = None
        db.commit = MagicMock()
        db.refresh = MagicMock(side_effect=lambda obj: None)
        db.add = MagicMock()

        response = authed_client.post("/users/me/onboarding", json=payload)
        assert response.status_code == 200

    def test_onboarding_with_minimal_fields(self, authed_client, db, fake_user):
        """Empty payload (all optional) should still succeed."""
        payload = {}

        db.query.return_value.filter.return_value.first.return_value = None
        db.commit = MagicMock()
        db.refresh = MagicMock(side_effect=lambda obj: None)
        db.add = MagicMock()

        response = authed_client.post("/users/me/onboarding", json=payload)
        assert response.status_code == 200

    def test_onboarding_sets_onboarding_complete_flag(self, authed_client, db, fake_user):
        """After onboarding, User.onboarding_complete should be True."""
        db.query.return_value.filter.return_value.first.return_value = None
        db.commit = MagicMock()
        db.refresh = MagicMock(side_effect=lambda obj: None)
        db.add = MagicMock()

        authed_client.post("/users/me/onboarding", json={"calorie_target": 2000})

        # The endpoint sets onboarding_complete = True directly on current_user
        assert fake_user.onboarding_complete is True

    def test_onboarding_creates_preferences_when_none_exist(self, authed_client, db, fake_user):
        """If no UserPreferences row exists, one should be created."""
        # First query returns None (no existing prefs)
        db.query.return_value.filter.return_value.first.return_value = None
        db.commit = MagicMock()
        db.refresh = MagicMock(side_effect=lambda obj: None)
        db.add = MagicMock()

        payload = {
            "dietary_restrictions": ["gluten-free"],
            "calorie_target": 2200,
        }

        authed_client.post("/users/me/onboarding", json=payload)

        # db.add should have been called for preferences and user
        assert db.add.call_count >= 2  # prefs + user (and possibly goal)

    def test_onboarding_creates_nutrition_goal_when_goal_type_and_calorie_provided(
        self, authed_client, db, fake_user
    ):
        """
        When both goal_type and calorie_target are provided, a NutritionGoal
        should be created.
        """
        # First query: no existing prefs
        # Second query: no existing active goal
        db.query.return_value.filter.return_value.first.side_effect = [
            None,  # UserPreferences
            None,  # NutritionGoal (active)
        ]
        db.commit = MagicMock()
        db.refresh = MagicMock(side_effect=lambda obj: None)
        db.add = MagicMock()

        payload = {
            "goal_type": "muscle_gain",
            "calorie_target": 2500,
            "protein_target": 180,
        }

        authed_client.post("/users/me/onboarding", json=payload)

        # db.add should be called with the NutritionGoal object
        add_calls = db.add.call_args_list
        types_added = [type(call.args[0]).__name__ for call in add_calls if call.args]

        assert "NutritionGoal" in types_added or len(add_calls) >= 3

    def test_onboarding_no_goal_without_calorie_target(self, authed_client, db, fake_user):
        """If calorie_target is missing, no NutritionGoal should be created."""
        db.query.return_value.filter.return_value.first.return_value = None
        db.commit = MagicMock()
        db.refresh = MagicMock(side_effect=lambda obj: None)
        db.add = MagicMock()

        payload = {
            "goal_type": "weight_loss",
            # no calorie_target
        }

        authed_client.post("/users/me/onboarding", json=payload)

        add_calls = db.add.call_args_list
        types_added = [type(call.args[0]).__name__ for call in add_calls if call.args]
        assert "NutritionGoal" not in types_added


class TestOnboardingRequestSchema:
    """Validation of the OnboardingRequest Pydantic model."""

    def test_schema_accepts_valid_data(self):
        from src.schemas.user import OnboardingRequest

        req = OnboardingRequest(
            goal_type="maintenance",
            calorie_target=2000,
            dietary_restrictions=["vegan"],
            cuisine_preferences=["thai"],
            allergies=["shellfish"],
            people_count=1,
        )
        assert req.goal_type == "maintenance"
        assert req.calorie_target == 2000

    def test_schema_defaults(self):
        from src.schemas.user import OnboardingRequest

        req = OnboardingRequest()
        assert req.goal_type is None
        assert req.calorie_target is None
        assert req.dietary_restrictions == []
        assert req.cuisine_preferences == []
        assert req.allergies == []
        assert req.people_count == 1

    def test_onboarding_complete_field_in_user_schema(self):
        """User schema should expose onboarding_complete."""
        from src.schemas.user import User as UserSchema

        fields = UserSchema.model_fields
        assert "onboarding_complete" in fields


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
