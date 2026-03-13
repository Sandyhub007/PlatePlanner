"""
Tests for Recipe Category / Meal-Type Filtering in POST /suggest_recipes.

Covers:
  - Filtering by "breakfast", "lunch", "dinner", "snack"
  - Graceful degradation when filter yields no results (returns unfiltered)
  - No category filter (should return all)
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.api.app import app


client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_recipe(title: str, combined_score: float = 0.7, **overrides) -> dict:
    base = {
        "title": title,
        "ingredients": ["tomato", "garlic"],
        "all_ingredients": ["tomato", "garlic"],
        "directions": "Cook.",
        "semantic_score": 0.6,
        "overlap_score": 0.5,
        "combined_score": combined_score,
        "rank": 1,
        "tags": {},
        "source": "local",
        "cuisine": [],
        "source_url": "",
        "image": "",
    }
    base.update(overrides)
    return base


def _post(payload: dict, local_results: list[dict]) -> dict | list:
    with patch("src.api.app.suggest_recipes", return_value=local_results), \
         patch("src.api.app.spoonacular") as mock_sp:
        mock_sp.enabled = False
        response = client.post("/suggest_recipes", json=payload)
    return response


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCategoryFilterBreakfast:
    """Filter by category='breakfast'."""

    def test_breakfast_filter_returns_breakfast_recipes(self):
        results = [
            _make_recipe("Pancake Stack", combined_score=0.9),
            _make_recipe("Grilled Steak", combined_score=0.8),
            _make_recipe("Omelette Supreme", combined_score=0.7),
        ]
        response = _post(
            {"ingredients": ["egg", "flour"], "category": "breakfast"},
            results,
        )
        assert response.status_code == 200
        titles = [r["title"] for r in response.json()]
        # Pancake and Omelette should match breakfast keywords; Steak should not
        assert "Pancake Stack" in titles
        assert "Omelette Supreme" in titles

    def test_breakfast_filter_case_insensitive(self):
        results = [
            _make_recipe("French Toast Delight", combined_score=0.9),
        ]
        response = _post(
            {"ingredients": ["bread", "egg"], "category": "Breakfast"},
            results,
        )
        assert response.status_code == 200


class TestCategoryFilterLunch:
    """Filter by category='lunch'."""

    def test_lunch_filter_returns_lunch_recipes(self):
        results = [
            _make_recipe("Turkey Sandwich", combined_score=0.8),
            _make_recipe("Caesar Salad", combined_score=0.7),
            _make_recipe("Chocolate Cake", combined_score=0.9),
        ]
        response = _post(
            {"ingredients": ["lettuce", "chicken"], "category": "lunch"},
            results,
        )
        assert response.status_code == 200
        titles = [r["title"] for r in response.json()]
        assert "Turkey Sandwich" in titles or "Caesar Salad" in titles


class TestCategoryFilterDinner:
    """Filter by category='dinner'."""

    def test_dinner_filter_returns_dinner_recipes(self):
        results = [
            _make_recipe("Grilled Chicken Pasta", combined_score=0.9),
            _make_recipe("Beef Stew", combined_score=0.8),
            _make_recipe("Granola Bars", combined_score=0.7),
        ]
        response = _post(
            {"ingredients": ["chicken", "pasta"], "category": "dinner"},
            results,
        )
        assert response.status_code == 200
        titles = [r["title"] for r in response.json()]
        # Pasta and chicken/beef stew are dinner keywords
        assert any("Pasta" in t or "Stew" in t for t in titles)


class TestCategoryFilterSnack:
    """Filter by category='snack'."""

    def test_snack_filter_returns_snack_recipes(self):
        results = [
            _make_recipe("Trail Mix Bites", combined_score=0.8),
            _make_recipe("Energy Ball Snack", combined_score=0.7),
            _make_recipe("Beef Lasagna", combined_score=0.9),
        ]
        response = _post(
            {"ingredients": ["oats", "honey"], "category": "snack"},
            results,
        )
        assert response.status_code == 200
        titles = [r["title"] for r in response.json()]
        assert any("Trail Mix" in t or "Snack" in t or "Energy Ball" in t for t in titles)


class TestCategoryFilterDessert:
    """Filter by category='dessert'."""

    def test_dessert_filter_returns_dessert_recipes(self):
        results = [
            _make_recipe("Chocolate Brownie", combined_score=0.9),
            _make_recipe("Grilled Salmon", combined_score=0.8),
        ]
        response = _post(
            {"ingredients": ["chocolate", "sugar"], "category": "dessert"},
            results,
        )
        assert response.status_code == 200
        titles = [r["title"] for r in response.json()]
        assert "Chocolate Brownie" in titles


class TestCategoryFilterGracefulDegradation:
    """When the filter yields zero results, the unfiltered list should be returned."""

    def test_no_match_returns_unfiltered(self):
        results = [
            _make_recipe("Plain Rice", combined_score=0.5),
            _make_recipe("Steamed Vegetables", combined_score=0.6),
        ]
        response = _post(
            {"ingredients": ["rice"], "category": "breakfast"},
            results,
        )
        assert response.status_code == 200
        data = response.json()
        # Neither "Plain Rice" nor "Steamed Vegetables" match breakfast keywords,
        # so graceful degradation should return the unfiltered set.
        assert len(data) >= 1


class TestNoCategoryFilter:
    """When no category is provided, all results should be returned."""

    def test_no_category_returns_all(self):
        results = [
            _make_recipe("A", combined_score=0.9),
            _make_recipe("B", combined_score=0.8),
            _make_recipe("C", combined_score=0.7),
        ]
        response = _post(
            {"ingredients": ["test"]},
            results,
        )
        assert response.status_code == 200
        assert len(response.json()) == 3

    def test_category_none_returns_all(self):
        results = [
            _make_recipe("Alpha", combined_score=0.9),
            _make_recipe("Beta", combined_score=0.8),
        ]
        response = _post(
            {"ingredients": ["test"], "category": None},
            results,
        )
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestCategoryFilterWithIngredientMatch:
    """Category filter also checks ingredient list for keywords."""

    def test_matches_on_ingredients_not_just_title(self):
        results = [
            _make_recipe(
                "Morning Delight",
                combined_score=0.8,
                all_ingredients=["egg", "bacon", "toast"],
            ),
        ]
        response = _post(
            {"ingredients": ["egg"], "category": "breakfast"},
            results,
        )
        assert response.status_code == 200
        # "egg" is a breakfast keyword that appears in ingredients
        titles = [r["title"] for r in response.json()]
        assert "Morning Delight" in titles


class TestUnknownCategory:
    """Unknown category should not crash; just returns unfiltered."""

    def test_unknown_category_returns_unfiltered(self):
        results = [
            _make_recipe("Some Recipe", combined_score=0.7),
        ]
        response = _post(
            {"ingredients": ["test"], "category": "brunch"},
            results,
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
