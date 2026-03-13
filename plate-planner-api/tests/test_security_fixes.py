"""
Tests for Security Fixes — Cypher Injection Prevention

Verifies that the healthy_alternatives.py service safely parameterises
all user-supplied values passed into Cypher queries, so that malicious
input cannot escape the query string.
"""
import pytest
from unittest.mock import Mock, call

from src.services.healthy_alternatives import HealthyAlternativesService
from src.schemas.nutrition import DietaryRestriction, Allergen


@pytest.fixture
def mock_neo4j():
    """Mock Neo4j service."""
    return Mock()


@pytest.fixture
def service(mock_neo4j):
    """Create HealthyAlternativesService with a mocked Neo4j backend."""
    return HealthyAlternativesService(mock_neo4j)


class TestCypherInjectionPrevention:
    """Ensure user-supplied strings never end up interpolated in Cypher."""

    def test_meal_type_injection_attempt_is_parameterized(self, service, mock_neo4j):
        """
        A malicious meal_type like "breakfast' OR 1=1 --" should be passed
        through the $meal_type parameter, NOT interpolated into the query
        string.
        """
        mock_neo4j.execute_query.return_value = []

        # suggest_healthiest_recipes passes meal_type via $meal_type param
        service.suggest_healthiest_recipes(
            meal_type="breakfast' OR 1=1 --",
            limit=5,
        )

        call_args = mock_neo4j.execute_query.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        # The malicious string must NOT appear inline in the Cypher text
        assert "OR 1=1" not in query
        # It must be safely passed as a parameter
        assert params["meal_type"] == "breakfast' OR 1=1 --"
        # The query itself should reference $meal_type
        assert "$meal_type" in query

    def test_recipe_id_injection_attempt_is_parameterized(self, service, mock_neo4j):
        """
        A crafted recipe_id like "recipe-1' DETACH DELETE (n) --" must
        be safely parameterized.
        """
        mock_neo4j.execute_query.return_value = []

        service.find_healthier_alternative(
            recipe_id="recipe-1' DETACH DELETE (n) --"
        )

        # First call fetches the original recipe
        first_call_args = mock_neo4j.execute_query.call_args_list[0]
        query = first_call_args[0][0]
        params = first_call_args[0][1]

        assert "DETACH DELETE" not in query
        assert params["recipe_id"] == "recipe-1' DETACH DELETE (n) --"
        assert "$recipe_id" in query

    def test_meal_type_none_does_not_add_filter(self, service, mock_neo4j):
        """When meal_type is None the query should not include a meal_type clause."""
        mock_neo4j.execute_query.return_value = []

        service.suggest_healthiest_recipes(meal_type=None, limit=5)

        call_args = mock_neo4j.execute_query.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "meal_type" not in query.lower() or "$meal_type" not in query
        assert "meal_type" not in params

    def test_dietary_filter_does_not_interpolate_user_values(self, service, mock_neo4j):
        """
        Dietary restriction filters are hard-coded (r2.is_vegan = true)
        and should NOT embed any user-supplied strings.
        """
        mock_neo4j.execute_query.return_value = []

        service.suggest_healthiest_recipes(
            meal_type="dinner",
            dietary_restrictions=[DietaryRestriction.VEGAN],
            allergens=[Allergen.NUTS],
            limit=5,
        )

        call_args = mock_neo4j.execute_query.call_args
        query = call_args[0][0]

        # Dietary clause is hard-coded, not interpolated
        assert "r.is_vegan = true" in query
        assert "NOT 'nuts' IN r.allergens" in query

    def test_special_characters_in_meal_type_are_safe(self, service, mock_neo4j):
        """
        Even special characters (backslash, quotes, semicolons) must be
        safely passed as parameters.
        """
        mock_neo4j.execute_query.return_value = []

        evil_inputs = [
            "breakfast\\'; DROP TABLE recipes; --",
            'breakfast"}]) RETURN 1 //',
            "lunch\n RETURN n UNION MATCH (n)",
        ]

        for evil_input in evil_inputs:
            service.suggest_healthiest_recipes(meal_type=evil_input, limit=1)

            call_args = mock_neo4j.execute_query.call_args
            query = call_args[0][0]
            params = call_args[0][1]

            # The evil string should NEVER appear directly in the query
            assert evil_input not in query, (
                f"Injection payload appeared in query: {evil_input}"
            )
            assert params["meal_type"] == evil_input


class TestHealthyAlternativesParameterisation:
    """Extra checks that the alternative-finding query uses $-params everywhere."""

    def test_find_healthier_uses_params_for_recipe_id(self, service, mock_neo4j):
        """find_healthier_alternative should pass recipe_id as $recipe_id."""
        mock_neo4j.execute_query.side_effect = [
            [{  # original recipe
                "id": "r1",
                "title": "Fried Chicken",
                "health_score": 4.0,
                "calories": 500,
                "protein_g": 30,
                "sodium_mg": 1200,
            }],
            [],  # no alternatives
        ]

        service.find_healthier_alternative("r1")

        # Both queries should reference $recipe_id
        for call_args in mock_neo4j.execute_query.call_args_list:
            query = call_args[0][0]
            params = call_args[0][1]
            assert "$recipe_id" in query
            assert params["recipe_id"] == "r1"

    def test_min_score_is_parameterized(self, service, mock_neo4j):
        """The minimum health score threshold should be a $min_score param."""
        mock_neo4j.execute_query.side_effect = [
            [{
                "id": "r1",
                "title": "Burger",
                "health_score": 3.0,
                "calories": 700,
            }],
            [],  # no alternatives
        ]

        service.find_healthier_alternative("r1", min_score_improvement=1.0)

        # Second query is the alternative search
        second_call = mock_neo4j.execute_query.call_args_list[1]
        query = second_call[0][0]
        params = second_call[0][1]

        assert "$min_score" in query
        assert params["min_score"] == 4.0  # 3.0 + 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
