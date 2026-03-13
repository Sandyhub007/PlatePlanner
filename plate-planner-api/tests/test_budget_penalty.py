"""
Tests for Budget Penalty Logic in meal_plan_service._pick_recipe.

Verifies the three scenarios:
  1. Hard penalty:  meal cost > remaining_budget  (penalty = |remaining_after| * 10)
  2. Soft penalty:  meal cost > per_meal_budget   (penalty = (cost - budget) * 5)
  3. No penalty:    meal cost <= per_meal_budget
"""
import uuid
from collections import deque

import pytest

from src.services.meal_plan_service import (
    MealPlanEngine,
    MealSlot,
    PreferenceProfile,
    RecipeRecord,
    NutritionEstimate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_recipe(
    recipe_id: str = "r1",
    title: str = "Test",
    calories: int = 500,
    cost: float = 5.0,
    prep_time: int = 20,
) -> RecipeRecord:
    return RecipeRecord(
        recipe_id=recipe_id,
        title=title,
        normalized_title=title.lower(),
        ingredients=("chicken", "rice"),
        ingredient_set=frozenset({"chicken", "rice"}),
        cuisine_tags=frozenset(),
        nutrition=NutritionEstimate(calories=calories, protein=30, carbs=40, fat=15),
        estimated_cost=cost,
        prep_time_minutes=prep_time,
    )


def _make_slot(
    calorie_target: int = 500,
    per_meal_budget: float = 5.0,
    max_prep_time: int = 60,
) -> MealSlot:
    return MealSlot(
        day_index=0,
        meal_type="lunch",
        calorie_target=calorie_target,
        per_meal_budget=per_meal_budget,
        max_prep_time=max_prep_time,
    )


def _make_profile(
    budget_per_week: float = 105.0,
    people_count: int = 1,
) -> PreferenceProfile:
    return PreferenceProfile(
        dietary_restrictions=[],
        allergies=[],
        cuisine_preferences=[],
        calorie_target=2000,
        protein_target=None,
        carb_target=None,
        fat_target=None,
        cooking_time_max=60,
        budget_per_week=budget_per_week,
        people_count=people_count,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBudgetPenalty:
    """Unit tests for the budget penalty logic inside _pick_recipe."""

    def test_hard_penalty_when_exceeding_remaining_budget(self):
        """
        When a meal's cost pushes remaining_budget below 0 the engine
        should prefer cheaper alternatives.
        """
        engine = MealPlanEngine()
        profile = _make_profile(budget_per_week=105.0, people_count=1)
        slot = _make_slot(calorie_target=500, per_meal_budget=5.0)

        cheap = _make_recipe("cheap", "Cheap", calories=500, cost=3.0)
        expensive = _make_recipe("expensive", "Expensive", calories=500, cost=20.0)

        candidates = [cheap, expensive]
        used_recent = deque(maxlen=5)

        # remaining_budget = 4.0 (almost exhausted)
        picked = engine._pick_recipe(candidates, slot, profile, used_recent, remaining_budget=4.0)

        # cheap costs 3.0 (within budget), expensive costs 20.0 (way over).
        # With hard penalty of |4.0-20.0| * 10 = 160 for expensive, cheap wins.
        assert picked.recipe_id == "cheap"

    def test_soft_penalty_when_above_per_meal_average(self):
        """
        A meal costing more than per_meal_budget but still under remaining
        should get a soft penalty, making the cheaper option preferable.
        """
        engine = MealPlanEngine()
        profile = _make_profile(budget_per_week=105.0, people_count=1)
        slot = _make_slot(calorie_target=500, per_meal_budget=5.0)

        on_budget = _make_recipe("on_budget", "On Budget", calories=500, cost=5.0)
        slightly_over = _make_recipe("over", "Slightly Over", calories=500, cost=8.0)

        candidates = [on_budget, slightly_over]
        used_recent = deque(maxlen=5)

        picked = engine._pick_recipe(candidates, slot, profile, used_recent, remaining_budget=50.0)

        # slightly_over cost (8.0) > per_meal_budget (5.0)
        # soft penalty = (8.0 - 5.0) * 5.0 = 15.0
        # on_budget has 0 penalty  => should be picked
        assert picked.recipe_id == "on_budget"

    def test_no_penalty_when_within_budget(self):
        """
        When remaining budget is ample and cost <= per_meal_budget,
        there should be zero budget penalty.
        """
        engine = MealPlanEngine()
        profile = _make_profile(budget_per_week=200.0, people_count=1)
        slot = _make_slot(calorie_target=500, per_meal_budget=10.0)

        r1 = _make_recipe("r1", "Recipe A", calories=500, cost=4.0)
        r2 = _make_recipe("r2", "Recipe B", calories=490, cost=5.0)

        candidates = [r1, r2]
        used_recent = deque(maxlen=5)

        # Both within budget; pick should be driven by calorie penalty only
        picked = engine._pick_recipe(candidates, slot, profile, used_recent, remaining_budget=100.0)

        # r1 has calorie penalty |500-500| = 0,  r2 has |490-500| = 10
        # both budget penalties = 0, so r1 should win
        assert picked.recipe_id == "r1"

    def test_no_budget_penalty_when_budget_is_none(self):
        """If remaining_budget is None, no budget penalty should apply."""
        engine = MealPlanEngine()
        profile = _make_profile(budget_per_week=None, people_count=1)
        slot = _make_slot(calorie_target=500, per_meal_budget=None)

        cheap = _make_recipe("cheap", "Cheap", calories=500, cost=2.0)
        expensive = _make_recipe("exp", "Expensive", calories=500, cost=50.0)

        candidates = [cheap, expensive]
        used_recent = deque(maxlen=5)

        # With no budget, both have the same calorie penalty
        # Neither should be penalised for cost
        picked = engine._pick_recipe(candidates, slot, profile, used_recent, remaining_budget=None)
        # Either is fine since both have zero calorie deviation
        assert picked is not None

    def test_repeat_penalty_combines_with_budget_penalty(self):
        """
        Repeat penalty (200) and budget penalty should both factor into
        the total score.
        """
        engine = MealPlanEngine()
        profile = _make_profile(budget_per_week=105.0, people_count=1)
        slot = _make_slot(calorie_target=500, per_meal_budget=5.0)

        repeated = _make_recipe("repeated", "Repeated", calories=500, cost=4.0)
        fresh = _make_recipe("fresh", "Fresh", calories=500, cost=5.0)

        candidates = [repeated, fresh]
        used_recent = deque(maxlen=5)
        used_recent.append("repeated")

        picked = engine._pick_recipe(candidates, slot, profile, used_recent, remaining_budget=50.0)

        # repeated: calorie=0, repeat=200, budget=0 => total 200
        # fresh:    calorie=0, repeat=0,   budget=0 => total 0
        assert picked.recipe_id == "fresh"

    def test_people_count_multiplies_cost(self):
        """
        meal_cost = estimated_cost * people_count, so a family meal costs
        more and should be penalised harder when over budget.
        """
        engine = MealPlanEngine()
        profile = _make_profile(budget_per_week=210.0, people_count=3)
        # per_meal_budget = 210 / 21 = 10.0
        slot = _make_slot(calorie_target=500, per_meal_budget=10.0)

        cheap = _make_recipe("cheap", "Cheap", calories=500, cost=3.0)
        expensive = _make_recipe("exp", "Expensive", calories=500, cost=6.0)

        candidates = [cheap, expensive]
        used_recent = deque(maxlen=5)

        # expensive: meal_cost = 6 * 3 = 18.0 > per_meal_budget (10.0)
        # soft penalty = (18-10) * 5 = 40
        # cheap: meal_cost = 3 * 3 = 9.0 <= 10.0 => penalty = 0
        picked = engine._pick_recipe(candidates, slot, profile, used_recent, remaining_budget=100.0)
        assert picked.recipe_id == "cheap"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
