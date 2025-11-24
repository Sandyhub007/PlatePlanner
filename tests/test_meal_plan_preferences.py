from src.database import models
from src.schemas.meal_plan import MealPlanPreferencesOverride
from src.services import meal_plan_service


def test_extract_ingredients_deduplicates_preserving_order():
    raw_value = "['Milk', 'Eggs', 'Milk', 'Flour', 'flour']"
    ingredients = meal_plan_service._extract_ingredients(raw_value)
    assert ingredients == ["milk", "eggs", "flour"]


def test_build_preference_profile_applies_overrides():
    prefs = models.UserPreferences(
        dietary_restrictions=["Vegan"],
        allergies=["Peanut"],
        cuisine_preferences=["thai"],
        calorie_target=1800,
        people_count=2,
    )
    override = MealPlanPreferencesOverride(
        cuisine_preferences=["mexican"],
        people_count=3,
        cooking_time_max=25,
    )

    profile = meal_plan_service._build_preference_profile(prefs, override)

    assert profile.cuisine_preferences == ["mexican"]
    assert profile.people_count == 3
    assert "vegan" in profile.dietary_restrictions
    assert profile.cooking_time_max == 25

