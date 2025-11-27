from datetime import date, timedelta
import uuid

from src.database import models
from src.schemas.meal_plan import MealPlanPreferencesOverride
from src.services import meal_plan_service
from src.services.meal_plan_service import (
    NutritionEstimate,
    RecipeRecord,
    _hydrate_summary_response,
)


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


def test_slot_for_item_uses_meal_ratios():
    prefs = models.UserPreferences(calorie_target=2000, people_count=1)
    profile = meal_plan_service._build_preference_profile(prefs, None)
    plan_item = models.MealPlanItem(
        plan_id=uuid.uuid4(),
        day_of_week=0,
        meal_type="breakfast",
        recipe_id="test",
        recipe_title="Test",
    )

    slot = meal_plan_service._slot_for_item(profile, plan_item)

    assert slot.meal_type == "breakfast"
    assert slot.day_index == 0
    # Default breakfast split is 25% of calories (clamped to >=250)
    assert slot.calorie_target == max(250, int((profile.calorie_target or 2000) * 0.25))


def test_recalculate_plan_totals_sums_items():
    plan = models.MealPlan(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        week_start_date=date.today(),
        week_end_date=date.today(),
    )

    item_a = models.MealPlanItem(
        plan_id=uuid.uuid4(),
        day_of_week=0,
        meal_type="breakfast",
        recipe_id="a",
        recipe_title="A",
        servings=1,
        calories=400,
        protein=20,
        carbs=30,
        fat=10,
        estimated_cost=5.0,
    )
    item_b = models.MealPlanItem(
        plan_id=uuid.uuid4(),
        day_of_week=0,
        meal_type="lunch",
        recipe_id="b",
        recipe_title="B",
        servings=1,
        calories=600,
        protein=30,
        carbs=60,
        fat=20,
        estimated_cost=7.5,
    )

    plan.items = [item_a, item_b]
    meal_plan_service._recalculate_plan_totals(plan)

    assert plan.total_calories == 1000
    assert plan.total_protein == 50
    assert plan.total_carbs == 90
    assert plan.total_fat == 30
    assert plan.total_estimated_cost == 12.5


def test_validation_detects_calorie_and_budget_miss():
    plan = models.MealPlan(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        week_start_date=date.today(),
        week_end_date=date.today(),
        total_calories=5000,
        total_estimated_cost=150.0,
        items=[],
    )
    prefs = models.UserPreferences(
        calorie_target=2000,
        budget_per_week=100.0,
        people_count=1,
    )
    profile = meal_plan_service._build_preference_profile(prefs, None)
    issues = meal_plan_service._run_validation_checks(plan, profile)

    codes = {issue["code"] for issue in issues}
    assert "calorie_target_miss" in codes
    assert "budget_exceeded" in codes


def test_validation_detects_allergy_and_prep_time():
    recipe_id = "unit-test-recipe"
    lookup = meal_plan_service._recipe_id_lookup()
    lookup[recipe_id] = RecipeRecord(
        recipe_id=recipe_id,
        title="Peanut Stew",
        normalized_title="peanut stew",
        ingredients=("peanut", "broth"),
        ingredient_set=frozenset({"peanut", "broth"}),
        cuisine_tags=frozenset(),
        nutrition=NutritionEstimate(calories=600, protein=20, carbs=50, fat=25),
        estimated_cost=8.0,
        prep_time_minutes=60,
    )

    plan = models.MealPlan(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        week_start_date=date.today(),
        week_end_date=date.today(),
        total_calories=8400,
        total_estimated_cost=56.0,
    )
    plan.items = [
        models.MealPlanItem(
            plan_id=plan.id,
            day_of_week=0,
            meal_type="dinner",
            recipe_id=recipe_id,
            recipe_title="Peanut Stew",
            servings=1,
            calories=600,
            protein=20,
            carbs=50,
            fat=25,
            estimated_cost=8.0,
            prep_time_minutes=60,
        )
    ]

    prefs = models.UserPreferences(
        allergies=["peanut"],
        cooking_time_max=30,
        people_count=1,
        calorie_target=1200,
    )
    profile = meal_plan_service._build_preference_profile(prefs, None)
    issues = meal_plan_service._run_validation_checks(plan, profile)
    codes = {issue["code"] for issue in issues}

    assert "allergy_violation" in codes
    assert "prep_time_exceeded" in codes

    lookup.pop(recipe_id, None)


def test_build_summary_payload():
    start = date(2024, 1, 1)
    plan = models.MealPlan(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        week_start_date=start,
        week_end_date=start + timedelta(days=6),
        total_estimated_cost=42.0,
    )
    item_a = models.MealPlanItem(
        plan_id=plan.id,
        day_of_week=0,
        meal_type="breakfast",
        recipe_id="a",
        recipe_title="Oats",
        servings=1,
        calories=500,
        protein=20,
        carbs=50,
        fat=10,
        estimated_cost=5.0,
        prep_time_minutes=30,
    )
    item_b = models.MealPlanItem(
        plan_id=plan.id,
        day_of_week=0,
        meal_type="dinner",
        recipe_id="b",
        recipe_title="Soup",
        servings=1,
        calories=600,
        protein=25,
        carbs=40,
        fat=15,
        estimated_cost=7.0,
        prep_time_minutes=20,
    )
    item_c = models.MealPlanItem(
        plan_id=plan.id,
        day_of_week=1,
        meal_type="lunch",
        recipe_id="c",
        recipe_title="Salad",
        servings=1,
        calories=400,
        protein=15,
        carbs=30,
        fat=12,
        estimated_cost=6.0,
        prep_time_minutes=10,
    )
    plan.items = [item_a, item_b, item_c]

    summary = meal_plan_service._build_summary_payload(plan)

    assert summary["total"]["calories"] == 1500
    assert summary["total"]["protein"] == 60
    assert len(summary["daily"]) == 7
    assert summary["daily"][0]["total"]["calories"] == 1100
    assert summary["daily"][1]["total"]["calories"] == 400
    assert summary["daily"][0]["date"] == start
    assert summary["average_prep_time_minutes"] == 20.0


def test_hydrate_summary_response_injects_meals():
    start = date(2024, 1, 1)
    plan = models.MealPlan(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        week_start_date=start,
        week_end_date=start + timedelta(days=6),
    )
    meal = models.MealPlanItem(
        plan_id=plan.id,
        day_of_week=0,
        meal_type="lunch",
        recipe_id="demo",
        recipe_title="Demo Meal",
        servings=1,
        calories=300,
        protein=10,
        carbs=35,
        fat=12,
        estimated_cost=4.0,
        prep_time_minutes=15,
    )
    plan.items = [meal]

    snapshot = meal_plan_service._build_summary_payload(
        plan,
        include_meals=False,
        serialize_dates=True,
        include_plan_id=False,
    )
    hydrated = _hydrate_summary_response(plan, snapshot)

    assert hydrated["plan_id"] == plan.id
    assert isinstance(hydrated["week_start_date"], date)
    assert hydrated["daily"][0]["meals"][0].recipe_title == "Demo Meal"
